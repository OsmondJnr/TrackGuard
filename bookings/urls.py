from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.service_list, name='service_list'),

    # Auth
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.TrackGuardLoginView.as_view(), name='login'),
    path('logout/', views.TrackGuardLogoutView.as_view(), name='logout'),

    # Customer
    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:pk>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('bookings/<int:pk>/confirmation/', views.booking_confirmation, name='booking_confirmation'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/vehicles/add/', views.add_vehicle, name='add_vehicle'),

    # Booking flow
    path('book/', views.book_step1_service, name='book_step1_service'),
    path('book/<int:service_id>/date/', views.book_step2_date, name='book_step2_date'),
    path('book/<int:service_id>/date/<str:slot_date>/slots/', views.book_step3_slot, name='book_step3_slot'),
    path('book/<int:service_id>/slot/<int:slot_id>/confirm/', views.book_step4_confirm, name='book_step4_confirm'),

    # Staff
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/bookings/', views.manage_bookings, name='manage_bookings'),
    path('staff/bookings/<int:pk>/status/', views.update_booking_status, name='update_booking_status'),
    path('staff/slots/', views.manage_slots, name='manage_slots'),
    path('staff/slots/<int:pk>/edit/', views.edit_slot, name='edit_slot'),
    path('staff/slots/<int:pk>/delete/', views.delete_slot, name='delete_slot'),
    path('staff/slots/<int:pk>/toggle/', views.toggle_slot_availability, name='toggle_slot_availability'),
    path('staff/services/', views.manage_services, name='manage_services'),
    path('staff/services/<int:pk>/edit/', views.edit_service, name='edit_service'),
    path('staff/services/<int:pk>/delete/', views.delete_service, name='delete_service'),
    path('staff/customers/', views.manage_customers, name='manage_customers'),
    path('staff/customers/<int:pk>/', views.customer_detail, name='customer_detail'),
]
