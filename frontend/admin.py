from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.http import urlencode
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from .models import Signal, SignalPurchase, UserProfile, PaymentTransaction, Notification, LiveSession, SessionParticipant, SessionMessage, SessionTradeIdea, SessionRecording, VideoCallRoom, VideoCallParticipant, VideoCallRecording


@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = [
        'symbol', 'signal_type_badge', 'status', 'price', 
        'entry_price', 'take_profit_1', 'stop_loss', 'timestamp', 
        'created_at', 'purchase_count', 'profit_loss_calc'
    ]
    list_filter = ['signal_type', 'status', 'created_at']
    search_fields = ['symbol', 'signal_type']
    readonly_fields = ['created_at', 'updated_at', 'purchase_count', 'profit_loss_calc']
    list_per_page = 20
    list_editable = ['price', 'status']
    date_hierarchy = 'created_at'
    actions = ['mark_as_closed', 'mark_as_open', 'duplicate_signals']
    
    fieldsets = (
        ('Signal Information', {
            'fields': ('symbol', 'signal_type', 'status', 'timestamp', 'price')
        }),
        ('Trading Levels', {
            'fields': ('entry_price', 'take_profit_1', 'stop_loss')
        }),
        ('Statistics', {
            'fields': ('purchase_count', 'profit_loss_calc'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            purchase_count=Count('signalpurchase')
        )

    def purchase_count(self, obj):
        count = obj.signalpurchase_set.count()
        url = (
            reverse("admin:frontend_signalpurchase_changelist")
            + "?"
            + urlencode({"signal__id": f"{obj.id}"})
        )
        return format_html('<a href="{}" title="View purchases">{}</a>', url, count)
    purchase_count.short_description = '📊 Purchases'

    def profit_loss_calc(self, obj):
        """Calculate potential profit/loss percentage"""
        if obj.signal_type == 'BUY':
            profit_target = obj.take_profit_1
            risk = obj.stop_loss
        else:  # SELL
            profit_target = obj.stop_loss
            risk = obj.take_profit_1
        
        try:
            entry = float(obj.entry_price)
            profit = float(profit_target)
            risk_val = float(risk)
            
            profit_pct = ((profit - entry) / entry) * 100
            risk_pct = ((risk_val - entry) / entry) * 100
            
            reward_ratio = abs(profit_pct / risk_pct) if risk_pct != 0 else 0
            
            color = 'green' if profit_pct > 0 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f}% / {:.2f}% (R:R {:.2f})</span>',
                color, profit_pct, risk_pct, reward_ratio
            )
        except (ValueError, TypeError):
            return format_html('<span style="color: gray;">N/A</span>')
    profit_loss_calc.short_description = 'P/L %'

    def signal_type_badge(self, obj):
        color = 'green' if obj.signal_type == 'BUY' else 'red'
        icon = '📈' if obj.signal_type == 'BUY' else '📉'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_signal_type_display()
        )
    signal_type_badge.short_description = 'Type'

    def mark_as_closed(self, request, queryset):
        updated = queryset.update(status='CLOSED')
        self.message_user(
            request, 
            f'Successfully closed {updated} signal(s).',
            messages.SUCCESS
        )
    mark_as_closed.short_description = "🔒 Mark selected as CLOSED"

    def mark_as_open(self, request, queryset):
        updated = queryset.update(status='OPEN')
        self.message_user(
            request, 
            f'Successfully opened {updated} signal(s).',
            messages.SUCCESS
        )
    mark_as_open.short_description = "🔓 Mark selected as OPEN"

    def duplicate_signals(self, request, queryset):
        for signal in queryset:
            signal.pk = None
            signal.symbol = f"{signal.symbol}-COPY"
            signal.status = 'PENDING'
            signal.save()
        
        self.message_user(
            request,
            f'Successfully duplicated {queryset.count()} signal(s).',
            messages.SUCCESS
        )
    duplicate_signals.short_description = "📋 Duplicate selected signals"


