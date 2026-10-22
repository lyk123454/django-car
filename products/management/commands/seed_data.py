from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from products.models import Car, CarCategory, RentalOrder

CATEGORIES = [
    ('econom', 'Эконом', 'fa-car', 'Небольшой расход, удобно для города'),
    ('comfort', 'Комфорт', 'fa-car-side', 'Просторный салон для ежедневных поездок'),
    ('business', 'Бизнес', 'fa-taxi', 'Представительский класс для встреч и поездок'),
    ('premium', 'Премиум', 'fa-car-rear', 'Автомобили с максимальным уровнем комфорта'),
    ('suv', 'Внедорожник', 'fa-truck-monster', 'Для поездок за город и по плохим дорогам'),
    ('collector', 'Коллекционные', 'fa-crown', 'Редкие автомобили для ценителей и особых случаев'),
]

CARS = [
    ('Renault', 'Logan', 2021, 'Эконом', 1800, 4, 'manual', 'petrol', 15000),
    ('Kia', 'Rio', 2022, 'Эконом', 2100, 4, 'automatic', 'petrol', 18000),
    ('Hyundai', 'Solaris', 2023, 'Эконом', 2400, 4, 'automatic', 'petrol', 12000),
    ('Volkswagen', 'Polo', 2022, 'Эконом', 2300, 5, 'manual', 'petrol', 20000),
    ('Skoda', 'Rapid', 2021, 'Комфорт', 2700, 5, 'manual', 'petrol', 25000),
    ('Lada', 'Vesta', 2023, 'Комфорт', 2500, 5, 'manual', 'petrol', 10000),
    ('Toyota', 'Camry', 2022, 'Комфорт', 4500, 5, 'automatic', 'petrol', 30000),
    ('Mazda', '6', 2023, 'Комфорт', 4800, 5, 'automatic', 'petrol', 28000),
    ('Mercedes-Benz', 'E 200', 2022, 'Бизнес', 9500, 5, 'automatic', 'petrol', 60000),
    ('BMW', '5 Series', 2023, 'Бизнес', 11000, 5, 'automatic', 'petrol', 65000),
    ('Audi', 'A6', 2022, 'Бизнес', 10500, 5, 'automatic', 'diesel', 55000),
    ('Lexus', 'ES 350', 2023, 'Премиум', 14000, 5, 'automatic', 'hybrid', 90000),
    ('Porsche', 'Cayenne', 2022, 'Премиум', 22000, 5, 'automatic', 'petrol', 150000),
    ('Lada', 'Niva Travel', 2021, 'Внедорожник', 2800, 5, 'manual', 'petrol', 15000),
    ('Toyota', 'RAV4', 2023, 'Внедорожник', 6500, 5, 'automatic', 'hybrid', 45000),
    ('Jeep', 'Grand Cherokee', 2022, 'Внедорожник', 8500, 5, 'automatic', 'petrol', 50000),
    ('Skoda', 'Superb', 2022, 'Бизнес', 6500, 5, 'automatic', 'petrol', 35000),
    ('Mercedes-Benz', '300 SL', 1955, 'Коллекционные', 50000, 2, 'manual', 'petrol', 500000),
    ('Jaguar', 'E-Type', 1967, 'Коллекционные', 45000, 2, 'manual', 'petrol', 400000),
    ('Ford', 'Mustang', 1967, 'Коллекционные', 40000, 4, 'manual', 'petrol', 350000),
]

DEMO_USER = {
    'username': 'demo',
    'email': 'demo@drivern.ru',
    'password': 'demo12345',
    'first_name': 'Демо',
    'last_name': 'Пользователь',
}


class Command(BaseCommand):
    help = 'Наполняет базу демонстрационными категориями, автомобилями и заказом'

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=1, help='Сколько заказов создать для demo-пользователя')

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {}
        for slug, name, icon, description in CATEGORIES:
            category, _ = CarCategory.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'description': description},
            )
            categories[name] = category

        for brand, model, year, category_name, price, seats, transmission, fuel, deposit in CARS:
            slug = slugify(f'{brand}-{model}-{year}')
            Car.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': f'{brand} {model}',
                    'brand': brand,
                    'model': model,
                    'year': year,
                    'category': categories[category_name],
                    'price_per_day': price,
                    'seats': seats,
                    'transmission': transmission,
                    'fuel_type': fuel,
                    'deposit': deposit,
                    'short_description': f'{category_name}-класс, {year} года выпуска',
                    'description': (
                        f'Автомобиль {brand} {model} {year} года выпуска в классе «{category_name}». '
                        'Чистый салон, исправное техническое состояние, зарегистрирован в РФ. '
                        'Подходит для городских поездок, командировок и поездок за город.'
                    ),
                },
            )

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=DEMO_USER['username'],
            defaults={
                'email': DEMO_USER['email'],
                'first_name': DEMO_USER['first_name'],
                'last_name': DEMO_USER['last_name'],
            },
        )
        if created:
            user.set_password(DEMO_USER['password'])
            user.save()

        today = timezone.localdate()
        orders = [
            (5, 3, RentalOrder.Status.COMPLETED),
            (20, 4, RentalOrder.Status.NEW),
        ][:options['orders']]
        for days, car_index, status in orders:
            brand, model, year = CARS[car_index][:3]
            car = Car.objects.get(slug=slugify(f'{brand}-{model}-{year}'))
            if RentalOrder.objects.filter(user=user, car=car).exists():
                continue
            order = RentalOrder(
                user=user,
                car=car,
                start_date=today - timedelta(days=days + 2),
                end_date=today - timedelta(days=2),
                status=status,
                comment='Демонстрационный заказ',
            )
            order.save()

        self.stdout.write(self.style.SUCCESS(
            f'Готово: категорий {CarCategory.objects.count()}, '
            f'автомобилей {Car.objects.count()}, заказов {RentalOrder.objects.count()}'
        ))
        self.stdout.write(f'Демо-пользователь: {DEMO_USER["username"]} / {DEMO_USER["password"]}')
