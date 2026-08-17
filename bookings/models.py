import uuid
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Profile(models.Model):
    """Extends Django's built-in User with the extra fields TrackGuard needs."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.get_username()}"


class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('car', 'Car'),
        ('suv', 'SUV'),
        ('truck', 'Truck'),
        ('van', 'Van'),
        ('motorcycle', 'Motorcycle'),
        ('bus', 'Bus'),
        ('other', 'Other'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicles'
    )
    registration_number = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='car')
    color = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.make} {self.model} ({self.registration_number})"

    def clean(self):
        current_year = date.today().year
        if self.year and (self.year < 1950 or self.year > current_year + 1):
            raise ValidationError({'year': f'Enter a valid vehicle year between 1950 and {current_year + 1}.'})


class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_duration_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TimeSlot(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_bookings = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ('date', 'start_time', 'end_time')

    def __str__(self):
        return f"{self.date} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time.')

    @property
    def active_booking_count(self):
        return self.bookings.exclude(status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED]).count()

    @property
    def is_full(self):
        return self.active_booking_count >= self.max_bookings

    @property
    def is_bookable(self):
        return self.is_available and not self.is_full and self.date >= date.today()


class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings'
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='bookings')
    slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT, related_name='bookings')
    booking_reference = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # A customer cannot hold two simultaneously "active" bookings on the same slot.
            models.UniqueConstraint(
                fields=['customer', 'slot'],
                condition=models.Q(status__in=['pending', 'confirmed', 'completed']),
                name='unique_active_booking_per_customer_slot',
            )
        ]

    def __str__(self):
        return f"{self.booking_reference} - {self.customer.get_username()} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self._generate_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference():
        """Generate a unique, human-friendly booking reference like TG-8F3A1C2B."""
        while True:
            candidate = f"TG-{uuid.uuid4().hex[:8].upper()}"
            if not Booking.objects.filter(booking_reference=candidate).exists():
                return candidate

    @property
    def is_active(self):
        return self.status not in (self.STATUS_CANCELLED, self.STATUS_REJECTED)