@admin.register(SignalPurchase)
class SignalPurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'signal_link', 'payment_method_badge', 'amount', 
        'status_badge', 'purchased_at', 'transaction_link', 'time_since_purchase'
    ]
    list_filter = ['payment_method', 'status', 'purchased_at']
    search_fields = ['user__username', 'signal__symbol', 'transaction_id']
    readonly_fields = ['purchased_at', 'time_since_purchase']
    list_per_page = 20
    date_hierarchy = 'purchased_at'
    actions = ['mark_as_completed', 'mark_as_failed']
    
    fieldsets = (
        ('Purchase Information', {
            'fields': ('user', 'signal', 'payment_method', 'amount', 'status')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'purchased_at', 'time_since_purchase')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'signal')

    def signal_link(self, obj):
        url = reverse("admin:frontend_signal_change", args=[obj.signal.id])
        return format_html('<a href="{}" title="View signal">📊 {}</a>', url, obj.signal.symbol)
    signal_link.short_description = 'Signal'

    def transaction_link(self, obj):
        if obj.transaction_id:
            try:
                payment_tx = PaymentTransaction.objects.get(transaction_id=obj.transaction_id)
                url = reverse("admin:frontend_paymenttransaction_change", args=[payment_tx.id])
                return format_html('<a href="{}" title="View transaction">🔗 {}</a>', url, obj.transaction_id[:15] + '...')
            except PaymentTransaction.DoesNotExist:
                return format_html('<code>{}</code>', obj.transaction_id[:15] + '...')
        return "—"
    transaction_link.short_description = 'Transaction'

    def payment_method_badge(self, obj):
        colors = {
            'MPESA': 'green',
            'PAYPAL': 'blue'
        }
        icons = {
            'MPESA': '📱',
            'PAYPAL': '💳'
        }
        color = colors.get(obj.payment_method, 'gray')
        icon = icons.get(obj.payment_method, '💰')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_payment_method_display()
        )
    payment_method_badge.short_description = 'Payment Method'

    def status_badge(self, obj):
        colors = {
            'COMPLETED': 'green',
            'PENDING': 'orange',
            'FAILED': 'red'
        }
        icons = {
            'COMPLETED': '✅',
            'PENDING': '⏳',
            'FAILED': '❌'
        }
        color = colors.get(obj.status, 'gray')
        icon = icons.get(obj.status, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def time_since_purchase(self, obj):
        if not obj.purchased_at:
            return "Not purchased yet"
        
        try:
            now = timezone.now()
            diff = now - obj.purchased_at
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds >= 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds >= 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        except (TypeError, AttributeError):
            return "Recently"
    time_since_purchase.short_description = 'Time Since'

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(
            request, 
            f'Successfully marked {updated} purchase(s) as completed.',
            messages.SUCCESS
        )
    mark_as_completed.short_description = "✅ Mark selected as COMPLETED"

    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='FAILED')
        self.message_user(
            request, 
            f'Successfully marked {updated} purchase(s) as failed.',
            messages.SUCCESS
        )
    mark_as_failed.short_description = "❌ Mark selected as FAILED"


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'signal_link', 'payment_method_badge', 'amount', 
        'status_badge', 'created_at', 'transaction_preview', 'time_since_created'
    ]
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = [
        'user__username', 'signal__symbol', 'transaction_id', 
        'merchant_request_id', 'checkout_request_id', 'paypal_order_id'
    ]
    readonly_fields = ['created_at', 'updated_at', 'time_since_created']
    list_per_page = 20
    date_hierarchy = 'created_at'
    actions = ['mark_as_completed', 'mark_as_failed', 'resend_notifications']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('user', 'signal', 'payment_method', 'amount', 'status')
        }),
        ('Payment References', {
            'fields': ('transaction_id', 'merchant_request_id', 'checkout_request_id', 'paypal_order_id', 'phone_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'time_since_created'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'signal')

    def signal_link(self, obj):
        url = reverse("admin:frontend_signal_change", args=[obj.signal.id])
        return format_html('<a href="{}" title="View signal">📊 {}</a>', url, obj.signal.symbol)
    signal_link.short_description = 'Signal'

    def payment_method_badge(self, obj):
        colors = {
            'MPESA': 'green',
            'PAYPAL': 'blue'
        }
        icons = {
            'MPESA': '📱',
            'PAYPAL': '💳'
        }
        color = colors.get(obj.payment_method, 'gray')
        icon = icons.get(obj.payment_method, '💰')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_payment_method_display()
        )
    payment_method_badge.short_description = 'Payment Method'

    def status_badge(self, obj):
        colors = {
            'COMPLETED': 'green',
            'PENDING': 'orange',
            'FAILED': 'red',
            'CANCELLED': 'gray'
        }
        icons = {
            'COMPLETED': '✅',
            'PENDING': '⏳',
            'FAILED': '❌',
            'CANCELLED': '🚫'
        }
        color = colors.get(obj.status, 'gray')
        icon = icons.get(obj.status, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def transaction_preview(self, obj):
        if obj.transaction_id:
            preview = obj.transaction_id[:20] + '...' if len(obj.transaction_id) > 20 else obj.transaction_id
            return format_html('<code title="{}">🔗 {}</code>', obj.transaction_id, preview)
        return "—"
    transaction_preview.short_description = 'Transaction ID'

    def time_since_created(self, obj):
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    time_since_created.short_description = 'Time Since'

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(
            request, 
            f'Successfully marked {updated} transaction(s) as completed.',
            messages.SUCCESS
        )
    mark_as_completed.short_description = "✅ Mark selected as COMPLETED"

    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='FAILED')
        self.message_user(
            request, 
            f'Successfully marked {updated} transaction(s) as failed.',
            messages.SUCCESS
        )
    mark_as_failed.short_description = "❌ Mark selected as FAILED"

    def resend_notifications(self, request, queryset):
        count = 0
        for transaction in queryset:
            if transaction.status == 'COMPLETED':
                Notification.objects.create(
                    user=transaction.user,
                    title='Payment Completed',
                    message=f'Your payment of ${transaction.amount} for {transaction.signal.symbol} signal has been processed successfully.',
                    notification_type='SUCCESS'
                )
                count += 1
        
        self.message_user(
            request,
            f'Successfully re-sent {count} notification(s) for completed transactions.',
            messages.SUCCESS
        )
    resend_notifications.short_description = "📧 Resend notifications for completed"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'is_trader_badge', 'trader_application_status_badge',
        'video_call_enabled_badge', 'screen_sharing_enabled_badge',
        'date_joined', 'last_login'
    ]
    list_filter = ['is_trader', 'trader_application_status', 'video_call_enabled', 'screen_sharing_enabled', 'created_at']
    search_fields = ['user__username', 'user__email', 'trader_experience', 'trader_specialization']
    readonly_fields = ['user_link', 'is_trader_badge', 'trader_application_status_badge', 'date_joined', 'last_login']
    list_per_page = 20
    actions = ['approve_trader_applications', 'reject_trader_applications', 'enable_video_calls', 'disable_video_calls']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_link', 'date_joined', 'last_login')
        }),
        ('Profile Information', {
            'fields': ('profile_picture', 'mpesa_number', 'paypal_email', 'phone_number', 'country', 'city', 'date_of_birth', 'bio')
        }),
        ('Social Media', {
            'fields': ('twitter_url', 'linkedin_url', 'youtube_url'),
            'classes': ('collapse',)
        }),
        ('Trading Preferences', {
            'fields': ('preferred_markets', 'trading_experience'),
            'classes': ('collapse',)
        }),
        ('Video Call Settings', {
            'fields': ('video_call_enabled', 'screen_sharing_enabled', 'max_participants'),
            'classes': ('collapse',)
        }),
        ('Privacy Settings', {
            'fields': ('show_email', 'show_phone', 'show_trading_stats'),
            'classes': ('collapse',)
        }),
        ('Trader Application', {
            'fields': ('is_trader', 'is_trader_badge', 'trader_application_status', 'trader_application_status_badge', 
                      'trader_application_date', 'trader_approval_date', 'trader_application_feedback')
        }),
        ('Trader Details', {
            'fields': ('trader_bio', 'trader_experience', 'trader_specialization'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_trades', 'successful_trades', 'total_profit', 'follower_count', 'following_count'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">👤 {}</a>', url, obj.user.username)
    user_link.short_description = 'User'

    def is_trader_badge(self, obj):
        if obj.is_trader:
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">✅ VERIFIED TRADER</span>'
            )
        elif obj.trader_application_status == 'PENDING':
            return format_html(
                '<span style="background-color: orange; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">⏳ PENDING REVIEW</span>'
            )
        elif obj.trader_application_status == 'REJECTED':
            return format_html(
                '<span style="background-color: red; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">❌ REJECTED</span>'
            )
        else:
            return format_html(
                '<span style="background-color: gray; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">👤 STANDARD USER</span>'
            )
    is_trader_badge.short_description = 'Trader Status'

    def trader_application_status_badge(self, obj):
        colors = {
            'NOT_APPLIED': 'gray',
            'PENDING': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red'
        }
        icons = {
            'NOT_APPLIED': '📝',
            'PENDING': '⏳',
            'APPROVED': '✅',
            'REJECTED': '❌'
        }
        color = colors.get(obj.trader_application_status, 'gray')
        icon = icons.get(obj.trader_application_status, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_trader_application_status_display()
        )
    trader_application_status_badge.short_description = 'Application Status'

    def video_call_enabled_badge(self, obj):
        if obj.video_call_enabled:
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🎥 ENABLED</span>'
            )
        return format_html(
            '<span style="background-color: red; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🚫 DISABLED</span>'
        )
    video_call_enabled_badge.short_description = 'Video Calls'

    def screen_sharing_enabled_badge(self, obj):
        if obj.screen_sharing_enabled:
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🖥️ ENABLED</span>'
            )
        return format_html(
            '<span style="background-color: red; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🚫 DISABLED</span>'
        )
    screen_sharing_enabled_badge.short_description = 'Screen Sharing'

    def date_joined(self, obj):
        return obj.user.date_joined.strftime('%Y-%m-%d %H:%M')
    date_joined.short_description = 'Date Joined'

    def last_login(self, obj):
        if obj.user.last_login:
            return obj.user.last_login.strftime('%Y-%m-%d %H:%M')
        return "Never"
    last_login.short_description = 'Last Login'

    def approve_trader_applications(self, request, queryset):
        approved_count = 0
        for profile in queryset:
            if not profile.is_trader and profile.trader_application_status == 'PENDING':
                profile.is_trader = True
                profile.trader_application_status = 'APPROVED'
                profile.trader_approval_date = timezone.now()
                profile.save()
                approved_count += 1
                
                Notification.objects.create(
                    user=profile.user,
                    title='Trader Application Approved! 🎉',
                    message='Congratulations! Your trader application has been approved. You can now host live trading sessions and share your expertise with the community.',
                    notification_type='SUCCESS'
                )
        
        if approved_count > 0:
            self.message_user(
                request, 
                f'Successfully approved {approved_count} trader application(s). Users have been notified.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'No pending applications were found in the selected items.',
                messages.WARNING
            )
    approve_trader_applications.short_description = "✅ Approve selected trader applications"

    def reject_trader_applications(self, request, queryset):
        rejected_count = 0
        for profile in queryset:
            if profile.trader_application_status == 'PENDING':
                profile.trader_application_status = 'REJECTED'
                profile.trader_application_feedback = "Application rejected by administrator. Please contact support for more information."
                profile.save()
                rejected_count += 1
                
                Notification.objects.create(
                    user=profile.user,
                    title='Trader Application Update',
                    message='Your trader application requires additional review. Please contact our support team for more information about improving your application.',
                    notification_type='WARNING'
                )
        
        if rejected_count > 0:
            self.message_user(
                request, 
                f'Successfully rejected {rejected_count} trader application(s). Users have been notified.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'No pending applications were found in the selected items.',
                messages.WARNING
            )
    reject_trader_applications.short_description = "❌ Reject selected trader applications"

    def enable_video_calls(self, request, queryset):
        updated = queryset.update(video_call_enabled=True)
        self.message_user(
            request,
            f'Successfully enabled video calls for {updated} user(s).',
            messages.SUCCESS
        )
    enable_video_calls.short_description = "🎥 Enable video calls"

    def disable_video_calls(self, request, queryset):
        updated = queryset.update(video_call_enabled=False)
        self.message_user(
            request,
            f'Successfully disabled video calls for {updated} user(s).',
            messages.SUCCESS
        )
    disable_video_calls.short_description = "🚫 Disable video calls"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return list(self.readonly_fields) + ['user']
        return self.readonly_fields


