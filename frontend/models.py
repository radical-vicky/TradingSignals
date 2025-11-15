from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class Signal(models.Model):
    SIGNAL_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('PENDING', 'Pending'),
    ]
    
    symbol = models.CharField(max_length=50)
    signal_type = models.CharField(max_length=10, choices=SIGNAL_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    entry_price = models.DecimalField(max_digits=10, decimal_places=2)
    take_profit_1 = models.DecimalField(max_digits=10, decimal_places=2)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, help_text="Price in USD for purchasing this signal")
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'frontend_signal'
    
    def __str__(self):
        return f"{self.symbol} {self.signal_type} - ${self.price}"

class SignalPurchase(models.Model):
    PAYMENT_METHODS = [
        ('PAYPAL', 'PayPal'),
        ('MPESA', 'M-Pesa'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Actual amount paid")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'frontend_signalpurchase'
        unique_together = ['user', 'signal']
    
    def __str__(self):
        return f"{self.user.username} - {self.signal.symbol} - ${self.amount}"

class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('MPESA', 'M-Pesa'),
        ('PAYPAL', 'PayPal'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    merchant_request_id = models.CharField(max_length=255, blank=True, null=True)  # For M-Pesa
    checkout_request_id = models.CharField(max_length=255, blank=True, null=True)  # For M-Pesa
    paypal_order_id = models.CharField(max_length=255, blank=True, null=True)  # For PayPal
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # For M-Pesa
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'frontend_paymenttransaction'
    
    def __str__(self):
        return f"{self.user.username} - {self.payment_method} - ${self.amount}"





class UserProfile(models.Model):
    TRADER_STATUS_CHOICES = [
        ('NOT_APPLIED', 'Not Applied'),
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    TRADING_EXPERIENCE_CHOICES = [
        ('BEGINNER', 'Beginner (0-1 years)'),
        ('INTERMEDIATE', 'Intermediate (1-3 years)'),
        ('ADVANCED', 'Advanced (3+ years)'),
        ('PROFESSIONAL', 'Professional (5+ years)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        null=True, 
        blank=True,
        default='profile_pics/default.png'
    )
    mpesa_number = models.CharField(max_length=15, blank=True, default='')
    paypal_email = models.EmailField(blank=True, default='')
    
    # Enhanced profile fields
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(
        blank=True, 
        null=True, 
        max_length=500,
        help_text="Brief introduction about yourself (max 500 characters)"
    )
    
    # Social media links
    twitter_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    
    # Trading preferences
    preferred_markets = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="Preferred trading markets (e.g., Forex, Crypto, Stocks)"
    )
    trading_experience = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        choices=TRADING_EXPERIENCE_CHOICES
    )
    
    # Privacy settings
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)
    show_trading_stats = models.BooleanField(default=True)
    
    # Statistics
    total_trades = models.PositiveIntegerField(default=0)
    successful_trades = models.PositiveIntegerField(default=0)
    total_profit = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.00
    )
    follower_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    
    # Video call settings
    video_call_enabled = models.BooleanField(default=True)
    screen_sharing_enabled = models.BooleanField(default=True)
    max_participants = models.PositiveIntegerField(
        default=10, 
        help_text="Maximum participants for video calls"
    )
    
    # Trader fields
    is_trader = models.BooleanField(
        default=False, 
        help_text="Designates if this user is a trader who can host live sessions"
    )
    trader_application_status = models.CharField(
        max_length=20, 
        choices=TRADER_STATUS_CHOICES, 
        default='NOT_APPLIED'
    )
    trader_application_date = models.DateTimeField(null=True, blank=True)
    trader_approval_date = models.DateTimeField(null=True, blank=True)
    trader_application_feedback = models.TextField(
        blank=True, 
        null=True, 
        help_text="Feedback for rejected applications"
    )
    
    trader_bio = models.TextField(
        blank=True, 
        null=True, 
        max_length=1000,
        help_text="Trader's biography and expertise (max 1000 characters)"
    )
    trader_experience = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="e.g., 5+ years in Forex Trading"
    )
    trader_specialization = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="e.g., Forex, Crypto, Stocks, Options"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'frontend_userprofile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate date of birth
        if self.date_of_birth:
            if self.date_of_birth > timezone.now().date():
                raise ValidationError({'date_of_birth': 'Date of birth cannot be in the future.'})
            
            # Check if user is at least 18 years old
            age = (timezone.now().date() - self.date_of_birth).days // 365
            if age < 18:
                raise ValidationError({'date_of_birth': 'You must be at least 18 years old.'})
        
        # Validate trader fields if applying as trader
        if self.trader_application_status in ['PENDING', 'APPROVED']:
            if not self.trader_experience:
                raise ValidationError({
                    'trader_experience': 'Trading experience is required for trader applications.'
                })
            if not self.trader_specialization:
                raise ValidationError({
                    'trader_specialization': 'Trading specialization is required for trader applications.'
                })
    
    def save(self, *args, **kwargs):
        """Custom save method to handle profile picture and trader status"""
        
        # Handle profile picture deletion when updating
        if self.pk:
            try:
                old_profile = UserProfile.objects.get(pk=self.pk)
                if (old_profile.profile_picture and 
                    self.profile_picture != old_profile.profile_picture and
                    old_profile.profile_picture.name != 'profile_pics/default.png'):
                    # Delete old profile picture file
                    if os.path.isfile(old_profile.profile_picture.path):
                        os.remove(old_profile.profile_picture.path)
            except UserProfile.DoesNotExist:
                pass
        
        # Set trader application date when status changes to PENDING
        if (self.trader_application_status == 'PENDING' and 
            self._state.adding or 
            (self.pk and 
             UserProfile.objects.get(pk=self.pk).trader_application_status != 'PENDING')):
            self.trader_application_date = timezone.now()
        
        # Set approval date when status changes to APPROVED
        if (self.trader_application_status == 'APPROVED' and 
            self.pk and 
            UserProfile.objects.get(pk=self.pk).trader_application_status != 'APPROVED'):
            self.trader_approval_date = timezone.now()
            self.is_trader = True
        
        # Set is_trader to False if rejected
        if (self.trader_application_status == 'REJECTED' and 
            self.pk and 
            UserProfile.objects.get(pk=self.pk).trader_application_status != 'REJECTED'):
            self.is_trader = False
        
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
    
    def get_success_rate(self):
        """Calculate trading success rate"""
        if self.total_trades > 0:
            return round((self.successful_trades / self.total_trades) * 100, 2)
        return 0.00
    
    def get_average_profit(self):
        """Calculate average profit per trade"""
        if self.total_trades > 0:
            return round(float(self.total_profit) / self.total_trades, 2)
        return 0.00
    
    def can_host_video_calls(self):
        """Check if user can host video calls"""
        return self.video_call_enabled and (self.is_trader or self.follower_count >= 10)
    
    def can_create_live_sessions(self):
        """Check if user can create live sessions"""
        return self.is_trader
    
    def apply_as_trader(self, experience, specialization, trader_bio=""):
        """Apply to become a trader"""
        if self.trader_application_status != 'NOT_APPLIED':
            raise ValidationError("You have already applied or are already a trader.")
        
        if not experience or not specialization:
            raise ValidationError("Trading experience and specialization are required.")
        
        self.trader_experience = experience
        self.trader_specialization = specialization
        self.trader_bio = trader_bio
        self.trader_application_status = 'PENDING'
        self.save()
    
    def approve_trader_application(self, feedback=""):
        """Approve trader application"""
        if self.trader_application_status != 'PENDING':
            raise ValidationError("Can only approve pending applications.")
        
        self.trader_application_status = 'APPROVED'
        self.is_trader = True
        self.trader_application_feedback = feedback
        self.save()
    
    def reject_trader_application(self, feedback):
        """Reject trader application"""
        if self.trader_application_status != 'PENDING':
            raise ValidationError("Can only reject pending applications.")
        
        if not feedback:
            raise ValidationError("Feedback is required when rejecting an application.")
        
        self.trader_application_status = 'REJECTED'
        self.is_trader = False
        self.trader_application_feedback = feedback
        self.save()
    
    @property
    def display_name(self):
        """Get display name (full name or username)"""
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def is_eligible_for_trader(self):
        """Check if user is eligible to apply as trader"""
        return (
            self.trader_application_status == 'NOT_APPLIED' and
            self.total_trades >= 10 and
            self.get_success_rate() >= 60 and
            self.follower_count >= 5
        )



