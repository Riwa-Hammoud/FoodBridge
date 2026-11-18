from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.shortcuts import render
from .forms import SMSForm
import requests 
from django.core.mail import send_mail

from django.contrib import admin
from django.shortcuts import redirect
import requests

from django.contrib import admin
from django.shortcuts import redirect, reverse
import requests

class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'contact_email', 'contact_phone', 'cuisine_type', 'description')
    actions = ['send_sms_to_restaurants']
    readonly_fields = ()

    def send_sms_to_restaurants(self, request, queryset):
        username = "naderbakir@gmail.com"
        password = "qfzjui"
        advert_message = "REMINDER to make a difference today and change lives with FoodBridge!"

        for restaurant in queryset:
            number = restaurant.contact_phone

            url = f"http://unosms.us/api.php?user={username}&pass={password}&to={number}&from=fsegorg&msg={advert_message}"

            response = requests.get(url)

            if response.status_code == 200:
                self.message_user(request, f"SMS sent to {number} successfully!")
            else:
                self.message_user(request, f"Failed to send SMS to {number}. Error: {response.text}")

        change_list_url = reverse('admin:app1_restaurant_changelist')  # Replace 'app1' with your app name
        return redirect(change_list_url)  # Redirect to the restaurant change list page

    send_sms_to_restaurants.short_description = "Send Reminder SMS"






class NGOAdmin(admin.ModelAdmin):
    list_display = ('name','location','contact_email','contact_phone','capacity','description')
    actions = ['send_sms_to_restaurants']
    readonly_fields = ()

    def send_sms_to_restaurants(self, request, queryset):
        username = "naderbakir@gmail.com"
        password = "qfzjui"
        advert_message = "REMINDER to make a difference today and change lives with FoodBridge!"

        for restaurant in queryset:
            number = restaurant.contact_phone

            url = f"http://unosms.us/api.php?user={username}&pass={password}&to={number}&from=fsegorg&msg={advert_message}"

            response = requests.get(url)

            if response.status_code == 200:
                self.message_user(request, f"SMS sent to {number} successfully!")
            else:
                self.message_user(request, f"Failed to send SMS to {number}. Error: {response.text}")

        change_list_url = reverse('admin:app1_restaurant_changelist')  # Replace 'app1' with your app name
        return redirect(change_list_url)  # Redirect to the restaurant change list page

    send_sms_to_restaurants.short_description = "Send Reminder SMS"


class DonationAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'ngo', 'delivery_time', 'created_on', 'confirmed', 'expiration_date', 'requested', 'quantity')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'ngo'):
            return qs.filter(ngo=request.user.ngo)
        if hasattr(request.user, 'restaurant'):
            return qs.filter(restaurant=request.user.restaurant)
        return qs.none()

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
        if hasattr(request.user, 'ngo'):
            return ('confirmed', 'restaurant', 'ngo')
        if hasattr(request.user, 'restaurant'):
            return ('restaurant', 'donation_date', 'delivery_time', 'requested')
        return ()

    def has_add_permission(self, request):
        if hasattr(request.user, 'ngo') and not request.user.is_superuser:
            return False
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        if not change and hasattr(request.user, 'restaurant'):
            obj.restaurant = request.user.restaurant
        super().save_model(request, obj, form, change)


admin.site.register(Donation, DonationAdmin)
admin.site.register(NGO, NGOAdmin)
admin.site.register(Restaurant,RestaurantAdmin)