@admin.register(VideoCallRoom)
class VideoCallRoomAdmin(admin.ModelAdmin):
    list_display = [
        'room_name', 'room_id', 'created_by_link', 'room_type_badge', 
        'is_active_badge', 'participant_count', 'created_at', 'duration'
    ]
    list_filter = ['room_type', 'is_active', 'created_at', 'allow_screen_share', 'allow_recording']
    search_fields = ['room_name', 'room_id', 'created_by__username']
    readonly_fields = ['created_at', 'started_at', 'ended_at', 'room_id', 'participant_count']
    list_per_page = 20
    date_hierarchy = 'created_at'
    actions = ['mark_as_active', 'mark_as_inactive', 'end_selected_rooms']
    
    fieldsets = (
        ('Room Information', {
            'fields': ('created_by', 'room_name', 'room_id', 'room_type', 'is_active')
        }),
        ('Settings', {
            'fields': ('max_participants', 'allow_screen_share', 'allow_recording')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'ended_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('participant_count',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')

    def created_by_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.created_by.id])
        return format_html('<a href="{}">👤 {}</a>', url, obj.created_by.username)
    created_by_link.short_description = 'Created By'

    def room_type_badge(self, obj):
        colors = {
            'PRIVATE': 'blue',
            'PUBLIC': 'green',
            'GROUP': 'purple'
        }
        icons = {
            'PRIVATE': '🔒',
            'PUBLIC': '🌍',
            'GROUP': '👥'
        }
        color = colors.get(obj.room_type, 'gray')
        icon = icons.get(obj.room_type, '🎥')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_room_type_display()
        )
    room_type_badge.short_description = 'Room Type'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🔴 LIVE</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">⚫ ENDED</span>'
        )
    is_active_badge.short_description = 'Status'

    def participant_count(self, obj):
        count = obj.get_participants_count()
        url = (
            reverse("admin:frontend_videocallparticipant_changelist")
            + "?"
            + urlencode({"room__id": f"{obj.id}"})
        )
        return format_html('<a href="{}" title="View participants">👥 {}</a>', url, count)
    participant_count.short_description = 'Participants'

    def duration(self, obj):
        if obj.started_at and obj.ended_at:
            duration = obj.ended_at - obj.started_at
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif obj.started_at:
            duration = timezone.now() - obj.started_at
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s (ongoing)"
        return "—"
    duration.short_description = 'Duration'

    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True, started_at=timezone.now())
        self.message_user(
            request,
            f'Successfully activated {updated} video call room(s).',
            messages.SUCCESS
        )
    mark_as_active.short_description = "🔴 Activate selected rooms"

    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False, ended_at=timezone.now())
        self.message_user(
            request,
            f'Successfully deactivated {updated} video call room(s).',
            messages.SUCCESS
        )
    mark_as_inactive.short_description = "⚫ Deactivate selected rooms"

    def end_selected_rooms(self, request, queryset):
        for room in queryset:
            if room.is_active:
                VideoCallParticipant.objects.filter(
                    room=room,
                    left_at__isnull=True
                ).update(left_at=timezone.now())
                room.is_active = False
                room.ended_at = timezone.now()
                room.save()
        
        self.message_user(
            request,
            f'Successfully ended {queryset.count()} active video call room(s).',
            messages.SUCCESS
        )
    end_selected_rooms.short_description = "🛑 End selected rooms (with participants)"