class VideoCallRoom(models.Model):
    ROOM_TYPES = [
        ('PRIVATE', 'Private'),
        ('PUBLIC', 'Public'),
        ('GROUP', 'Group'),
    ]
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    room_id = models.CharField(max_length=100, unique=True)
    room_name = models.CharField(max_length=200)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='PRIVATE')
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=10)
    allow_screen_share = models.BooleanField(default=True)
    allow_recording = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'frontend_videocallroom'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.room_name} ({self.room_id})"
    
    def get_participants_count(self):
        return self.participants.filter(left_at__isnull=True).count()
    
    def can_join(self, user):
        """Check if user can join this room"""
        if not self.is_active:
            return False
        if self.get_participants_count() >= self.max_participants:
            return False
        return True

class VideoCallParticipant(models.Model):
    room = models.ForeignKey(VideoCallRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_screen_sharing = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    is_video_off = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'frontend_videocallparticipant'
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user.username} in {self.room.room_name}"

class VideoCallRecording(models.Model):
    room = models.ForeignKey(VideoCallRoom, on_delete=models.CASCADE)
    recording_url = models.URLField(blank=True, null=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'frontend_videocallrecording'
    
    def __str__(self):
        return f"Recording for {self.room.room_name}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('INFO', 'Information'),
        ('SUCCESS', 'Success'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('ALERT', 'New Alert'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='INFO')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'frontend_notification'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def get_time_ago(self):
        """Get human-readable time difference"""
        if not self.created_at:
            return "Recently"
            
        now = timezone.now()
        diff = now - self.created_at
        
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

class LiveSession(models.Model):
    SESSION_STATUS = [
        ('SCHEDULED', 'Scheduled'),
        ('LIVE', 'Live'),
        ('ENDED', 'Ended'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    SESSION_TYPES = [
        ('TRADING', 'Trading Session'),
        ('QNA', 'Q&A Session'),
        ('EDUCATION', 'Educational Session'),
        ('MARKET_ANALYSIS', 'Market Analysis'),
    ]
    
    trader = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Trader/Host")
    title = models.CharField(max_length=200)
    description = models.TextField()
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='TRADING')
    status = models.CharField(max_length=15, choices=SESSION_STATUS, default='SCHEDULED')
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    max_participants = models.PositiveIntegerField(default=100)
    is_public = models.BooleanField(default=True)
    room_id = models.CharField(max_length=50, unique=True, help_text="Unique room identifier for WebRTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'frontend_livesession'
        ordering = ['-scheduled_start']
    
    def __str__(self):
        return f"{self.title} - {self.trader.username}"
    
    def is_live(self):
        return self.status == 'LIVE'
    
    def can_join(self):
        """Check if session can be joined"""
        now = timezone.now()
        return (self.status == 'LIVE' or 
                (self.status == 'SCHEDULED' and now >= self.scheduled_start and now <= self.scheduled_end))
    
    def get_duration(self):
        """Calculate session duration"""
        if self.actual_start and self.actual_end:
            return self.actual_end - self.actual_start
        return None

class SessionParticipant(models.Model):
    ROLE_CHOICES = [
        ('TRADER', 'Trader'),
        ('MODERATOR', 'Moderator'),
        ('PARTICIPANT', 'Participant'),
        ('VIEWER', 'Viewer'),
    ]
    
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='VIEWER')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'frontend_sessionparticipant'
        unique_together = ['session', 'user']
    
    def __str__(self):
        return f"{self.user.username} in {self.session.title}"

class SessionMessage(models.Model):
    MESSAGE_TYPES = [
        ('TEXT', 'Text Message'),
        ('TRADE_IDEA', 'Trade Idea'),
        ('ANNOUNCEMENT', 'Announcement'),
        ('QUESTION', 'Question'),
        ('ANSWER', 'Answer'),
    ]
    
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message_type = models.CharField(max_length=15, choices=MESSAGE_TYPES, default='TEXT')
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'frontend_sessionmessage'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}..."

class SessionTradeIdea(models.Model):
    IDEA_TYPES = [
        ('BUY', 'Buy Recommendation'),
        ('SELL', 'Sell Recommendation'),
        ('HOLD', 'Hold Recommendation'),
        ('WATCH', 'Watchlist Addition'),
    ]
    
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='trade_ideas')
    trader = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=50)
    idea_type = models.CharField(max_length=10, choices=IDEA_TYPES)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rationale = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'frontend_sessiontradeidea'
    
    def __str__(self):
        return f"{self.symbol} {self.idea_type} by {self.trader.username}"

