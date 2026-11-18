import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.dateparse import parse_time
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    NGOProfileForm,
    PasswordResetConfirmationForm,
    PasswordResetRequestForm,
    RegistrationForm,
    RestaurantProfileForm,
)
from .models import NGO, Donation, Restaurant
from .permissions import (
    ROLE_NGO,
    ROLE_RESTAURANT,
    get_profile,
    get_role,
    ngo_required,
    restaurant_required,
)

logger = logging.getLogger(__name__)

PROFILE_FORMS = {
    ROLE_RESTAURANT: (RestaurantProfileForm, 'profile.restaurant.html'),
    ROLE_NGO: (NGOProfileForm, 'profile.ngo.html'),
}


# helpers

def page_context(request, **extra):
    """Context the nav and footer templates expect ('user' is the role letter)."""
    role = get_role(request.user)
    return {'user': role, 'status': role is not None, **extra}


def send_email(subject, body, to, html=False):
    """Send an email without crashing the request if SMTP is unavailable."""
    message = EmailMessage(subject, body, from_email=settings.DEFAULT_FROM_EMAIL, to=[to])
    if html:
        message.content_subtype = 'html'
    try:
        message.send()
    except (SMTPException, OSError):
        logger.exception('Could not send email to %s', to)
        return False
    return True


def flash_form_errors(request, form):
    for field, errors in form.errors.items():
        prefix = '' if field == '__all__' else f'{field.replace("_", " ").title()}: '
        for error in errors:
            messages.error(request, prefix + error)


def home_context(request):
    profile = get_profile(request.user)
    return page_context(
        request,
        user_name=profile.name if profile else '',
        restaurants=Restaurant.objects.filter(is_verified=True),
    )


# public pages