@admin.register(VideoCallParticipant)
class VideoCallParticipantAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'room_link', 'status_badge', 'joined_at', 
        'left_at', 'duration', 'is_screen_sharing_badge'
    ]
    list_filter = ['is_screen_sharing', 'is_muted', 'is_video_off', 'joined_at']
    search_fields = ['user__username', 'room__room_name']
    readonly_fields = ['joined_at', 'left_at']
    list_per_page = 20
    
    def room_link(self, obj):
        url = reverse("admin:frontend_videocallroom_change", args=[obj.room.id])
        return format_html('<a href="{}">🎥 {}</a>', url, obj.room.room_name)
    room_link.short_description = 'Room'

    def status_badge(self, obj):
        if obj.left_at:
            return format_html(
                '<span style="background-color: gray; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">👋 LEFT</span>'
            )
        else:
            status_parts = []
            if obj.is_muted:
                status_parts.append('🔇')
            if obj.is_video_off:
                status_parts.append('📷')
            if not status_parts:
                status_parts.append('🎤')
            
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
                ' '.join(status_parts)
            )
    status_badge.short_description = 'Status'

    def is_screen_sharing_badge(self, obj):
        if obj.is_screen_sharing:
            return format_html(
                '<span style="background-color: blue; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🖥️ SHARING</span>'
            )
        return "—"
    is_screen_sharing_badge.short_description = 'Screen Share'

    def duration(self, obj):
        if obj.joined_at:
            end_time = obj.left_at or timezone.now()
            duration = end_time - obj.joined_at
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        return "—"
    duration.short_description = 'Duration'


