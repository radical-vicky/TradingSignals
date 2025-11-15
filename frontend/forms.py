from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import UserProfile, SignalPurchase, PaymentTransaction, Notification, LiveSession, SessionMessage, SessionTradeIdea, VideoCallRoom, VideoCallParticipant


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class EnhancedUserProfileForm(forms.ModelForm):
    apply_as_trader = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Apply to become a trader"
    )

    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'mpesa_number', 'paypal_email', 'phone_number',
            'country', 'city', 'date_of_birth', 'bio', 'twitter_url', 
            'linkedin_url', 'youtube_url', 'preferred_markets', 'trading_experience',
            'show_email', 'show_phone', 'show_trading_stats', 'video_call_enabled',
            'screen_sharing_enabled', 'max_participants', 'trader_bio', 
            'trader_experience', 'trader_specialization'
        ]
        widgets = {
            'mpesa_number': forms.TextInput(attrs={
                'placeholder': 'e.g., 254712345678',
                'class': 'form-control'
            }),
            'paypal_email': forms.EmailInput(attrs={
                'placeholder': 'your-email@example.com',
                'class': 'form-control'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your country'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your city'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'twitter_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/username'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/username'
            }),
            'youtube_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/c/username'
            }),
            'preferred_markets': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Forex, Crypto, Stocks'
            }),
            'trader_bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about your trading experience and expertise...'
            }),
            'trader_experience': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 5+ years in Forex Trading'
            }),
            'trader_specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Forex, Crypto, Stocks, Options'
            }),
            'trading_experience': forms.Select(attrs={
                'class': 'form-control'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'show_email': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'show_phone': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'show_trading_stats': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'video_call_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'screen_sharing_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.cleaned_data.get('apply_as_trader') and not instance.is_trader:
            if instance.trader_application_status != 'PENDING':
                instance.trader_application_status = 'PENDING'
                instance.trader_application_date = timezone.now()
        
        if commit:
            instance.save()
        return instance

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture']
    
    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Check file size (max 5MB)
            if picture.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 5MB )")
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif']
            extension = picture.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise forms.ValidationError("Unsupported file extension. Supported: JPG, JPEG, PNG, GIF")
        
        return picture


class VideoCallRoomForm(forms.ModelForm):
    class Meta:
        model = VideoCallRoom
        fields = ['room_name', 'room_type', 'max_participants', 'allow_screen_share', 'allow_recording']
        widgets = {
            'room_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter room name...'
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'allow_screen_share': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allow_recording': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_max_participants(self):
        max_participants = self.cleaned_data.get('max_participants')
        if self.user:
            user_profile = UserProfile.objects.get(user=self.user)
            if max_participants > user_profile.max_participants:
                raise forms.ValidationError(
                    f"You can only host up to {user_profile.max_participants} participants. "
                    "Upgrade your account to host more participants."
                )
        return max_participants


class SignalPurchaseForm(forms.Form):
    PAYMENT_METHODS = [
        ('MPESA', 'M-Pesa'),
        ('PAYPAL', 'PayPal'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'payment-option'}),
        required=True,
        error_messages={'required': 'Please select a payment method'}
    )
class PaymentTransactionForm(forms.ModelForm):
    class Meta:
        model = PaymentTransaction
        fields = ['payment_method', 'amount', 'phone_number']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '254712345678'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.signal = kwargs.pop('signal', None)
        super().__init__(*args, **kwargs)
        
        if self.signal:
            self.fields['amount'].initial = self.signal.price
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        payment_method = self.cleaned_data.get('payment_method')
        
        if payment_method == 'MPESA' and not phone_number:
            raise forms.ValidationError("Phone number is required for M-Pesa payments")
        
        if phone_number and payment_method == 'MPESA':
            if not phone_number.startswith('254'):
                raise forms.ValidationError("Phone number should start with 254")
            if len(phone_number) != 12:
                raise forms.ValidationError("Phone number should be 12 digits (including 254)")
            if not phone_number[3:].isdigit():
                raise forms.ValidationError("Phone number should contain only digits after 254")
        
        return phone_number
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.user
        instance.signal = self.signal
        
        if commit:
            instance.save()
        return instance


class LiveSessionForm(forms.ModelForm):
    class Meta:
        model = LiveSession
        fields = ['title', 'description', 'session_type', 'scheduled_start', 'scheduled_end', 'max_participants', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter session title...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe what this session will cover...'
            }),
            'session_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'scheduled_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'scheduled_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 1000
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.trader = kwargs.pop('trader', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_start = cleaned_data.get('scheduled_start')
        scheduled_end = cleaned_data.get('scheduled_end')
        
        if scheduled_start and scheduled_end:
            if scheduled_start >= scheduled_end:
                raise forms.ValidationError("Session end time must be after start time")
            
            if scheduled_start <= timezone.now():
                raise forms.ValidationError("Session start time must be in the future")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.trader:
            instance.trader = self.trader
        instance.room_id = f"room_{timezone.now().strftime('%Y%m%d%H%M%S')}_{self.trader.username}"
        
        if commit:
            instance.save()
        return instance


class SessionMessageForm(forms.ModelForm):
    class Meta:
        model = SessionMessage
        fields = ['content', 'message_type']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...',
                'maxlength': '1000'
            }),
            'message_type': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.session = self.session
        instance.user = self.user
        
        if commit:
            instance.save()
        return instance


