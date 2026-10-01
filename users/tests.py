from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Profile


class RegistrationTestCase(TestCase):
    def test_profile_created_with_user(self):
        user = get_user_model().objects.create_user(username='anna', password='pass12345')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_registration_page(self):
        response = self.client.get(reverse('users:register'))
        self.assertEqual(response.status_code, 200)

    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'Новый',
            'last_name': 'Пользователь',
            'birth_date': f'{timezone.localdate().year - 25}-06-15',
            'password1': 'strongpass123',
            'password2': 'strongpass123',
        })
        self.assertRedirects(response, reverse('users:profile'))
        user = get_user_model().objects.get(username='newuser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertIsNotNone(user.profile.birth_date)

    def test_registration_underage_rejected(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'younguser',
            'email': 'young@example.com',
            'first_name': 'Молодой',
            'birth_date': f'{timezone.localdate().year - 18}-01-01',
            'password1': 'strongpass123',
            'password2': 'strongpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'с 19 лет')
        self.assertFalse(get_user_model().objects.filter(username='younguser').exists())

    def test_registration_future_birthdate_rejected(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'futureuser',
            'email': 'future@example.com',
            'first_name': 'ИзБудущего',
            'birth_date': f'{timezone.localdate().year + 1}-01-01',
            'password1': 'strongpass123',
            'password2': 'strongpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'будущем')
        self.assertFalse(get_user_model().objects.filter(username='futureuser').exists())

    def test_registration_birthdate_required(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'nodateuser',
            'email': 'nodate@example.com',
            'first_name': 'БезДаты',
            'password1': 'strongpass123',
            'password2': 'strongpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='nodateuser').exists())

    def test_registration_password_mismatch(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'baduser',
            'password1': 'strongpass123',
            'password2': 'otherpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='baduser').exists())


class LoginTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ivan', password='pass12345')

    def test_login_page(self):
        self.assertEqual(self.client.get(reverse('users:login')).status_code, 200)

    def test_login_and_logout(self):
        self.assertTrue(self.client.login(username='ivan', password='pass12345'))
        self.assertEqual(self.client.get(reverse('users:profile')).status_code, 200)

        self.client.post(reverse('users:logout'))
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_profile_update(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.post(reverse('users:profile'), {
            'phone': '+7 900 111-22-33',
            'driver_license': '99 12 345678',
            'about': 'Аккуратно вожу',
        })
        self.assertRedirects(response, reverse('users:profile'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '+79001112233')

    def test_profile_stats(self):
        self.assertEqual(self.user.profile.orders_count, 0)
        self.assertEqual(self.user.profile.rented_days, 0)
        self.assertEqual(self.user.profile.spent_money, 0)


class PhoneLoginTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ivan', password='pass12345')
        self.user.profile.phone = '+79000000001'
        self.user.profile.save(update_fields=['phone'])

    def _login(self, username, password='pass12345'):
        return self.client.post(reverse('users:login'), {'username': username, 'password': password})

    def test_login_by_phone(self):
        response = self._login('+79000000001')
        self.assertRedirects(response, reverse('users:profile'))

    def test_login_by_phone_any_format(self):
        from django.test import Client

        for variant in ['89000000001', '8 (900) 000-00-01', '+7 900 000-00-01']:
            with self.subTest(variant=variant):
                client = Client()
                response = client.post(reverse('users:login'), {
                    'username': variant, 'password': 'pass12345',
                })
                self.assertEqual(response.status_code, 302, f'не удалось войти как {variant}')
                self.assertEqual(client.session.get('_auth_user_id'), str(self.user.pk))

    def test_login_by_username_still_works(self):
        response = self._login('ivan')
        self.assertRedirects(response, reverse('users:profile'))

    def test_wrong_password_by_phone(self):
        response = self._login('+79000000001', 'wrongpass')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Неверное имя пользователя или пароль')
        self.assertNotEqual(self.client.session.get('_auth_user_id'), str(self.user.pk))

    def test_unknown_phone_rejected(self):
        response = self._login('+70000000000')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Пользователь не зарегистрирован')
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_unknown_username_rejected(self):
        response = self._login('no_such_user')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Пользователь не зарегистрирован')
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_known_username_wrong_password(self):
        response = self._login('ivan', 'wrongpass')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Неверное имя пользователя или пароль')
        self.assertNotContains(response, 'не зарегистрирован')
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_phone_saved_normalized(self):
        self.client.login(username='ivan', password='pass12345')
        self.client.post(reverse('users:profile'), {'phone': '8 (900) 111-22-33'})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '+79001112233')

    def test_duplicate_phone_rejected(self):
        other = get_user_model().objects.create_user(username='petr', password='pass12345')
        self.client.login(username='petr', password='pass12345')
        response = self.client.post(reverse('users:profile'), {'phone': '+7 900 000-00-01'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'уже используется')
        other.profile.refresh_from_db()
        self.assertEqual(other.profile.phone, '')

    def test_invalid_phone_rejected(self):
        self.client.login(username='ivan', password='pass12345')
        response = self.client.post(reverse('users:profile'), {'phone': '123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'корректный номер')