def home(request):
    return render(request, 'index.html', home_context(request))


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        try:
            send_mail(
                subject='Contact Us: ' + subject,
                message='Name: ' + name + '\nEmail: ' + email + '\n\nMessage: ' + message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Contact form email failed')
    return render(request, 'contact.html', page_context(request))


def loginRegister(request):
    return render(request, 'login-register.html')


# authentication

def send_verification_email(request, user):
    body = render_to_string('verify_email.html', {
        'user': user,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    return send_email('Activate Your Account', body, user.email, html=True)


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.method == 'GET':
        return render(request, 'login-register.html')

    form = RegistrationForm(request.POST)
    if not form.is_valid():
        flash_form_errors(request, form)
        return render(request, 'login-register.html', {'signup': True})

    data = form.cleaned_data
    with transaction.atomic():
        user = User.objects.create_user(
            username=data['name'], email=data['email'],
            password=data['password'], is_active=False,
        )
        profile_model = Restaurant if data['choice'] == 'Restaurant' else NGO
        profile_model.objects.create(
            user=user, name=data['name'], contact_email=data['email'],
            contact_phone=data['phone'], location=data['location'],
        )
        sent = send_verification_email(request, user)
        if not sent:
            transaction.set_rollback(True)  # no email, no half-created account

    if not sent:
        messages.error(request, 'We could not send the verification email. Please try again later.')
        return render(request, 'login-register.html', {'signup': True})
    messages.success(request, 'Account created. Check your email to verify it before logging in.')
    return render(request, 'login-register.html')


def verify_email(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'Invalid or expired verification link.')
        return render(request, 'login-register.html')

    profile = get_profile(user)
    if profile is None:
        messages.error(request, 'No restaurant or charity is linked to this account.')
        return render(request, 'login-register.html')

    if not profile.is_verified:  # a used link can never re-activate a disabled account
        with transaction.atomic():
            user.is_active = True
            user.save(update_fields=['is_active'])
            profile.is_verified = True
            profile.save(update_fields=['is_verified'])
    messages.success(request, 'Your email is verified. You can log in now.')
    return redirect('login')


@require_http_methods(['GET', 'POST'])
def login(request):
    if request.method == 'GET':
        return render(request, 'login-register.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = auth.authenticate(request, username=username, password=password)

    if user is None:
        inactive = User.objects.filter(username=username, is_active=False).first()
        if inactive and inactive.check_password(password):
            messages.error(request, 'Please verify your email before logging in.')
        else:
            messages.error(request, 'Invalid username or password.')
        return render(request, 'login-register.html')

    profile = get_profile(user)
    if profile is None:
        messages.error(request, 'This account is not linked to a restaurant or charity.')
        return render(request, 'login-register.html')
    if not profile.is_verified:
        messages.error(request, 'Your account is not verified yet.')
        return render(request, 'login-register.html')

    auth.login(request, user)
    return redirect('dashboard', user=get_role(user))


def logout_view(request):
    auth.logout(request)
    return redirect('home')


@login_required
def dashboard(request, user):
    role = get_role(request.user)
    if role is None:
        return redirect('home')
    if user != role:
        return redirect('dashboard', user=role)
    return render(request, 'index.html', home_context(request))


# password reset

class PasswordResetRequestView(PasswordResetView):
    form_class = PasswordResetRequestForm
    template_name = 'password_reset_request.html'
    html_email_template_name = 'password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except (SMTPException, OSError):
            logger.exception('Password reset email failed')
            messages.error(self.request, 'We could not send the email right now. Please try again later.')
            return self.form_invalid(form)


class PasswordResetConfirmationView(PasswordResetConfirmView):
    form_class = PasswordResetConfirmationForm
    template_name = 'password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'password_reset_complete.html'


# restaurant side

def available_ngos(restaurant):
    ngos = NGO.objects.filter(is_verified=True)
    if restaurant.name == "Aquaria":
        ngos = ngos.filter(location__in=['Mina', 'Al-Tal'])
    if restaurant.name == "hallab":
        ngos = ngos.filter(location__in=['Tripoli Zeitoun', 'Al-Mina'])
    if restaurant.name == "Baytuna":
        ngos = ngos.filter(location__in=['Tripoli Zeitoun', 'Al-Mina', 'Al-Tabbaneh'])
    return ngos


def quantity_category(value):
    if value < 50:
        return "less than 50"
    if value < 100:
        return "50-100"
    if value < 200:
        return "100-200"
    if value < 500:
        return "200-500"
    return "more than 500"


@restaurant_required
def add_donation(request):
    restaurant = request.user.restaurant
    ngos = available_ngos(restaurant)

    if request.method == 'POST' and 'next_button' in request.POST:
        try:
            quantity_value = int(request.POST.get('food_quantity', ''))
        except ValueError:
            return redirect('donate')
        if quantity_value < 1:
            return redirect('donate')

        donation = Donation.objects.create(
            restaurant=restaurant,
            quantity=quantity_category(quantity_value),
            expiration_date=request.POST.get('expiration_date'),
            food_condition=request.POST.get('food_condition'),
            packaging=request.POST.get('packaging'),
            transportation=request.POST.get('transportation'),
        )
        request.session['donation_id'] = donation.id
        return render(request, 'second_form.html', page_context(request, ngos=ngos))

    donations = Donation.objects.filter(restaurant=restaurant)
    return render(request, 'donations.html', page_context(
        request,
        donations=donations,
        ngos=ngos,
        todo_donations=donations.filter(requested=False),
        inprogress_donations=donations.filter(requested=True, confirmed=False),
        done_donations=donations.filter(requested=True, confirmed=True),
    ))


@restaurant_required
@require_POST
def submit_donation(request):
    restaurant = request.user.restaurant
    donation_id = request.session.get('donation_id')
    ngo_id = request.POST.get('ngo', '')
    delivery_time = parse_time(request.POST.get('delivery_time', ''))

    if donation_id and ngo_id.isdigit() and delivery_time:
        ngo = available_ngos(restaurant).filter(pk=int(ngo_id)).first()
        donation = Donation.objects.filter(
            pk=donation_id, restaurant=restaurant, ngo__isnull=True
        ).first()
        if ngo and donation:
            donation.ngo = ngo
            donation.delivery_time = delivery_time
            donation.save()
            del request.session['donation_id']
    return redirect('donate')


@restaurant_required
@require_POST
def confirm_donation(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id, restaurant=request.user.restaurant)

    if donation.requested and not donation.confirmed:
        donation.confirmed = True
        donation.save()
        body = render_to_string('donation_confirmation.html', {
            'restaurant_location': donation.restaurant.location,
            'restaurant_number': donation.restaurant.contact_phone,
            'ngo_name': donation.ngo.name,
            'restaurant_name': donation.restaurant.name,
        })
        send_email('Donation Confirmation', body, donation.ngo.contact_email, html=True)
    return redirect('donate')


@restaurant_required
def charity_view(request):
    charities = NGO.objects.filter(is_verified=True)
    return render(request, 'charity.html', page_context(request, charities=charities))


# NGO side

@ngo_required
def view_donations(request):
    ngo = request.user.ngo
    donations = Donation.objects.filter(ngo=ngo)
    return render(request, 'browse_donations.html', page_context(request, donations=donations, ngo=ngo))


@ngo_required
@require_POST
def request_donation(request, donation_id):
    ngo = request.user.ngo
    donation = get_object_or_404(Donation, pk=donation_id, ngo=ngo)
    if donation.confirmed:
        return redirect('browse_donations')

    donation.requested = not donation.requested
    donation.save()

    restaurant = donation.restaurant
    if donation.requested:
        subject = 'New Donation Request'
        body = (f'Dear {restaurant.name}, please check your FoodBridge account. '
                f'You might have new requests available from {ngo.name}.')
    else:
        subject = 'Donation Request Undone'
        body = (f'Dear {restaurant.name}, the donation request from {ngo.name} '
                f'has been undone. Please check your FoodBridge account.')
    send_email(subject, body, restaurant.contact_email)
    return redirect('browse_donations')


@ngo_required
def restaurant_view(request):
    restaurants = Restaurant.objects.filter(is_verified=True)
    return render(request, 'restaurant.html', page_context(request, restaurants=restaurants))


@ngo_required
def restaurant_detail(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id, is_verified=True)
    return render(request, 'restaurant_detail.html', {'restaurant': restaurant})


# profile

@login_required
def update_profile(request):
    role = get_role(request.user)
    if role is None:
        return redirect('home')

    form_class, template = PROFILE_FORMS[role]
    instance = form_class._meta.model.objects.get(user=request.user)  # fresh copy

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            with transaction.atomic():
                profile = form.save()
                request.user.username = profile.name
                request.user.save(update_fields=['username'])
            return redirect('home')
    else:
        form = form_class(instance=instance)

    values = {name: form[name].value() for name in form.fields if name != 'profile_picture'}
    return render(request, template, {'form': form, **values})