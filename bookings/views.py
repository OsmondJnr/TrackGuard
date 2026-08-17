from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import (
    BookingForm,
    BookingStatusForm,
    ProfileUpdateForm,
    RegistrationForm,
    ServiceForm,
    TimeSlotForm,
    VehicleForm,
)
from .models import Booking, Profile, Service, TimeSlot, Vehicle


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

def home(request):
    services = Service.objects.filter(is_active=True)[:3]
    return render(request, 'bookings/home.html', {'services': services})


def about(request):
    return render(request, 'bookings/about.html')


def service_list(request):
    services = Service.objects.filter(is_active=True)
    return render(request, 'bookings/services.html', {'services': services})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterView(CreateView):
    form_class = RegistrationForm
    template_name = 'bookings/register.html'
    success_url = reverse_lazy('bookings:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        auth_login(self.request, self.object)
        messages.success(self.request, 'Welcome to TrackGuard! Your account has been created.')
        return response


class TrackGuardLoginView(LoginView):
    template_name = 'bookings/login.html'

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().first_name or form.get_user().username}!")
        return super().form_valid(form)


class TrackGuardLogoutView(LogoutView):
    next_page = reverse_lazy('bookings:home')


# ---------------------------------------------------------------------------
# Customer dashboard / bookings
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    bookings = Booking.objects.filter(customer=request.user)
    upcoming = (
        bookings.filter(status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED], slot__date__gte=date.today())
        .order_by('slot__date', 'slot__start_time')
        .first()
    )
    context = {
        'total_bookings': bookings.count(),
        'pending_count': bookings.filter(status=Booking.STATUS_PENDING).count(),
        'confirmed_count': bookings.filter(status=Booking.STATUS_CONFIRMED).count(),
        'completed_count': bookings.filter(status=Booking.STATUS_COMPLETED).count(),
        'upcoming': upcoming,
        'recent_bookings': bookings[:5],
    }
    return render(request, 'bookings/dashboard.html', context)


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(customer=request.user).select_related('service', 'slot', 'vehicle')
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.customer_id != request.user.id and not request.user.is_staff:
        messages.error(request, "You don't have permission to view that booking.")
        return redirect('bookings:my_bookings')
    return render(request, 'bookings/booking_detail.html', {'booking': booking})


@login_required
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.customer_id != request.user.id and not request.user.is_staff:
        messages.error(request, "You don't have permission to cancel that booking.")
        return redirect('bookings:my_bookings')

    if request.method == 'POST':
        if not booking.is_active:
            messages.warning(request, 'This booking is already cancelled or rejected.')
        else:
            booking.status = Booking.STATUS_CANCELLED
            booking.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Booking {booking.booking_reference} has been cancelled.')
        return redirect('bookings:my_bookings')

    return render(request, 'bookings/cancel_confirm.html', {'booking': booking})


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('bookings:profile')
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)
    vehicles = Vehicle.objects.filter(owner=request.user)
    return render(request, 'bookings/profile.html', {'form': form, 'vehicles': vehicles})