@admin.register(VideoCallRecording)
class VideoCallRecordingAdmin(admin.ModelAdmin):
    list_display = ['room_link', 'file_size_mb', 'duration', 'created_at']
    list_filter = ['created_at']
    search_fields = ['room__room_name']
    readonly_fields = ['created_at']
    
    def room_link(self, obj):
        url = reverse("admin:frontend_videocallroom_change", args=[obj.room.id])
        return format_html('<a href="{}">🎥 {}</a>', url, obj.room.room_name)
    room_link.short_description = 'Room'

    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{(obj.file_size / (1024 * 1024)):.2f} MB"
        return "—"
    file_size_mb.short_description = 'File Size'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'title', 'notification_type_badge', 'is_read_badge', 
        'created_at', 'notification_preview', 'safe_time_ago'
    ]
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'safe_time_ago']
    list_per_page = 20
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread', 'delete_old_notifications']
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('user', 'title', 'message', 'notification_type', 'is_read')
        }),
        ('Metadata', {
            'fields': ('created_at', 'safe_time_ago'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">👤 {}</a>', url, obj.user.username)
    user_link.short_description = 'User'

    def safe_time_ago(self, obj):
        try:
            return obj.get_time_ago()
        except (TypeError, AttributeError):
            return "Recently"
    safe_time_ago.short_description = 'Time Ago'

    def notification_type_badge(self, obj):
        colors = {
            'INFO': 'blue',
            'SUCCESS': 'green',
            'WARNING': 'orange',
            'ERROR': 'red',
            'ALERT': 'purple'
        }
        icons = {
            'INFO': 'ℹ️',
            'SUCCESS': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'ALERT': '🚨'
        }
        color = colors.get(obj.notification_type, 'gray')
        icon = icons.get(obj.notification_type, '📢')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'

    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">📖 READ</span>'
            )
        return format_html(
            '<span style="background-color: orange; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">📝 UNREAD</span>'
        )
    is_read_badge.short_description = 'Read Status'

    def notification_preview(self, obj):
        preview = obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
        return format_html('<span title="{}" style="font-size: 12px;">💬 {}</span>', obj.message, preview)
    notification_preview.short_description = 'Message Preview'

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(
            request, 
            f'Successfully marked {updated} notification(s) as read.',
            messages.SUCCESS
        )
    mark_as_read.short_description = "📖 Mark selected as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(
            request, 
            f'Successfully marked {updated} notification(s) as unread.',
            messages.SUCCESS
        )
    mark_as_unread.short_description = "📝 Mark selected as unread"

    def delete_old_notifications(self, request, queryset):
        cutoff_date = timezone.now() - timedelta(days=30)
        old_notifications = Notification.objects.filter(created_at__lt=cutoff_date)
        count = old_notifications.count()
        old_notifications.delete()
        
        self.message_user(
            request,
            f'Successfully deleted {count} notification(s) older than 30 days.',
            messages.SUCCESS
        )
    delete_old_notifications.short_description = "🗑️ Delete notifications older than 30 days"


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'trader_link', 'session_type_badge', 'status_badge', 
        'scheduled_start', 'scheduled_end', 'participant_count', 'is_public_badge'
    ]
    list_filter = ['session_type', 'status', 'is_public', 'scheduled_start']
    search_fields = ['title', 'trader__username', 'description']
    readonly_fields = ['created_at', 'updated_at', 'room_id', 'participant_count']
    date_hierarchy = 'scheduled_start'
    actions = ['mark_as_live', 'mark_as_ended', 'mark_as_cancelled']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('trader', 'title', 'description', 'session_type', 'status', 'is_public')
        }),
        ('Schedule', {
            'fields': ('scheduled_start', 'scheduled_end', 'actual_start', 'actual_end')
        }),
        ('Participants', {
            'fields': ('max_participants', 'participant_count'),
            'classes': ('collapse',)
        }),
        ('Technical', {
            'fields': ('room_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        if 'trader' in form.base_fields:
            form.base_fields['trader'].queryset = User.objects.filter(
                userprofile__is_trader=True
            ).select_related('userprofile')
            form.base_fields['trader'].label_from_instance = lambda obj: f"{obj.username} ({obj.get_full_name() or obj.email}) - Trader"
        
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "trader":
            kwargs["queryset"] = User.objects.filter(
                userprofile__is_trader=True
            ).select_related('userprofile').order_by('username')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def trader_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.trader.id])
        return format_html('<a href="{}">👤 {}</a>', url, obj.trader.username)
    trader_link.short_description = 'Trader'

    def participant_count(self, obj):
        count = obj.participants.count()
        url = (
            reverse("admin:frontend_sessionparticipant_changelist")
            + "?"
            + urlencode({"session__id": f"{obj.id}"})
        )
        return format_html('<a href="{}" title="View participants">👥 {}</a>', url, count)
    participant_count.short_description = 'Participants'

    def session_type_badge(self, obj):
        colors = {
            'TRADING': 'red',
            'QNA': 'blue',
            'EDUCATION': 'green',
            'MARKET_ANALYSIS': 'purple'
        }
        icons = {
            'TRADING': '📈',
            'QNA': '❓',
            'EDUCATION': '🎓',
            'MARKET_ANALYSIS': '🔍'
        }
        color = colors.get(obj.session_type, 'gray')
        icon = icons.get(obj.session_type, '📺')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_session_type_display()
        )
    session_type_badge.short_description = 'Type'

    def status_badge(self, obj):
        colors = {
            'SCHEDULED': 'blue',
            'LIVE': 'green',
            'ENDED': 'gray',
            'CANCELLED': 'red'
        }
        icons = {
            'SCHEDULED': '⏰',
            'LIVE': '🔴',
            'ENDED': '✅',
            'CANCELLED': '❌'
        }
        color = colors.get(obj.status, 'gray')
        icon = icons.get(obj.status, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def is_public_badge(self, obj):
        if obj.is_public:
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🌍 PUBLIC</span>'
            )
        return format_html(
            '<span style="background-color: orange; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">🔒 PRIVATE</span>'
        )
    is_public_badge.short_description = 'Visibility'

    def mark_as_live(self, request, queryset):
        updated = queryset.update(status='LIVE', actual_start=timezone.now())
        self.message_user(
            request, 
            f'Successfully marked {updated} session(s) as live.',
            messages.SUCCESS
        )
    mark_as_live.short_description = "🔴 Mark selected as LIVE"

    def mark_as_ended(self, request, queryset):
        updated = queryset.update(status='ENDED', actual_end=timezone.now())
        self.message_user(
            request, 
            f'Successfully marked {updated} session(s) as ended.',
            messages.SUCCESS
        )
    mark_as_ended.short_description = "✅ Mark selected as ENDED"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(
            request, 
            f'Successfully marked {updated} session(s) as cancelled.',
            messages.SUCCESS
        )
    mark_as_cancelled.short_description = "❌ Mark selected as CANCELLED"


