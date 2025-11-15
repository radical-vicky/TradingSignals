# frontend/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('alerts/', views.signal_list, name='alerts'),
    path('signals/', views.signal_list, name='signal_list'),
    path('profile/', views.profile, name='profile'),
    
    # Signal routes
    path('signal/<int:signal_id>/', views.signal_detail, name='signal_detail'),
    path('signal/<int:signal_id>/purchase/', views.purchase_signal, name='purchase_signal'),
    
    # Payment processing routes
    path('payment/process/mpesa/<int:signal_id>/', views.process_mpesa_payment, name='process_mpesa_payment'),
    path('payment/process/paypal/<int:signal_id>/', views.process_paypal_payment, name='process_paypal_payment'),
    
    # Payment gateway routes
    path('payment/mpesa/<int:transaction_id>/', views.initiate_mpesa_payment, name='initiate_mpesa_payment'),
    path('payment/paypal/<int:transaction_id>/', views.initiate_paypal_payment, name='initiate_paypal_payment'),
    path('payment/paypal/success/<int:transaction_id>/', views.paypal_payment_success, name='paypal_payment_success'),
    path('payment/paypal/cancel/<int:transaction_id>/', views.paypal_payment_cancel, name='paypal_payment_cancel'),
    path('payment/status/<int:transaction_id>/', views.payment_status, name='payment_status'),
    path('payment/check-update/<int:transaction_id>/', views.check_and_update_payment, name='check_update_payment'),
    
    # Live Session routes
    path('live-sessions/', views.live_sessions, name='live_sessions'),
    path('live-sessions/create/', views.create_live_session, name='create_live_session'),
    path('live-sessions/<int:session_id>/', views.live_session_detail, name='live_session_detail'),
    path('live-sessions/<int:session_id>/join/', views.join_live_session, name='join_live_session'),
    path('live-sessions/<int:session_id>/leave/', views.leave_live_session, name='leave_live_session'),
    path('live-sessions/<int:session_id>/start/', views.start_live_session, name='start_live_session'),
    path('live-sessions/<int:session_id>/end/', views.end_live_session, name='end_live_session'),
    
    # Live Session API routes
    path('api/live-sessions/<int:session_id>/messages/', views.get_session_messages, name='get_session_messages'),
    path('api/live-sessions/<int:session_id>/participants/', views.get_session_participants, name='get_session_participants'),
    path('api/live-sessions/<int:session_id>/status/', views.api_session_status, name='api_session_status'),
    path('api/live-sessions/<int:session_id>/send-message/', views.send_session_message, name='send_session_message'),
    path('api/live-sessions/<int:session_id>/create-trade-idea/', views.create_trade_idea, name='create_trade_idea'),
    path('api/user-sessions/', views.api_user_sessions, name='api_user_sessions'),
    
    # Video Call routes
    path('video-call/create/', views.create_video_call, name='create_video_call'),
    path('video-call/<str:room_id>/', views.video_call_room, name='video_call_room'),
    path('video-call/<str:room_id>/leave/', views.leave_video_call, name='leave_video_call'),
    path('video-call/<str:room_id>/end/', views.end_video_call, name='end_video_call'),
    path('video-call/<str:room_id>/update-status/', views.update_participant_status, name='update_participant_status'),
    
    # Notification routes
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notifications/count/', views.get_notifications_count, name='get_notifications_count'),
    path('api/notifications/recent/', views.get_recent_notifications, name='get_recent_notifications'),
    
    # Payment API routes
    path('api/mpesa-callback/', views.mpesa_callback, name='mpesa_callback'),
    
   
]