@login_required
def add_vehicle(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()
            messages.success(request, f'Vehicle {vehicle.registration_number} added.')
            return redirect('bookings:profile')
    else:
        form = VehicleForm()
    return render(request, 'bookings/vehicle_form.html', {'form': form})


# ---------------------------------------------------------------------------
# Booking flow (steps 1-4)
# ---------------------------------------------------------------------------

@login_required
def book_step1_service(request):
    services = Service.objects.filter(is_active=True)
    if not Vehicle.objects.filter(owner=request.user).exists():
        messages.info(request, 'Please add a vehicle to your profile before booking an installation.')
        return redirect('bookings:add_vehicle')
    return render(request, 'bookings/book_step1_service.html', {'services': services})


@login_required
def book_step2_date(request, service_id):
    service = get_object_or_404(Service, pk=service_id, is_active=True)
    today = date.today()
    upcoming_dates = [today + timedelta(days=i) for i in range(1, 15)]
    # Only surface dates that actually have at least one bookable slot.
    dates_with_slots = set(
        TimeSlot.objects.filter(date__gte=today, is_available=True)
        .values_list('date', flat=True)
    )
    context = {
        'service': service,
        'upcoming_dates': upcoming_dates,
        'dates_with_slots': dates_with_slots,
    }
    return render(request, 'bookings/book_step2_date.html', context)


@login_required
def book_step3_slot(request, service_id, slot_date):
    service = get_object_or_404(Service, pk=service_id, is_active=True)
    slots = TimeSlot.objects.filter(date=slot_date, is_available=True).order_by('start_time')
    bookable_slots = [s for s in slots if s.is_bookable]
    context = {'service': service, 'slot_date': slot_date, 'slots': bookable_slots}
    return render(request, 'bookings/book_step3_slot.html', context)


@login_required
def book_step4_confirm(request, service_id, slot_id):
    service = get_object_or_404(Service, pk=service_id, is_active=True)
    slot = get_object_or_404(TimeSlot, pk=slot_id)

    if request.method == 'POST':
        form = BookingForm(request.POST, customer=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    locked_slot = TimeSlot.objects.select_for_update().get(pk=slot.pk)

                    if locked_slot.date < date.today():
                        form.add_error(None, 'You cannot book a slot in the past.')
                        raise ValueError('past-date')

                    if not locked_slot.is_available:
                        form.add_error(None, 'This slot is no longer available.')
                        raise ValueError('unavailable')

                    if locked_slot.is_full:
                        form.add_error(None, 'This slot has already been fully booked.')
                        raise ValueError('full')

                    booking = form.save(commit=False)
                    booking.customer = request.user
                    booking.service = service
                    booking.slot = locked_slot
                    booking.status = Booking.STATUS_PENDING
                    booking.save()

                    # If the slot has now reached capacity, mark it unavailable for new bookings.
                    if locked_slot.is_full:
                        locked_slot.is_available = False
                        locked_slot.save(update_fields=['is_available'])

                messages.success(request, f'Booking confirmed! Your reference is {booking.booking_reference}.')
                return redirect('bookings:booking_confirmation', pk=booking.pk)
            except IntegrityError:
                form.add_error(None, 'You already have an active booking for this slot.')
            except ValueError:
                pass
    else:
        form = BookingForm(customer=request.user)

    context = {'service': service, 'slot': slot, 'form': form}
    return render(request, 'bookings/book_step4_confirm.html', context)


@login_required
def booking_confirmation(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.customer_id != request.user.id and not request.user.is_staff:
        return redirect('bookings:my_bookings')
    return render(request, 'bookings/booking_confirmation.html', {'booking': booking})


# ---------------------------------------------------------------------------
# Staff / admin dashboard
# ---------------------------------------------------------------------------

@user_passes_test(is_staff_user, login_url='bookings:login')
def staff_dashboard(request):
    bookings = Booking.objects.all()
    context = {
        'total_bookings': bookings.count(),
        'pending_count': bookings.filter(status=Booking.STATUS_PENDING).count(),
        'confirmed_count': bookings.filter(status=Booking.STATUS_CONFIRMED).count(),
        'completed_count': bookings.filter(status=Booking.STATUS_COMPLETED).count(),
        'cancelled_count': bookings.filter(status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED]).count(),
        'total_customers': Profile.objects.count(),
        'total_slots': TimeSlot.objects.count(),
        'recent_bookings': bookings.select_related('customer', 'service', 'slot')[:8],
    }
    return render(request, 'bookings/staff_dashboard.html', context)


@user_passes_test(is_staff_user, login_url='bookings:login')
def manage_bookings(request):
    bookings = Booking.objects.select_related('customer', 'service', 'slot', 'vehicle').all()
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    context = {'bookings': bookings, 'status_choices': Booking.STATUS_CHOICES, 'status_filter': status_filter}
    return render(request, 'bookings/manage_bookings.html', context)


@user_passes_test(is_staff_user, login_url='bookings:login')
def update_booking_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        form = BookingStatusForm(request.POST, instance=booking)
        if form.is_valid():
            old_status = booking.status
            updated = form.save()
            # Free the slot back up if the booking is cancelled/rejected.
            if updated.status in (Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED) and old_status not in (
                Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED
            ):
                slot = updated.slot
                slot.is_available = True
                slot.save(update_fields=['is_available'])
            messages.success(request, f'Booking {updated.booking_reference} updated to {updated.get_status_display()}.')
    return redirect('bookings:manage_bookings')


@user_passes_test(is_staff_user, login_url='bookings:login')
def manage_slots(request):
    slots = TimeSlot.objects.annotate(booking_count=Count('bookings')).order_by('date', 'start_time')
    if request.method == 'POST':
        form = TimeSlotForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Time slot created.')
            return redirect('bookings:manage_slots')
    else:
        form = TimeSlotForm()
    return render(request, 'bookings/manage_slots.html', {'slots': slots, 'form': form})


@user_passes_test(is_staff_user, login_url='bookings:login')
def edit_slot(request, pk):
    slot = get_object_or_404(TimeSlot, pk=pk)
    if request.method == 'POST':
        form = TimeSlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Time slot updated.')
            return redirect('bookings:manage_slots')
    else:
        form = TimeSlotForm(instance=slot)
    return render(request, 'bookings/edit_slot.html', {'form': form, 'slot': slot})


@user_passes_test(is_staff_user, login_url='bookings:login')
def delete_slot(request, pk):
    slot = get_object_or_404(TimeSlot, pk=pk)
    if request.method == 'POST':
        if slot.bookings.exists():
            messages.error(request, 'Cannot delete a slot that has bookings attached to it. Mark it unavailable instead.')
        else:
            slot.delete()
            messages.success(request, 'Time slot deleted.')
    return redirect('bookings:manage_slots')


@user_passes_test(is_staff_user, login_url='bookings:login')
def toggle_slot_availability(request, pk):
    slot = get_object_or_404(TimeSlot, pk=pk)
    if request.method == 'POST':
        slot.is_available = not slot.is_available
        slot.save(update_fields=['is_available'])
    return redirect('bookings:manage_slots')


@user_passes_test(is_staff_user, login_url='bookings:login')
def manage_services(request):
    services = Service.objects.all()
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service created.')
            return redirect('bookings:manage_services')
    else:
        form = ServiceForm()
    return render(request, 'bookings/manage_services.html', {'services': services, 'form': form})


@user_passes_test(is_staff_user, login_url='bookings:login')
def edit_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated.')
            return redirect('bookings:manage_services')
    else:
        form = ServiceForm(instance=service)
    return render(request, 'bookings/edit_service.html', {'form': form, 'service': service})


@user_passes_test(is_staff_user, login_url='bookings:login')
def delete_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        if service.bookings.exists():
            service.is_active = False
            service.save(update_fields=['is_active'])
            messages.warning(request, 'Service has existing bookings, so it was deactivated instead of deleted.')
        else:
            service.delete()
            messages.success(request, 'Service deleted.')
    return redirect('bookings:manage_services')


@user_passes_test(is_staff_user, login_url='bookings:login')
def manage_customers(request):
    customers = Profile.objects.select_related('user').annotate(booking_count=Count('user__bookings'))
    return render(request, 'bookings/manage_customers.html', {'customers': customers})


@user_passes_test(is_staff_user, login_url='bookings:login')
def customer_detail(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    bookings = Booking.objects.filter(customer=profile.user).select_related('service', 'slot')
    vehicles = Vehicle.objects.filter(owner=profile.user)
    return render(request, 'bookings/customer_detail.html', {'profile': profile, 'bookings': bookings, 'vehicles': vehicles})