@admin.register(SessionParticipant)
class SessionParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_link', 'role_badge', 'joined_at', 'left_at', 'is_active_badge']
    list_filter = ['role', 'is_active', 'joined_at']
    search_fields = ['user__username', 'session__title']
    readonly_fields = ['joined_at']
    
    def session_link(self, obj):
        url = reverse("admin:frontend_livesession_change", args=[obj.session.id])
        return format_html('<a href="{}">📺 {}</a>', url, obj.session.title)
    session_link.short_description = 'Session'

    def role_badge(self, obj):
        colors = {
            'TRADER': 'red',
            'MODERATOR': 'orange',
            'PARTICIPANT': 'blue',
            'VIEWER': 'gray'
        }
        icons = {
            'TRADER': '👑',
            'MODERATOR': '🛡️',
            'PARTICIPANT': '💬',
            'VIEWER': '👀'
        }
        color = colors.get(obj.role, 'gray')
        icon = icons.get(obj.role, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_role_display()
        )
    role_badge.short_description = 'Role'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">✅ ACTIVE</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">❌ INACTIVE</span>'
        )
    is_active_badge.short_description = 'Active'


@admin.register(SessionMessage)
class SessionMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_link', 'message_type_badge', 'content_preview', 'created_at', 'is_pinned_badge']
    list_filter = ['message_type', 'is_pinned', 'created_at']
    search_fields = ['user__username', 'content', 'session__title']
    readonly_fields = ['created_at']
    
    def session_link(self, obj):
        url = reverse("admin:frontend_livesession_change", args=[obj.session.id])
        return format_html('<a href="{}">📺 {}</a>', url, obj.session.title)
    session_link.short_description = 'Session'

    def content_preview(self, obj):
        preview = obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        return format_html('<span title="{}">{}</span>', obj.content, preview)
    content_preview.short_description = 'Message'

    def message_type_badge(self, obj):
        colors = {
            'TEXT': 'gray',
            'TRADE_IDEA': 'green',
            'ANNOUNCEMENT': 'blue',
            'QUESTION': 'orange',
            'ANSWER': 'purple'
        }
        icons = {
            'TEXT': '💬',
            'TRADE_IDEA': '💡',
            'ANNOUNCEMENT': '📢',
            'QUESTION': '❓',
            'ANSWER': '💡'
        }
        color = colors.get(obj.message_type, 'gray')
        icon = icons.get(obj.message_type, '💬')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_message_type_display()
        )
    message_type_badge.short_description = 'Type'

    def is_pinned_badge(self, obj):
        if obj.is_pinned:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">📌 PINNED</span>'
            )
        return "—"
    is_pinned_badge.short_description = 'Pinned'


