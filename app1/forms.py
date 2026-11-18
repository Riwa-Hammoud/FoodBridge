from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import NGO, Restaurant

MAX_IMAGE_MB = 2
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
CUISINE_CHOICES = [
    ('eastern', 'Eastern food'),
    ('western-eastern', 'Western-Eastern food'),
    ('fast-food', 'Fast Food'),
    ('western', 'Western food'),
]
CAPACITY_CHOICES = [(c, c) for c in ('less than 100', '100-200', '200-500', 'more than 500')]


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    location = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput)
    choice = forms.ChoiceField(choices=[('Restaurant', 'Restaurant'), ('Charity', 'Charity')])

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if User.objects.filter(username__iexact=name).exists():
            raise ValidationError('An account with this name already exists.')
        return name

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if (User.objects.filter(email__iexact=email).exists()
                or Restaurant.objects.filter(contact_email__iexact=email).exists()
                or NGO.objects.filter(contact_email__iexact=email).exists()):
            raise ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        if password:
            candidate = User(username=cleaned.get('name', ''), email=cleaned.get('email', ''))
            try:
                validate_password(password, user=candidate)
            except ValidationError as error:
                self.add_error('password', error)
        return cleaned


class PasswordResetRequestForm(PasswordResetForm):
    email = forms.EmailField(label='Email')


class PasswordResetConfirmationForm(SetPasswordForm):
    new_password1 = forms.CharField(label='New Password', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Confirm New Password', widget=forms.PasswordInput)


class ProfileFormMixin:
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        taken = User.objects.filter(username__iexact=name).exclude(pk=self.instance.user_id)
        if taken.exists():
            raise ValidationError('This name is already taken.')
        return name

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if isinstance(picture, UploadedFile):  # a new upload, not the stored file
            if picture.size > MAX_IMAGE_MB * 1024 * 1024:
                raise ValidationError(f'Image must be smaller than {MAX_IMAGE_MB} MB.')
            if picture.image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError('Use a JPEG, PNG or WebP image.')
        return picture


class RestaurantProfileForm(ProfileFormMixin, forms.ModelForm):
    cuisine_type = forms.ChoiceField(choices=CUISINE_CHOICES)
    description = forms.CharField(max_length=255, required=False)

    class Meta:
        model = Restaurant
        fields = ['name', 'contact_phone', 'location', 'cuisine_type', 'description', 'profile_picture']


class NGOProfileForm(ProfileFormMixin, forms.ModelForm):
    capacity = forms.ChoiceField(choices=CAPACITY_CHOICES)
    description = forms.CharField(max_length=255, required=False)

    class Meta:
        model = NGO
        fields = ['name', 'contact_phone', 'location', 'capacity', 'description', 'profile_picture']


class SMSForm(forms.Form):  # still imported by admin.py, cleaned up in a later step
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}), label='Message')