class SessionTradeIdeaForm(forms.ModelForm):
    class Meta:
        model = SessionTradeIdea
        fields = ['symbol', 'idea_type', 'entry_price', 'target_price', 'stop_loss', 'rationale']
        widgets = {
            'symbol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BTCUSDT, EURUSD'
            }),
            'idea_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'entry_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'placeholder': 'Optional'
            }),
            'target_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'placeholder': 'Optional'
            }),
            'stop_loss': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'placeholder': 'Optional'
            }),
            'rationale': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain your trade idea...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        self.trader = kwargs.pop('trader', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.session = self.session
        instance.trader = self.trader
        
        if commit:
            instance.save()
        return instance


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Email'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Your Message',
            'rows': 5
        })
    )


class SignalFilterForm(forms.Form):
    SIGNAL_TYPE_CHOICES = [
        ('', 'All Types'),
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('PENDING', 'Pending'),
    ]
    
    signal_type = forms.ChoiceField(
        choices=SIGNAL_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    symbol = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by symbol...'
        })
    )


class LiveSessionFilterForm(forms.Form):
    SESSION_TYPE_CHOICES = [
        ('', 'All Types'),
        ('TRADING', 'Trading Session'),
        ('QNA', 'Q&A Session'),
        ('EDUCATION', 'Educational Session'),
        ('MARKET_ANALYSIS', 'Market Analysis'),
    ]
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('SCHEDULED', 'Scheduled'),
        ('LIVE', 'Live'),
        ('ENDED', 'Ended'),
    ]
    
    session_type = forms.ChoiceField(
        choices=SESSION_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class NotificationSettingsForm(forms.Form):
    EMAIL_NOTIFICATION_CHOICES = [
        ('ALL', 'All Notifications'),
        ('IMPORTANT', 'Important Only'),
        ('NONE', 'No Email Notifications'),
    ]
    
    PUSH_NOTIFICATION_CHOICES = [
        ('ALL', 'All Notifications'),
        ('SIGNALS', 'New Signals Only'),
        ('NONE', 'No Push Notifications'),
    ]
    
    email_notifications = forms.ChoiceField(
        choices=EMAIL_NOTIFICATION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='ALL'
    )
    
    push_notifications = forms.ChoiceField(
        choices=PUSH_NOTIFICATION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='ALL'
    )
    
    notify_new_signals = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Notify me when new signals are available"
    )
    
    notify_payment_status = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Notify me about payment status"
    )
    
    notify_signal_updates = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Notify me about signal updates"
    )
    
    notify_live_sessions = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Notify me about new live sessions"
    )


class MpesaPaymentForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '254712345678',
            'pattern': '254[0-9]{9}',
            'title': 'Enter your M-Pesa number starting with 254'
        })
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number.startswith('254'):
            raise forms.ValidationError("Phone number must start with 254")
        if len(phone_number) != 12:
            raise forms.ValidationError("Phone number must be 12 digits")
        if not phone_number[3:].isdigit():
            raise forms.ValidationError("Phone number must contain only digits after 254")
        return phone_number


class PayPalPaymentForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your-email@example.com'
        })
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )


class PasswordChangeCustomForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Password'
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("New passwords do not match")
        
        return cleaned_data


class BulkSignalUploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv, .xlsx, .xls'
        }),
        help_text="Upload CSV or Excel file with signal data"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            valid_extensions = ['.csv', '.xlsx', '.xls']
            ext = file.name.lower().split('.')[-1]
            if f'.{ext}' not in valid_extensions:
                raise forms.ValidationError("Unsupported file format. Please upload CSV or Excel file.")
        return file