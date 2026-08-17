import random
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from bookings.models import Booking, Profile, Service, TimeSlot, Vehicle


class Command(BaseCommand):
    help = 'Seeds the database with demo data for TrackGuard (admin, customer, services, slots, vehicle, bookings).'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding TrackGuard demo data...')

        # --- Demo staff/admin account -------------------------------------------------
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@trackguard.demo',
                'first_name': 'TrackGuard',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin_user.set_password('AdminPass123!')
            admin_user.save()
        Profile.objects.get_or_create(user=admin_user, defaults={'phone_number': '+2348010000001'})
        self.stdout.write(self.style.SUCCESS(f'  Admin account ready: {admin_user.username}'))

        # --- Demo customer account ------------------------------------------------------
        customer_user, created = User.objects.get_or_create(
            username='customer',
            defaults={
                'email': 'customer@trackguard.demo',
                'first_name': 'Chidi',
                'last_name': 'Okafor',
            },
        )
        if created:
            customer_user.set_password('CustomerPass123!')
            customer_user.save()
        Profile.objects.get_or_create(user=customer_user, defaults={'phone_number': '+2348020000002'})
        self.stdout.write(self.style.SUCCESS(f'  Customer account ready: {customer_user.username}'))

        # --- Services ---------------------------------------------------------------
        services_data = [
            {
                'name': 'Standard GPS Tracker Installation',
                'description': 'Basic GPS tracker installation with real-time location tracking for a single vehicle.',
                'price': 25000,
                'estimated_duration_minutes': 45,
            },
            {
                'name': 'Premium GPS Tracker Installation',
                'description': 'Advanced tracker with fuel monitoring, engine cut-off, and geofencing alerts.',
                'price': 55000,
                'estimated_duration_minutes': 90,
            },
            {
                'name': 'Fleet Tracker Installation',
                'description': 'Bulk tracker installation for commercial fleets, with centralized dashboard setup.',
                'price': 45000,
                'estimated_duration_minutes': 60,
            },
        ]
        services = []
        for data in services_data:
            service, _ = Service.objects.get_or_create(name=data['name'], defaults=data)
            services.append(service)
        self.stdout.write(self.style.SUCCESS(f'  {len(services)} services ready'))

        # --- Time slots ---------------------------------------------------------------
        start_hours = [(9, 0), (11, 0), (13, 0), (15, 0)]
        slots_created = 0
        today = date.today()
        for day_offset in range(1, 15):
            slot_date = today + timedelta(days=day_offset)
            if slot_date.weekday() == 6:  # skip Sundays
                continue
            for hour, minute in start_hours:
                start = time(hour, minute)
                end = time(hour + 1, minute)
                _, created = TimeSlot.objects.get_or_create(
                    date=slot_date, start_time=start, end_time=end,
                    defaults={'is_available': True, 'max_bookings': 1},
                )
                if created:
                    slots_created += 1
        self.stdout.write(self.style.SUCCESS(f'  {slots_created} new time slots created'))

        # --- Example vehicle ---------------------------------------------------------
        vehicle, _ = Vehicle.objects.get_or_create(
            owner=customer_user,
            registration_number='RIV-234-XY',
            defaults={
                'make': 'Toyota',
                'model': 'Camry',
                'year': 2019,
                'vehicle_type': 'car',
                'color': 'Silver',
            },
        )
        self.stdout.write(self.style.SUCCESS(f'  Example vehicle ready: {vehicle}'))

        # --- Example bookings ---------------------------------------------------------
        available_slot = TimeSlot.objects.filter(
            date__gte=today, is_available=True
        ).exclude(bookings__customer=customer_user).order_by('date', 'start_time').first()

        if available_slot and not Booking.objects.filter(customer=customer_user, slot=available_slot).exists():
            booking = Booking.objects.create(
                customer=customer_user,
                vehicle=vehicle,
                service=services[0],
                slot=available_slot,
                status=Booking.STATUS_CONFIRMED,
                notes='Please call on arrival.',
            )
            self.stdout.write(self.style.SUCCESS(f'  Example booking created: {booking.booking_reference}'))

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
        self.stdout.write('')
        self.stdout.write('Demo credentials:')
        self.stdout.write('  Admin:    username=admin    password=AdminPass123!')
        self.stdout.write('  Customer: username=customer password=CustomerPass123!')