@admin.register(SessionTradeIdea)
class SessionTradeIdeaAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'idea_type_badge', 'trader', 'session_link', 'entry_price', 'target_price', 'is_active', 'created_at']
    list_filter = ['idea_type', 'is_active', 'created_at']
    search_fields = ['symbol', 'trader__username', 'session__title']
    date_hierarchy = 'created_at'
    
    def session_link(self, obj):
        url = reverse("admin:frontend_livesession_change", args=[obj.session.id])
        return format_html('<a href="{}">📺 {}</a>', url, obj.session.title)
    session_link.short_description = 'Session'

    def idea_type_badge(self, obj):
        colors = {
            'BUY': 'green',
            'SELL': 'red',
            'HOLD': 'gray',
            'WATCH': 'blue'
        }
        icons = {
            'BUY': '📈',
            'SELL': '📉',
            'HOLD': '🤚',
            'WATCH': '👀'
        }
        color = colors.get(obj.idea_type, 'gray')
        icon = icons.get(obj.idea_type, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_idea_type_display()
        )               
    idea_type_badge.short_description = 'Type'
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'


@admin.register(SessionRecording)
class SessionRecordingAdmin(admin.ModelAdmin):
    list_display = ['session_link', 'duration', 'file_size_mb', 'created_at']
    list_filter = ['created_at']
    search_fields = ['session__title']
    readonly_fields = ['created_at']
    
    def session_link(self, obj):
        url = reverse("admin:frontend_livesession_change", args=[obj.session.id])
        return format_html('<a href="{}">📺 {}</a>', url, obj.session.title)
    session_link.short_description = 'Session'

    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{(obj.file_size / (1024 * 1024)):.2f} MB"
        return "—"
    file_size_mb.short_description = 'File Size'