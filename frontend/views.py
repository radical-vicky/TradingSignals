from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User  # ADD THIS IMPORT
from django.contrib import messages
from django.http import JsonResponse
from django.db import OperationalError, IntegrityError
from django.utils import timezone
from django.db.models import Q
import time
import json
import uuid
from .models import Signal, SignalPurchase, UserProfile, PaymentTransaction, Notification, LiveSession, SessionParticipant, SessionMessage, SessionTradeIdea, VideoCallRoom, VideoCallParticipant
from .forms import EnhancedUserProfileForm, ProfilePictureForm, VideoCallRoomForm, SignalPurchaseForm, LiveSessionForm, SessionMessageForm, SessionTradeIdeaForm, LiveSessionFilterForm
from .payment_services import MpesaService, PayPalService


def home(request):
    try:
        if not Signal.objects.exists():
            Signal.objects.create(
                symbol='GOLD',
                signal_type='SELL',
                status='CLOSED',
                entry_price=4147.84,
                take_profit_1=4148.00,
                stop_loss=4388.00,
                price=15.00,
                timestamp='2025-11-14 11:17:00'
            )
            Signal.objects.create(
                symbol='BTCUSDT',
                signal_type='BUY',
                status='OPEN',
                entry_price=34500.00,
                take_profit_1=35500.00,
                stop_loss=34000.00,
                price=20.00,
                timestamp='2025-11-14 10:30:00'
            )
        
        latest_signals = Signal.objects.filter(status='OPEN').order_by('-created_at')[:6]
        live_sessions = LiveSession.objects.filter(status='LIVE').order_by('-created_at')[:3]
        upcoming_sessions = LiveSession.objects.filter(status='SCHEDULED', scheduled_start__gte=timezone.now()).order_by('scheduled_start')[:3]
        active_video_calls = VideoCallRoom.objects.filter(is_active=True).order_by('-created_at')[:3]
        
        unread_notifications_count = 0
        if request.user.is_authenticated:
            unread_notifications_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
        
        context = {
            'latest_signals': latest_signals,
            'live_sessions': live_sessions,
            'upcoming_sessions': upcoming_sessions,
            'active_video_calls': active_video_calls,
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/home.html', context)
    
    except OperationalError:
        context = {
            'database_error': True,
            'latest_signals': [],
            'live_sessions': [],
            'upcoming_sessions': [],
            'active_video_calls': []
        }
        return render(request, 'dashboard/home.html', context)
@login_required
def profile(request):
    try:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        purchased_signals_count = SignalPurchase.objects.filter(
            user=request.user, 
            status='COMPLETED'
        ).count()
        
        active_sessions = SessionParticipant.objects.filter(
            user=request.user,
            is_active=True
        ).count()
        
        created_sessions_count = 0
        if user_profile.is_trader:
            created_sessions_count = LiveSession.objects.filter(trader=request.user).count()
        
        video_call_rooms = VideoCallRoom.objects.filter(created_by=request.user, is_active=True).order_by('-created_at')[:5]
        
        # Initialize forms
        form = EnhancedUserProfileForm(instance=user_profile)
        picture_form = ProfilePictureForm(instance=user_profile)
        
        if request.method == 'POST':
            print("POST request received")  # Debug
            print("FILES:", request.FILES)  # Debug
            print("POST data:", request.POST)  # Debug
            
            if 'profile_picture' in request.FILES:
                print("Profile picture found in FILES")  # Debug
                picture_form = ProfilePictureForm(request.POST, request.FILES, instance=user_profile)
                print("Picture form is valid:", picture_form.is_valid())  # Debug
                print("Picture form errors:", picture_form.errors)  # Debug
                
                if picture_form.is_valid():
                    try:
                        picture_form.save()
                        messages.success(request, 'Profile picture updated successfully!')
                        return redirect('profile')
                    except Exception as e:
                        messages.error(request, f'Error saving profile picture: {str(e)}')
                else:
                    # Show specific form errors
                    for field, errors in picture_form.errors.items():
                        for error in errors:
                            messages.error(request, f'Picture upload error: {error}')
                    # Keep the main form
                    form = EnhancedUserProfileForm(instance=user_profile)
            else:
                # Handle main profile form
                form = EnhancedUserProfileForm(request.POST, instance=user_profile)
                if form.is_valid():
                    form.save()
                    
                    if form.cleaned_data.get('apply_as_trader') and not user_profile.is_trader:
                        if user_profile.trader_application_status == 'PENDING':
                            Notification.objects.create(
                                user=request.user,
                                title='Trader Application Submitted',
                                message='Your application to become a trader has been submitted and is under review.',
                                notification_type='SUCCESS'
                            )
                            
                            staff_users = User.objects.filter(is_staff=True)
                            for staff_user in staff_users:
                                Notification.objects.create(
                                    user=staff_user,
                                    title='New Trader Application',
                                    message=f'User {request.user.username} has applied to become a trader.',
                                    notification_type='ALERT'
                                )
                    
                    messages.success(request, 'Profile updated successfully!')
                    return redirect('profile')
                else:
                    # Keep the picture form if main form is invalid
                    picture_form = ProfilePictureForm(instance=user_profile)
        
        purchased_signals = SignalPurchase.objects.filter(
            user=request.user, 
            status='COMPLETED'
        ).select_related('signal').order_by('-purchased_at')[:10]
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'form': form,
            'picture_form': picture_form,
            'user_profile': user_profile,
            'purchased_signals': purchased_signals,
            'purchased_signals_count': purchased_signals_count,
            'active_sessions_count': active_sessions,
            'created_sessions_count': created_sessions_count,
            'video_call_rooms': video_call_rooms,
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/profile.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('home')
    
@login_required
def create_video_call(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        if not user_profile.video_call_enabled:
            messages.error(request, 'Video calls are not enabled for your account.')
            return redirect('profile')
        
        if request.method == 'POST':
            form = VideoCallRoomForm(request.POST, user=request.user)
            if form.is_valid():
                room_id = f"vc_{request.user.username}_{uuid.uuid4().hex[:8]}"
                
                room = form.save(commit=False)
                room.created_by = request.user
                room.room_id = room_id
                room.started_at = timezone.now()
                room.save()
                
                VideoCallParticipant.objects.create(
                    room=room,
                    user=request.user
                )
                
                Notification.objects.create(
                    user=request.user,
                    title='Video Call Created',
                    message=f'You created a new video call room: {room.room_name}',
                    notification_type='SUCCESS'
                )
                
                messages.success(request, 'Video call room created successfully!')
                return redirect('video_call_room', room_id=room_id)
        else:
            form = VideoCallRoomForm(user=request.user)
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'form': form,
            'user_profile': user_profile,
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/create_video_call.html', context)
    
    except Exception as e:
        messages.error(request, f'Error creating video call: {str(e)}')
        return redirect('profile')


@login_required
def video_call_room(request, room_id):
    try:
        room = get_object_or_404(VideoCallRoom, room_id=room_id)
        user_profile = UserProfile.objects.get(user=request.user)
        
        if not room.can_join(request.user):
            messages.error(request, 'Cannot join this video call room. It may be full or inactive.')
            return redirect('profile')
        
        participant = VideoCallParticipant.objects.filter(
            room=room,
            user=request.user,
            left_at__isnull=True
        ).first()
        
        if not participant:
            participant = VideoCallParticipant.objects.create(
                room=room,
                user=request.user
            )
        
        participants = VideoCallParticipant.objects.filter(
            room=room,
            left_at__isnull=True
        ).select_related('user', 'user__userprofile')
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'room': room,
            'participant': participant,
            'participants': participants,
            'user_profile': user_profile,
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/video_call_room.html', context)
    
    except Exception as e:
        messages.error(request, f'Error joining video call: {str(e)}')
        return redirect('profile')


@login_required
def leave_video_call(request, room_id):
    try:
        room = get_object_or_404(VideoCallRoom, room_id=room_id)
        participant = get_object_or_404(
            VideoCallParticipant, 
            room=room, 
            user=request.user,
            left_at__isnull=True
        )
        
        participant.left_at = timezone.now()
        participant.save()
        
        if room.get_participants_count() == 0:
            room.is_active = False
            room.ended_at = timezone.now()
            room.save()
        
        messages.success(request, 'Left the video call successfully.')
        return redirect('profile')
    
    except Exception as e:
        messages.error(request, 'Error leaving video call.')
        return redirect('profile')


@login_required
def end_video_call(request, room_id):
    try:
        room = get_object_or_404(VideoCallRoom, room_id=room_id)
        
        if room.created_by != request.user:
            messages.error(request, 'Only the room creator can end the video call.')
            return redirect('video_call_room', room_id=room_id)
        
        VideoCallParticipant.objects.filter(
            room=room,
            left_at__isnull=True
        ).update(left_at=timezone.now())
        
        room.is_active = False
        room.ended_at = timezone.now()
        room.save()
        
        messages.success(request, 'Video call ended successfully.')
        return redirect('profile')
    
    except Exception as e:
        messages.error(request, 'Error ending video call.')
        return redirect('video_call_room', room_id=room_id)


@login_required
def update_participant_status(request, room_id):
    try:
        if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
            room = get_object_or_404(VideoCallRoom, room_id=room_id)
            participant = get_object_or_404(
                VideoCallParticipant,
                room=room,
                user=request.user,
                left_at__isnull=True
            )
            
            action = request.POST.get('action')
            
            if action == 'toggle_audio':
                participant.is_muted = not participant.is_muted
            elif action == 'toggle_video':
                participant.is_video_off = not participant.is_video_off
            elif action == 'toggle_screen_share':
                participant.is_screen_sharing = not participant.is_screen_sharing
            
            participant.save()
            
            return JsonResponse({
                'success': True,
                'is_muted': participant.is_muted,
                'is_video_off': participant.is_video_off,
                'is_screen_sharing': participant.is_screen_sharing
            })
        
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def signal_list(request):
    try:
        signals = Signal.objects.all().order_by('-created_at')
        
        purchased_signals = []
        unread_notifications_count = 0
        if request.user.is_authenticated:
            purchased_signals = SignalPurchase.objects.filter(
                user=request.user, 
                status='COMPLETED'
            ).values_list('signal_id', flat=True)
            
            unread_notifications_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
        
        is_alerts_page = request.path == '/alerts/'
        
        context = {
            'signals': signals,
            'purchased_signals': list(purchased_signals),
            'is_alerts_page': is_alerts_page,
            'page_title': 'Trading Alerts' if is_alerts_page else 'All Signals',
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/signal_list.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('home')


@login_required
def purchase_signal(request, signal_id):
    try:
        signal = get_object_or_404(Signal, id=signal_id)
        
        # Check if already purchased
        existing_purchase = SignalPurchase.objects.filter(
            user=request.user, 
            signal=signal,
            status='COMPLETED'
        ).first()
        
        if existing_purchase:
            messages.info(request, 'You have already purchased this signal!')
            return redirect('signal_detail', signal_id=signal_id)
        
        if request.method == 'POST':
            form = SignalPurchaseForm(request.POST)
            if form.is_valid():
                payment_method = form.cleaned_data['payment_method']
                print(f"Selected payment method: {payment_method}")  # Debug
                
                # Create payment transaction
                transaction = PaymentTransaction.objects.create(
                    user=request.user,
                    signal=signal,
                    payment_method=payment_method,
                    amount=signal.price,
                    status='PENDING'
                )
                
                # Redirect to appropriate payment gateway
                if payment_method == 'MPESA':
                    return redirect('initiate_mpesa_payment', transaction_id=transaction.id)
                elif payment_method == 'PAYPAL':
                    return redirect('initiate_paypal_payment', transaction_id=transaction.id)
                else:
                    messages.error(request, 'Invalid payment method selected.')
            else:
                # Form validation failed
                messages.error(request, 'Please select a payment method.')
                print("Form errors:", form.errors)  # Debug
        else:
            form = SignalPurchaseForm()
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'signal': signal,
            'form': form,
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/purchase_signal.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('signal_list')


@login_required
def process_mpesa_payment(request, signal_id):
    """Process M-Pesa payment for signal purchase"""
    try:
        signal = get_object_or_404(Signal, id=signal_id)
        
        # Check if already purchased
        existing_purchase = SignalPurchase.objects.filter(
            user=request.user, 
            signal=signal,
            status='COMPLETED'
        ).first()
        
        if existing_purchase:
            messages.info(request, 'You have already purchased this signal!')
            return redirect('signal_detail', signal_id=signal_id)
        
        # Create payment transaction
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            signal=signal,
            payment_method='MPESA',
            amount=signal.price,
            status='PENDING'
        )
        
        return redirect('initiate_mpesa_payment', transaction_id=transaction.id)
    
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('purchase_signal', signal_id=signal_id)


@login_required
def process_paypal_payment(request, signal_id):
    """Process PayPal payment for signal purchase"""
    try:
        signal = get_object_or_404(Signal, id=signal_id)
        
        # Check if already purchased
        existing_purchase = SignalPurchase.objects.filter(
            user=request.user, 
            signal=signal,
            status='COMPLETED'
        ).first()
        
        if existing_purchase:
            messages.info(request, 'You have already purchased this signal!')
            return redirect('signal_detail', signal_id=signal_id)
        
        # Create payment transaction
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            signal=signal,
            payment_method='PAYPAL',
            amount=signal.price,
            status='PENDING'
        )
        
        return redirect('initiate_paypal_payment', transaction_id=transaction.id)
    
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('purchase_signal', signal_id=signal_id)


@login_required
def initiate_mpesa_payment(request, transaction_id):
    try:
        transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
        
        if request.method == 'POST':
            phone_number = request.POST.get('phone_number')
            
            if not phone_number:
                messages.error(request, 'Please provide your M-Pesa phone number')
                return render(request, 'dashboard/mpesa_payment.html', {'transaction': transaction})
            
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif phone_number.startswith('+'):
                phone_number = phone_number[1:]
            
            mpesa_service = MpesaService()
            
            response = mpesa_service.stk_push(
                phone_number=phone_number,
                amount=int(transaction.amount),
                account_reference=f"SIG{transaction.signal.id}",
                transaction_desc=f"Signal purchase for {transaction.signal.symbol}"
            )
            
            if response and response.get('ResponseCode') == '0':
                transaction.merchant_request_id = response.get('MerchantRequestID')
                transaction.checkout_request_id = response.get('CheckoutRequestID')
                transaction.phone_number = phone_number
                transaction.save()
                
                messages.success(request, 'M-Pesa payment request sent to your phone. Please check your phone to complete the payment.')
                return redirect('payment_status', transaction_id=transaction.id)
            else:
                error_message = response.get('ResponseDescription', 'Failed to initiate payment') if response else 'Network error'
                messages.error(request, f'M-Pesa payment failed: {error_message}')
                return render(request, 'dashboard/mpesa_payment.html', {'transaction': transaction})
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return render(request, 'dashboard/mpesa_payment.html', {
            'transaction': transaction,
            'unread_notifications_count': unread_notifications_count
        })
    
    except Exception as e:
        messages.error(request, f'An error occurred while processing your payment: {str(e)}')
        return redirect('purchase_signal', signal_id=transaction.signal.id)


@login_required
def initiate_paypal_payment(request, transaction_id):
    try:
        transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
        
        paypal_service = PayPalService()
        
        return_url = request.build_absolute_uri(f'/payment/paypal/success/{transaction.id}/')
        cancel_url = request.build_absolute_uri(f'/payment/paypal/cancel/{transaction.id}/')
        
        order = paypal_service.create_order(
            amount=float(transaction.amount),
            return_url=return_url,
            cancel_url=cancel_url
        )
        
        if order and order.get('status') == 'CREATED':
            transaction.paypal_order_id = order['id']
            transaction.save()
            
            for link in order.get('links', []):
                if link.get('rel') == 'approve':
                    return redirect(link['href'])
        
        messages.error(request, 'Failed to create PayPal order. Please try again.')
        return redirect('purchase_signal', signal_id=transaction.signal.id)
    
    except Exception as e:
        messages.error(request, f'An error occurred while processing your payment: {str(e)}')
        return redirect('purchase_signal', signal_id=transaction.signal.id)


@login_required
def paypal_payment_success(request, transaction_id):
    try:
        transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
        
        paypal_service = PayPalService()
        capture_result = paypal_service.capture_order(transaction.paypal_order_id)
        
        if capture_result and capture_result.get('status') == 'COMPLETED':
            transaction.status = 'COMPLETED'
            transaction.transaction_id = capture_result['id']
            transaction.save()
            
            SignalPurchase.objects.create(
                user=request.user,
                signal=transaction.signal,
                payment_method='PAYPAL',
                amount=transaction.amount,
                status='COMPLETED',
                transaction_id=transaction.transaction_id
            )
            
            Notification.objects.create(
                user=request.user,
                title='Signal Purchased Successfully',
                message=f'You have successfully purchased the {transaction.signal.symbol} signal.',
                notification_type='SUCCESS'
            )
            
            messages.success(request, 'Payment completed successfully! You now have access to the signal.')
            return redirect('signal_detail', signal_id=transaction.signal.id)
        
        messages.error(request, 'Payment failed. Please try again.')
        return redirect('purchase_signal', signal_id=transaction.signal.id)
    
    except Exception as e:
        messages.error(request, f'An error occurred while processing your payment: {str(e)}')
        return redirect('purchase_signal', signal_id=transaction.signal.id)


@login_required
def paypal_payment_cancel(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    transaction.status = 'CANCELLED'
    transaction.save()
    
    messages.info(request, 'Payment was cancelled.')
    return redirect('purchase_signal', signal_id=transaction.signal.id)


@login_required
def payment_status(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    
    # Auto-complete M-Pesa payments after 30 seconds (for testing)
    if (transaction.payment_method == 'MPESA' and 
        transaction.status == 'PENDING' and
        transaction.created_at and
        (timezone.now() - transaction.created_at).total_seconds() > 30):
        
        transaction.status = 'COMPLETED'
        transaction.transaction_id = f"MP_AUTO_{transaction.id}"
        transaction.save()
        
        signal_purchase, created = SignalPurchase.objects.get_or_create(
            user=request.user,
            signal=transaction.signal,
            defaults={
                'payment_method': 'MPESA',
                'amount': transaction.amount,
                'status': 'COMPLETED',
                'transaction_id': transaction.transaction_id
            }
        )
        
        if not created:
            signal_purchase.status = 'COMPLETED'
            signal_purchase.payment_method = 'MPESA'
            signal_purchase.amount = transaction.amount
            signal_purchase.transaction_id = transaction.transaction_id
            signal_purchase.save()
        
        Notification.objects.create(
            user=request.user,
            title='Signal Purchased Successfully',
            message=f'You have successfully purchased the {transaction.signal.symbol} signal.',
            notification_type='SUCCESS'
        )
    
    # Ensure signal purchase exists for completed transactions
    if transaction.status == 'COMPLETED':
        has_access = SignalPurchase.objects.filter(
            user=request.user,
            signal=transaction.signal,
            status='COMPLETED'
        ).exists()
        
        if not has_access:
            SignalPurchase.objects.create(
                user=request.user,
                signal=transaction.signal,
                payment_method=transaction.payment_method,
                amount=transaction.amount,
                status='COMPLETED',
                transaction_id=transaction.transaction_id
            )
    
    unread_notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return render(request, 'dashboard/payment_status.html', {
        'transaction': transaction,
        'unread_notifications_count': unread_notifications_count
    })


@login_required
def check_and_update_payment(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    
    if transaction.status == 'PENDING':
        transaction.status = 'COMPLETED'
        transaction.transaction_id = f"MP_MANUAL_{transaction.id}"
        transaction.save()
        
        try:
            SignalPurchase.objects.get_or_create(
                user=request.user,
                signal=transaction.signal,
                defaults={
                    'payment_method': transaction.payment_method,
                    'amount': transaction.amount,
                    'status': 'COMPLETED',
                    'transaction_id': transaction.transaction_id
                }
            )
        except IntegrityError:
            existing_purchase = SignalPurchase.objects.get(
                user=request.user,
                signal=transaction.signal
            )
            existing_purchase.status = 'COMPLETED'
            existing_purchase.transaction_id = transaction.transaction_id
            existing_purchase.save()
        
        Notification.objects.create(
            user=request.user,
            title='Signal Purchased Successfully',
            message=f'You have successfully purchased the {transaction.signal.symbol} signal.',
            notification_type='SUCCESS'
        )
        
        messages.success(request, 'Payment status updated to completed!')
        return redirect('signal_detail', signal_id=transaction.signal.id)
    else:
        messages.info(request, f'Payment is already {transaction.status}')
        return redirect('payment_status', transaction_id=transaction.id)


@login_required
def signal_detail(request, signal_id):
    try:
        signal = get_object_or_404(Signal, id=signal_id)
        
        has_purchased = SignalPurchase.objects.filter(
            user=request.user, 
            signal=signal,
            status='COMPLETED'
        ).exists()
        
        has_payment = PaymentTransaction.objects.filter(
            user=request.user,
            signal=signal,
            status='COMPLETED'
        ).exists()
        
        has_access = has_purchased or has_payment
        
        if not has_access:
            messages.warning(request, 'You need to purchase this signal to view details!')
            return redirect('purchase_signal', signal_id=signal_id)
        
        if signal.signal_type == 'BUY':
            potential_profit = float(signal.take_profit_1) - float(signal.entry_price)
            potential_loss = float(signal.entry_price) - float(signal.stop_loss)
        else:
            potential_profit = float(signal.entry_price) - float(signal.take_profit_1)
            potential_loss = float(signal.stop_loss) - float(signal.entry_price)
        
        risk_reward_ratio = abs(potential_profit / potential_loss) if potential_loss != 0 else 0
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'signal': signal,
            'has_purchased': has_access,
            'potential_profit': round(potential_profit, 2),
            'potential_loss': round(potential_loss, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/signal_detail.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('signal_list')


@login_required
def live_sessions(request):
    try:
        sessions_list = LiveSession.objects.all().order_by('-scheduled_start')
        
        form = LiveSessionFilterForm(request.GET)
        if form.is_valid():
            session_type = form.cleaned_data.get('session_type')
            status = form.cleaned_data.get('status')
            
            if session_type:
                sessions_list = sessions_list.filter(session_type=session_type)
            if status:
                sessions_list = sessions_list.filter(status=status)
        
        live_sessions = sessions_list.filter(status='LIVE')
        scheduled_sessions = sessions_list.filter(status='SCHEDULED')
        ended_sessions = sessions_list.filter(status='ENDED')[:10]
        
        user_participations = SessionParticipant.objects.filter(
            user=request.user,
            is_active=True
        ).values_list('session_id', flat=True)
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'live_sessions': live_sessions,
            'scheduled_sessions': scheduled_sessions,
            'ended_sessions': ended_sessions,
            'filter_form': form,
            'user_participations': list(user_participations),
            'unread_notifications_count': unread_notifications_count,
        }
        
        return render(request, 'dashboard/live_sessions.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('home')


@login_required
def create_live_session(request):
    try:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if not user_profile.is_trader:
            messages.error(request, 'Only traders can create live sessions.')
            return redirect('live_sessions')
        
        if request.method == 'POST':
            form = LiveSessionForm(request.POST, trader=request.user)
            if form.is_valid():
                session = form.save()
                
                SessionParticipant.objects.create(
                    session=session,
                    user=request.user,
                    role='TRADER',
                    is_active=True
                )
                
                if session.is_public:
                    Notification.objects.create(
                        user=request.user,
                        title='Live Session Created',
                        message=f'Your live session "{session.title}" has been scheduled.',
                        notification_type='SUCCESS'
                    )
                
                messages.success(request, 'Live session created successfully!')
                return redirect('live_session_detail', session_id=session.id)
        else:
            form = LiveSessionForm(trader=request.user)
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'form': form,
            'unread_notifications_count': unread_notifications_count,
        }
        
        return render(request, 'dashboard/create_live_session.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('live_sessions')


@login_required
def live_session_detail(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        user_participation = SessionParticipant.objects.filter(
            session=session,
            user=request.user,
            is_active=True
        ).first()
        
        messages_list = SessionMessage.objects.filter(session=session).select_related('user').order_by('created_at')
        trade_ideas = SessionTradeIdea.objects.filter(session=session, is_active=True).order_by('-created_at')
        participants_count = SessionParticipant.objects.filter(session=session, is_active=True).count()
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        last_message = messages_list.last()
        last_message_id = last_message.id if last_message else 0
        
        context = {
            'session': session,
            'user_participation': user_participation,
            'messages': messages_list,
            'trade_ideas': trade_ideas,
            'participants_count': participants_count,
            'unread_notifications_count': unread_notifications_count,
            'last_message_id': last_message_id,
        }
        
        return render(request, 'dashboard/live_session_detail.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('live_sessions')


@login_required
def join_live_session(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        if not session.can_join():
            messages.error(request, 'This session is not currently available for joining.')
            return redirect('live_session_detail', session_id=session.id)
        
        existing_participation = SessionParticipant.objects.filter(
            session=session,
            user=request.user
        ).first()
        
        if existing_participation:
            if existing_participation.is_active:
                messages.info(request, 'You are already in this session.')
            else:
                existing_participation.is_active = True
                existing_participation.joined_at = timezone.now()
                existing_participation.left_at = None
                existing_participation.save()
                messages.success(request, 'Rejoined the session successfully!')
        else:
            current_participants = SessionParticipant.objects.filter(session=session, is_active=True).count()
            if current_participants >= session.max_participants:
                messages.error(request, 'This session has reached maximum participants.')
                return redirect('live_session_detail', session_id=session.id)
            
            if request.user == session.trader:
                role = 'TRADER'
            elif request.user.is_staff:
                role = 'MODERATOR'
            else:
                role = 'PARTICIPANT'
            
            SessionParticipant.objects.create(
                session=session,
                user=request.user,
                role=role,
                is_active=True
            )
            messages.success(request, 'Joined the session successfully!')
        
        return redirect('live_session_detail', session_id=session.id)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('live_sessions')


@login_required
def leave_live_session(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        participation = SessionParticipant.objects.filter(
            session=session,
            user=request.user,
            is_active=True
        ).first()
        
        if participation:
            participation.is_active = False
            participation.left_at = timezone.now()
            participation.save()
            messages.success(request, 'Left the session successfully!')
        else:
            messages.info(request, 'You are not currently in this session.')
        
        return redirect('live_session_detail', session_id=session.id)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('live_sessions')


@login_required
def send_session_message(request, session_id):
    try:
        if request.method == 'POST':
            session = get_object_or_404(LiveSession, id=session_id)
            
            participation = SessionParticipant.objects.filter(
                session=session,
                user=request.user,
                is_active=True
            ).first()
            
            if not participation:
                return JsonResponse({'success': False, 'error': 'You are not in this session'})
            
            form = SessionMessageForm(request.POST, session=session, user=request.user)
            if form.is_valid():
                message = form.save()
                
                return JsonResponse({
                    'success': True,
                    'message_id': message.id,
                    'user': message.user.username,
                    'content': message.content,
                    'message_type': message.message_type,
                    'created_at': message.created_at.strftime('%H:%M:%S')
                })
            else:
                return JsonResponse({'success': False, 'error': 'Invalid message'})
        
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def create_trade_idea(request, session_id):
    try:
        if request.method == 'POST':
            session = get_object_or_404(LiveSession, id=session_id)
            
            if request.user != session.trader:
                return JsonResponse({'success': False, 'error': 'Only the trader can create trade ideas'})
            
            form = SessionTradeIdeaForm(request.POST, session=session, trader=request.user)
            if form.is_valid():
                trade_idea = form.save()
                
                SessionMessage.objects.create(
                    session=session,
                    user=request.user,
                    message_type='TRADE_IDEA',
                    content=f"New trade idea: {trade_idea.symbol} {trade_idea.get_idea_type_display()} - {trade_idea.rationale}"
                )
                
                return JsonResponse({
                    'success': True,
                    'trade_idea_id': trade_idea.id,
                    'symbol': trade_idea.symbol,
                    'idea_type': trade_idea.get_idea_type_display(),
                    'rationale': trade_idea.rationale
                })
            else:
                return JsonResponse({'success': False, 'error': 'Invalid trade idea data'})
        
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def start_live_session(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        if request.user != session.trader:
            messages.error(request, 'Only the trader can start the session.')
            return redirect('live_session_detail', session_id=session.id)
        
        if session.status != 'SCHEDULED':
            messages.error(request, 'Session can only be started from scheduled status.')
            return redirect('live_session_detail', session_id=session.id)
        
        session.status = 'LIVE'
        session.actual_start = timezone.now()
        session.save()
        
        SessionMessage.objects.create(
            session=session,
            user=request.user,
            message_type='ANNOUNCEMENT',
            content="Session is now LIVE! Welcome everyone!"
        )
        
        messages.success(request, 'Session started successfully!')
        return redirect('live_session_detail', session_id=session.id)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('live_sessions')


@login_required
def end_live_session(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        if request.user != session.trader:
            messages.error(request, 'Only the trader can end the session.')
            return redirect('live_session_detail', session_id=session.id)
        
        if session.status != 'LIVE':
            messages.error(request, 'Session can only be ended from live status.')
            return redirect('live_session_detail', session_id=session.id)
        
        session.status = 'ENDED'
        session.actual_end = timezone.now()
        session.save()
        
        SessionParticipant.objects.filter(session=session, is_active=True).update(
            is_active=False,
            left_at=timezone.now()
        )
        
        SessionMessage.objects.create(
            session=session,
            user=request.user,
            message_type='ANNOUNCEMENT',
            content="Session has ended. Thank you for participating!"
        )
        
        messages.success(request, 'Session ended successfully!')
        return redirect('live_session_detail', session_id=session.id)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('live_sessions')


@login_required
def get_session_messages(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        participation = SessionParticipant.objects.filter(
            session=session,
            user=request.user,
            is_active=True
        ).first()
        
        if not participation:
            return JsonResponse({'success': False, 'error': 'Not a participant'})
        
        last_message_id = request.GET.get('last_message_id', 0)
        
        messages_list = SessionMessage.objects.filter(
            session=session,
            id__gt=last_message_id
        ).select_related('user').order_by('created_at')
        
        messages_data = []
        for msg in messages_list:
            messages_data.append({
                'id': msg.id,
                'user': msg.user.username,
                'content': msg.content,
                'message_type': msg.message_type,
                'is_pinned': msg.is_pinned,
                'created_at': msg.created_at.strftime('%H:%M:%S')
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_session_participants(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        participants = SessionParticipant.objects.filter(
            session=session,
            is_active=True
        ).select_related('user')
        
        participants_data = []
        for participant in participants:
            participants_data.append({
                'username': participant.user.username,
                'role': participant.role,
                'joined_at': participant.joined_at.strftime('%H:%M:%S')
            })
        
        return JsonResponse({
            'success': True,
            'participants': participants_data
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_session_status(request, session_id):
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        
        return JsonResponse({
            'status': session.status,
            'participants_count': SessionParticipant.objects.filter(session=session, is_active=True).count(),
            'is_trader': request.user == session.trader
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_user_sessions(request):
    try:
        active_sessions = SessionParticipant.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('session')
        
        sessions_data = []
        for participation in active_sessions:
            session = participation.session
            sessions_data.append({
                'id': session.id,
                'title': session.title,
                'status': session.status,
                'trader': session.trader.username,
                'role': participation.role
            })
        
        return JsonResponse({
            'success': True,
            'sessions': sessions_data
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def notifications(request):
    try:
        notifications_list = Notification.objects.filter(user=request.user).order_by('-created_at')
        
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        context = {
            'notifications': notifications_list,
            'unread_notifications_count': unread_notifications_count,
        }
        return render(request, 'dashboard/notifications.html', context)
    
    except OperationalError:
        messages.error(request, 'Database not ready. Please run migrations first.')
        return redirect('home')


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('notifications')


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('notifications')


@login_required
def get_notifications_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def get_recent_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': notification.get_time_ago(),
        })
    
    return JsonResponse({'notifications': notifications_data})


def mpesa_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
            merchant_request_id = data.get('Body', {}).get('stkCallback', {}).get('MerchantRequestID')
            checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
            
            if result_code == 0:
                transaction = PaymentTransaction.objects.get(
                    merchant_request_id=merchant_request_id,
                    checkout_request_id=checkout_request_id
                )
                transaction.status = 'COMPLETED'
                transaction.transaction_id = checkout_request_id
                transaction.save()
                
                SignalPurchase.objects.create(
                    user=transaction.user,
                    signal=transaction.signal,
                    payment_method='MPESA',
                    amount=transaction.amount,
                    status='COMPLETED',
                    transaction_id=checkout_request_id
                )
                
                Notification.objects.create(
                    user=transaction.user,
                    title='Signal Purchased Successfully',
                    message=f'You have successfully purchased the {transaction.signal.symbol} signal.',
                    notification_type='SUCCESS'
                )
            
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
        
        except Exception as e:
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Failed'})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)