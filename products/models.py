from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class CarCategory(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Адрес (slug)', max_length=100, unique=True)
    icon = models.CharField('Иконка Font Awesome', max_length=50, default='fa-car')
    description = models.TextField('Описание', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:cars_by_category', kwargs={'category_slug': self.slug})


class Car(models.Model):
    class Transmission(models.TextChoices):
        MANUAL = 'manual', 'Механика'
        AUTOMATIC = 'automatic', 'Автомат'

    class FuelType(models.TextChoices):
        PETROL = 'petrol', 'Бензин'
        DIESEL = 'diesel', 'Дизель'
        ELECTRIC = 'electric', 'Электро'
        HYBRID = 'hybrid', 'Гибрид'

    name = models.CharField('Название', max_length=128)
    slug = models.SlugField('Адрес (slug)', max_length=140, unique=True)
    brand = models.CharField('Марка', max_length=64)
    model = models.CharField('Модель', max_length=64)
    year = models.PositiveSmallIntegerField(
        'Год выпуска',
        validators=[MinValueValidator(1990), MaxValueValidator(2100)],
    )
    category = models.ForeignKey(
        CarCategory,
        verbose_name='Категория',
        on_delete=models.PROTECT,
        related_name='cars',
    )
    image = models.ImageField('Фото', upload_to='cars/', blank=True)
    short_description = models.CharField('Краткое описание', max_length=160, blank=True)
    description = models.TextField('Полное описание', blank=True)
    price_per_day = models.DecimalField(
        'Цена за сутки, ₽',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    deposit = models.DecimalField(
        'Залог, ₽',
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    seats = models.PositiveSmallIntegerField('Мест', default=5)
    transmission = models.CharField(
        'Коробка передач',
        max_length=10,
        choices=Transmission.choices,
        default=Transmission.MANUAL,
    )
    fuel_type = models.CharField(
        'Топливо',
        max_length=10,
        choices=FuelType.choices,
        default=FuelType.PETROL,
    )
    is_available = models.BooleanField('Доступна для аренды', default=True)
    created_at = models.DateTimeField('Добавлена', auto_now_add=True)

    class Meta:
        verbose_name = 'Автомобиль'
        verbose_name_plural = 'Автомобили'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.brand} {self.model} ({self.year})'

    def get_absolute_url(self):
        return reverse('products:car_detail', kwargs={'slug': self.slug})

    @property
    def has_photo(self):
        return bool(self.image)


class RentalOrder(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтверждён'
        ACTIVE = 'active', 'Активная аренда'
        COMPLETED = 'completed', 'Завершён'
        CANCELLED = 'cancelled', 'Отменён'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='orders',
    )
    car = models.ForeignKey(
        Car,
        verbose_name='Автомобиль',
        on_delete=models.PROTECT,
        related_name='orders',
    )
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    days = models.PositiveSmallIntegerField('Суток', default=1)
    total_price = models.DecimalField('Итого, ₽', max_digits=10, decimal_places=2, default=0)
    comment = models.TextField('Комментарий', blank=True)
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=Status.choices,
        default=Status.NEW,
    )
    is_paid = models.BooleanField('Оплачен', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.pk} — {self.car} ({self.user})'

    def save(self, *args, **kwargs):
        self.days = max((self.end_date - self.start_date).days, 1)
        self.total_price = self.car.price_per_day * self.days
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status in {self.Status.NEW, self.Status.CONFIRMED, self.Status.ACTIVE}

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])

    @property
    def is_overdue(self):
        return self.status == self.Status.ACTIVE and self.end_date < timezone.localdate()