class SessionRecording(models.Model):
    session = models.OneToOneField(LiveSession, on_delete=models.CASCADE, related_name='recording')
    video_url = models.URLField(blank=True, null=True)
    audio_url = models.URLField(blank=True, null=True)
    transcript = models.TextField(blank=True, null=True)
    duration = models.DurationField(null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'frontend_sessionrecording'
    
    def __str__(self):
        return f"Recording for {self.session.title}"

# Signal receivers
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

@receiver(post_save, sender=Signal)
def create_signal_notification(sender, instance, created, **kwargs):
    """Create notification when a new signal is created"""
    if created:
        users = User.objects.all()
        
        for user in users:
            Notification.objects.create(
                user=user,
                title='New Trading Signal Available',
                message=f'A new {instance.signal_type} signal for {instance.symbol} is now available.',
                notification_type='ALERT'
            )

@receiver(post_save, sender=LiveSession)
def create_session_notification(sender, instance, created, **kwargs):
    """Create notification when a new live session is scheduled"""
    if created and instance.is_public:
        users = User.objects.all()
        
        for user in users:
            Notification.objects.create(
                user=user,
                title='New Live Trading Session',
                message=f'Trader {instance.trader.username} has scheduled a live session: {instance.title}',
                notification_type='ALERT'
            )

@receiver(post_save, sender=LiveSession)
def update_session_status(sender, instance, **kwargs):
    """Automatically update session status based on time"""
    now = timezone.now()
    
    if instance.status == 'SCHEDULED' and now >= instance.scheduled_start:
        instance.status = 'LIVE'
        instance.actual_start = now
        instance.save(update_fields=['status', 'actual_start'])
    
    elif instance.status == 'LIVE' and now >= instance.scheduled_end:
        instance.status = 'ENDED'
        instance.actual_end = now
        instance.save(update_fields=['status', 'actual_end'])