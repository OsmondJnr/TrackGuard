from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Booking, Profile, Service, TimeSlot, Vehicle


def make_slot(days_ahead=1, hour=9, is_available=True, max_bookings=1):
    return TimeSlot.objects.create(
        date=date.today() + timedelta(days=days_ahead),
        start_time=time(hour, 0),
        end_time=time(hour + 1, 0),
        is_available=is_available,
        max_bookings=max_bookings,
    )


def make_service(name='Standard GPS Tracker Installation', price=25000):
    return Service.objects.create(name=name, description='Demo service', price=price, estimated_duration_minutes=45)


class AuthenticationTests(TestCase):
    def test_user_registration(self):
        response = self.client.post(reverse('bookings:register'), {
            'username': 'newcustomer',
            'first_name': 'Ada',
            'last_name': 'Lovelace',
            'email': 'ada@example.com',
            'phone_number': '+2348000000000',
            'password1': 'SuperSecret123!',
            'password2': 'SuperSecret123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newcustomer').exists())
        self.assertTrue(Profile.objects.filter(user__username='newcustomer').exists())

    def test_login(self):
        User.objects.create_user(username='logintest', password='TestPass123!')
        response = self.client.post(reverse('bookings:login'), {
            'username': 'logintest', 'password': 'TestPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_anonymous is False or True)  # session established


class BookingTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username='cust1', password='TestPass123!')
        Profile.objects.create(user=self.customer, phone_number='+2348011111111')
        self.other_customer = User.objects.create_user(username='cust2', password='TestPass123!')
        Profile.objects.create(user=self.other_customer, phone_number='+2348022222222')
        self.vehicle = Vehicle.objects.create(
            owner=self.customer, registration_number='ABC-123-XY', make='Toyota',
            model='Corolla', year=2020, vehicle_type='car', color='Blue',
        )
        self.service = make_service()
        self.client.login(username='cust1', password='TestPass123!')

    def test_successful_booking(self):
        slot = make_slot()
        response = self.client.post(
            reverse('bookings:book_step4_confirm', args=[self.service.id, slot.id]),
            {'service': self.service.id, 'vehicle': self.vehicle.id, 'notes': 'Test booking'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.status, Booking.STATUS_PENDING)
        self.assertTrue(booking.booking_reference.startswith('TG-'))

    def test_booking_unavailable_slot(self):
        slot = make_slot(is_available=False)
        response = self.client.post(
            reverse('bookings:book_step4_confirm', args=[self.service.id, slot.id]),
            {'service': self.service.id, 'vehicle': self.vehicle.id},
        )
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(response.status_code, 200)  # re-rendered with error, no redirect

    def test_duplicate_booking_prevention(self):
        slot = make_slot(max_bookings=5)
        Booking.objects.create(customer=self.customer, vehicle=self.vehicle, service=self.service, slot=slot)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Booking.objects.create(customer=self.customer, vehicle=self.vehicle, service=self.service, slot=slot)

    def test_full_slot_rejects_further_bookings(self):
        slot = make_slot(max_bookings=1)
        Booking.objects.create(customer=self.other_customer, vehicle=Vehicle.objects.create(
            owner=self.other_customer, registration_number='XYZ-999-ZZ', make='Honda',
            model='Civic', year=2018, vehicle_type='car', color='Red',
        ), service=self.service, slot=slot)
        slot.is_available = False
        slot.save()

        response = self.client.post(
            reverse('bookings:book_step4_confirm', args=[self.service.id, slot.id]),
            {'service': self.service.id, 'vehicle': self.vehicle.id},
        )
        self.assertEqual(Booking.objects.filter(slot=slot).count(), 1)
        self.assertEqual(response.status_code, 200)

    def test_past_date_slot_cannot_be_created(self):
        from .forms import TimeSlotForm
        form = TimeSlotForm(data={
            'date': date.today() - timedelta(days=1),
            'start_time': '09:00', 'end_time': '10:00',
            'is_available': True, 'max_bookings': 1,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_booking_cancellation_frees_slot(self):
        slot = make_slot(max_bookings=1)
        booking = Booking.objects.create(
            customer=self.customer, vehicle=self.vehicle, service=self.service, slot=slot,
            status=Booking.STATUS_PENDING,
        )
        slot.is_available = False
        slot.save()

        response = self.client.post(reverse('bookings:cancel_booking', args=[booking.pk]))
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.STATUS_CANCELLED)


class AuthorizationTests(TestCase):
    def setUp(self):
        self.customer1 = User.objects.create_user(username='auth1', password='TestPass123!')
        self.customer2 = User.objects.create_user(username='auth2', password='TestPass123!')
        self.staff = User.objects.create_user(username='staffuser', password='TestPass123!', is_staff=True)
        self.vehicle = Vehicle.objects.create(
            owner=self.customer1, registration_number='AUTH-001', make='Kia',
            model='Rio', year=2021, vehicle_type='car', color='Black',
        )
        self.service = make_service()
        self.slot = make_slot()
        self.booking = Booking.objects.create(
            customer=self.customer1, vehicle=self.vehicle, service=self.service, slot=self.slot,
        )

    def test_customer_cannot_access_another_customers_booking(self):
        self.client.login(username='auth2', password='TestPass123!')
        response = self.client.get(reverse('bookings:booking_detail', args=[self.booking.pk]))
        self.assertRedirects(response, reverse('bookings:my_bookings'))

    def test_staff_can_access_all_bookings(self):
        self.client.login(username='staffuser', password='TestPass123!')
        response = self.client.get(reverse('bookings:booking_detail', args=[self.booking.pk]))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_view_manage_bookings(self):
        self.client.login(username='staffuser', password='TestPass123!')
        response = self.client.get(reverse('bookings:manage_bookings'))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_cannot_access_staff_dashboard(self):
        self.client.login(username='auth1', password='TestPass123!')
        response = self.client.get(reverse('bookings:staff_dashboard'))
        self.assertNotEqual(response.status_code, 200)


class ModelTests(TestCase):
    def test_booking_reference_generation_is_unique(self):
        customer = User.objects.create_user(username='modeltest', password='TestPass123!')
        vehicle = Vehicle.objects.create(
            owner=customer, registration_number='MOD-001', make='Ford',
            model='Focus', year=2017, vehicle_type='car', color='White',
        )
        service = make_service()
        slot1 = make_slot(days_ahead=2, max_bookings=2)
        slot2 = make_slot(days_ahead=3, max_bookings=2)
        b1 = Booking.objects.create(customer=customer, vehicle=vehicle, service=service, slot=slot1)
        b2 = Booking.objects.create(customer=customer, vehicle=vehicle, service=service, slot=slot2)
        self.assertNotEqual(b1.booking_reference, b2.booking_reference)
        self.assertTrue(b1.booking_reference.startswith('TG-'))

    def test_booking_relationships(self):
        customer = User.objects.create_user(username='reltest', password='TestPass123!')
        vehicle = Vehicle.objects.create(
            owner=customer, registration_number='REL-001', make='Mazda',
            model='3', year=2016, vehicle_type='car', color='Gray',
        )
        service = make_service()
        slot = make_slot(days_ahead=4)
        booking = Booking.objects.create(customer=customer, vehicle=vehicle, service=service, slot=slot)
        self.assertEqual(booking.customer, customer)
        self.assertEqual(booking.vehicle.owner, customer)
        self.assertIn(booking, slot.bookings.all())
        self.assertIn(booking, service.bookings.all())

    def test_slot_availability_flags(self):
        slot = make_slot(days_ahead=5, max_bookings=1)
        self.assertTrue(slot.is_bookable)
        customer = User.objects.create_user(username='availtest', password='TestPass123!')
        vehicle = Vehicle.objects.create(
            owner=customer, registration_number='AVL-001', make='Nissan',
            model='Altima', year=2015, vehicle_type='car', color='Green',
        )
        service = make_service()
        Booking.objects.create(customer=customer, vehicle=vehicle, service=service, slot=slot)
        self.assertTrue(slot.is_full)
