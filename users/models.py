from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField('Телефон', max_length=20, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    driver_license = models.CharField('Водительское удостоверение', max_length=20, blank=True)
    about = models.TextField('О себе', blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль: {self.user.username}'

    @property
    def orders_count(self):
        return self.user.orders.exclude(status='cancelled').count()

    @property
    def rented_days(self):
        result = self.user.orders.exclude(status='cancelled').aggregate(total=Sum('days'))
        return result['total'] or 0

    @property
    def spent_money(self):
        result = self.user.orders.exclude(status='cancelled').aggregate(total=Sum('total_price'))
        return result['total'] or 0


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
