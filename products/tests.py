from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .models import Car, CarCategory, RentalOrder


class CarTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = CarCategory.objects.create(name='Эконом', slug='ekonom')
        cls.car = Car.objects.create(
            name='Kia Rio',
            slug='kia-rio-2022',
            brand='Kia',
            model='Rio',
            year=2022,
            category=cls.category,
            price_per_day=2000,
            deposit=15000,
        )

    def test_index_page(self):
        response = self.client.get(reverse('products:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kia Rio')

    def test_car_list(self):
        response = self.client.get(reverse('products:cars'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kia Rio')

    def test_car_list_search(self):
        response = self.client.get(reverse('products:cars'), {'q': 'kia'})
        self.assertContains(response, 'Kia Rio')

        response = self.client.get(reverse('products:cars'), {'q': 'bmw'})
        self.assertNotContains(response, 'Kia Rio')

    def test_car_list_by_category(self):
        response = self.client.get(self.category.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kia Rio')

    def test_car_detail(self):
        response = self.client.get(self.car.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2000')

    def test_about_page(self):
        self.assertEqual(self.client.get(reverse('products:about')).status_code, 200)


class RentalOrderTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ivan', password='pass12345')
        self.car = Car.objects.create(
            name='Toyota Camry',
            slug='toyota-camry',
            brand='Toyota',
            model='Camry',
            year=2022,
            category=CarCategory.objects.create(name='Комфорт', slug='komfort'),
            price_per_day=3000,
        )
        self.today = timezone.localdate()

    def test_order_requires_login(self):
        response = self.client.post(reverse('products:create_order', args=[self.car.slug]), {
            'start_date': self.today + timedelta(days=1),
            'end_date': self.today + timedelta(days=3),
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_create_order_calculates_price(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.post(reverse('products:create_order', args=[self.car.slug]), {
            'start_date': str(self.today + timedelta(days=1)),
            'end_date': str(self.today + timedelta(days=4)),
        })

        order = RentalOrder.objects.get()
        self.assertRedirects(response, reverse('products:pay_order', args=[order.pk]))
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.days, 3)
        self.assertEqual(order.total_price, 9000)
        self.assertEqual(order.status, RentalOrder.Status.NEW)
        self.assertFalse(order.is_paid)

    def test_end_date_before_start_date(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.post(reverse('products:create_order', args=[self.car.slug]), {
            'start_date': str(self.today + timedelta(days=5)),
            'end_date': str(self.today + timedelta(days=2)),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RentalOrder.objects.count(), 0)

    def test_dates_in_past_rejected(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.post(reverse('products:create_order', args=[self.car.slug]), {
            'start_date': str(self.today - timedelta(days=2)),
            'end_date': str(self.today + timedelta(days=2)),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RentalOrder.objects.count(), 0)

    def test_busy_dates_rejected(self):
        RentalOrder.objects.create(
            user=self.user,
            car=self.car,
            start_date=self.today + timedelta(days=1),
            end_date=self.today + timedelta(days=4),
        )
        self.client.login(username='ivan', password='pass12345')
        response = self.client.post(reverse('products:create_order', args=[self.car.slug]), {
            'start_date': str(self.today + timedelta(days=2)),
            'end_date': str(self.today + timedelta(days=3)),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RentalOrder.objects.count(), 1)

    def test_cancel_own_order(self):
        order = RentalOrder.objects.create(
            user=self.user,
            car=self.car,
            start_date=self.today + timedelta(days=1),
            end_date=self.today + timedelta(days=2),
        )
        self.client.login(username='ivan', password='pass12345')
        self.client.post(reverse('products:cancel_order', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, RentalOrder.Status.CANCELLED)

    def test_cannot_cancel_foreign_order(self):
        order = RentalOrder.objects.create(
            user=self.user,
            car=self.car,
            start_date=self.today + timedelta(days=1),
            end_date=self.today + timedelta(days=2),
        )
        other = get_user_model().objects.create_user(username='petr', password='pass12345')
        self.client.login(username='petr', password='pass12345')
        self.assertEqual(self.client.post(reverse('products:cancel_order', args=[order.pk])).status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, RentalOrder.Status.NEW)
        self.assertNotEqual(order.user, other)

    def test_my_orders_requires_login(self):
        response = self.client.get(reverse('products:my_orders'))
        self.assertEqual(response.status_code, 302)


class PaymentTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ivan', password='pass12345')
        self.car = Car.objects.create(
            name='Toyota Camry',
            slug='toyota-camry',
            brand='Toyota',
            model='Camry',
            year=2022,
            category=CarCategory.objects.create(name='Комфорт', slug='komfort'),
            price_per_day=3000,
        )
        self.today = timezone.localdate()
        self.order = RentalOrder.objects.create(
            user=self.user,
            car=self.car,
            start_date=self.today + timedelta(days=1),
            end_date=self.today + timedelta(days=3),
        )
        next_month = (self.today.replace(day=1) + timedelta(days=32)).replace(day=1)
        self.expiry = f'{next_month.month:02d}/{str(next_month.year)[2:]}'
        self.valid_data = {
            'card_number': '4111 1111 1111 1111',
            'expiry': self.expiry,
            'cvv': '123',
            'cardholder': 'IVAN IVANOV',
        }

    def _url(self):
        return reverse('products:pay_order', args=[self.order.pk])

    def test_pay_requires_login(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_pay_page_renders(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Оплата заказа')
        self.assertContains(response, '6000')

    def test_invalid_card_rejected(self):
        self.client.login(username='ivan', password='pass12345')
        data = dict(self.valid_data, card_number='1234')
        response = self.client.post(self._url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '16 цифр')
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)

    def test_expired_card_rejected(self):
        self.client.login(username='ivan', password='pass12345')
        data = dict(self.valid_data, expiry='01/20')
        response = self.client.post(self._url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'истёк')
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)

    def test_successful_payment(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.post(self._url(), self.valid_data)
        self.assertRedirects(response, reverse('products:my_orders'))
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)

    def test_already_paid_redirects(self):
        self.order.is_paid = True
        self.order.save(update_fields=['is_paid'])
        self.client.login(username='ivan', password='pass12345')
        response = self.client.get(self._url())
        self.assertRedirects(response, reverse('products:my_orders'))

    def test_cannot_pay_foreign_order(self):
        other = get_user_model().objects.create_user(username='petr', password='pass12345')
        self.client.login(username='petr', password='pass12345')
        self.assertEqual(self.client.get(self._url()).status_code, 404)

    def test_my_orders_shows_pay_button(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.get(reverse('products:my_orders'))
        self.assertContains(response, 'Оплатить')
        self.order.is_paid = True
        self.order.save(update_fields=['is_paid'])
        response = self.client.get(reverse('products:my_orders'))
        self.assertContains(response, 'Оплачен')
        self.assertNotContains(response, 'Оплатить')


class SeedCommandTestCase(TestCase):
    def test_seed_creates_data(self):
        from django.core.management import call_command

        call_command('seed_data', verbosity=0)
        self.assertTrue(CarCategory.objects.exists())
        self.assertTrue(Car.objects.exists())
        self.assertEqual(Car.objects.first().slug, slugify(Car.objects.first().slug))
