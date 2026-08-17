from django.contrib import admin

from .models import Booking, Profile, Service, TimeSlot, Vehicle


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone_number')
    list_filter = ('created_at',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'owner', 'make', 'model', 'year', 'vehicle_type', 'color')
    list_filter = ('vehicle_type', 'make', 'year')
    search_fields = ('registration_number', 'make', 'model', 'owner__username')
    ordering = ('-created_at',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'estimated_duration_minutes', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
    fieldsets = (
        (None, {'fields': ('name', 'description')}),
        ('Pricing & Duration', {'fields': ('price', 'estimated_duration_minutes')}),
        ('Status', {'fields': ('is_active',)}),
    )


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'is_available', 'max_bookings', 'active_booking_count')
    list_filter = ('is_available', 'date')
    search_fields = ('date',)
    ordering = ('date', 'start_time')

    @admin.display(description='Active bookings')
    def active_booking_count(self, obj):
        return obj.active_booking_count


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_reference', 'customer', 'service', 'slot', 'status', 'created_at',
    )
    list_filter = ('status', 'service', 'slot__date')
    search_fields = ('booking_reference', 'customer__username', 'customer__email', 'vehicle__registration_number')
    ordering = ('-created_at',)
    readonly_fields = ('booking_reference', 'created_at', 'updated_at')
    fieldsets = (
        ('Booking Info', {'fields': ('booking_reference', 'status', 'notes')}),
        ('Relations', {'fields': ('customer', 'vehicle', 'service', 'slot')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
