from django.contrib.auth.views import PasswordResetDoneView
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),

    path('login-register/', views.loginRegister, name='loginRegister'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('verify_email/<str:uidb64>/<str:token>/', views.verify_email, name='verify_email'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/<str:user>/', views.dashboard, name='dashboard'),
    path('update-profile/', views.update_profile, name='update_profile'),

    path('password_reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password_reset/done/',
         PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
         name='password_reset_done'),
    path('password_reset/confirm/<str:uidb64>/<str:token>/',
         views.PasswordResetConfirmationView.as_view(), name='password_reset_confirm'),
    path('password_reset/complete/',
         views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('donate/', views.add_donation, name='donate'),
    path('submit_donation/', views.submit_donation, name='submit_donation'),
    path('confirm_donation/<int:donation_id>/', views.confirm_donation, name='confirm_donation'),
    path('charity/', views.charity_view, name='charity'),

    path('browse_donations/', views.view_donations, name='browse_donations'),
    path('donation/request/<int:donation_id>/', views.request_donation, name='request_donation'),
    path('restaurant/', views.restaurant_view, name='restaurant'),
    path('restaurant/<int:restaurant_id>/', views.restaurant_detail, name='restaurant_detail'),
]