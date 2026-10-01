import re

from django import forms
from django.utils import timezone

from .models import Car, RentalOrder

TEXT_CLASS = 'form-control'


class RentalOrderForm(forms.ModelForm):
    class Meta:
        model = RentalOrder
        fields = ('start_date', 'end_date', 'comment')
        widgets = {
            'start_date': forms.DateInput(attrs={'class': TEXT_CLASS, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': TEXT_CLASS, 'type': 'date'}),
            'comment': forms.Textarea(attrs={'class': TEXT_CLASS, 'rows': 3, 'placeholder': 'Например: нужен автомобиль на выходные'}),
        }
        labels = {
            'start_date': 'Дата начала аренды',
            'end_date': 'Дата окончания аренды',
            'comment': 'Комментарий',
        }

    def __init__(self, *args, car=None, **kwargs):
        self.car = car
        super().__init__(*args, **kwargs)
        self.fields['start_date'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_start_date(self):
        start_date = self.cleaned_data['start_date']
        if start_date < timezone.localdate():
            raise forms.ValidationError('Дата начала не может быть в прошлом.')
        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data['end_date']
        start_date = self.cleaned_data.get('start_date')
        if not start_date:
            return end_date
        if end_date < start_date:
            raise forms.ValidationError('Дата окончания раньше даты начала.')
        if end_date == start_date:
            raise forms.ValidationError('Минимальный срок аренды — 1 сутки.')
        if self.car and self.car.orders.filter(
            status__in=[RentalOrder.Status.NEW, RentalOrder.Status.CONFIRMED, RentalOrder.Status.ACTIVE],
            start_date__lt=end_date,
            end_date__gt=start_date,
        ).exists():
            raise forms.ValidationError('Эти даты уже заняты, выберите другие.')
        return end_date


class PaymentForm(forms.Form):
    card_number = forms.CharField(
        label='Номер карты',
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': TEXT_CLASS,
            'placeholder': '0000 0000 0000 0000',
            'inputmode': 'numeric',
            'autocomplete': 'cc-number',
        }),
    )
    expiry = forms.CharField(
        label='Срок действия',
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': TEXT_CLASS,
            'placeholder': 'ММ/ГГ',
            'inputmode': 'numeric',
            'autocomplete': 'cc-exp',
        }),
    )
    cvv = forms.CharField(
        label='CVV',
        max_length=3,
        widget=forms.TextInput(attrs={
            'class': TEXT_CLASS,
            'placeholder': '123',
            'type': 'password',
            'inputmode': 'numeric',
            'autocomplete': 'cc-csc',
        }),
    )
    cardholder = forms.CharField(
        label='Имя держателя карты',
        widget=forms.TextInput(attrs={
            'class': TEXT_CLASS,
            'placeholder': 'IVAN IVANOV',
            'autocomplete': 'cc-name',
        }),
    )

    def clean_card_number(self):
        value = re.sub(r'\D', '', self.cleaned_data['card_number'])
        if len(value) != 16:
            raise forms.ValidationError('Номер карты должен содержать 16 цифр.')
        return value

    def clean_expiry(self):
        value = self.cleaned_data['expiry'].strip()
        match = re.fullmatch(r'(\d{2})\s*/\s*(\d{2})', value)
        if not match:
            raise forms.ValidationError('Укажите срок действия в формате ММ/ГГ.')
        month, year = int(match.group(1)), 2000 + int(match.group(2))
        if not 1 <= month <= 12:
            raise forms.ValidationError('Некорректный месяц.')
        today = timezone.localdate()
        if (year, month) < (today.year, today.month):
            raise forms.ValidationError('Срок действия карты истёк.')
        return f'{month:02d}/{year % 100:02d}'

    def clean_cvv(self):
        value = self.cleaned_data['cvv']
        if not re.fullmatch(r'\d{3}', value):
            raise forms.ValidationError('CVV — это 3 цифры.')
        return value

    def clean_cardholder(self):
        value = self.cleaned_data['cardholder'].strip()
        if len(value) < 2:
            raise forms.ValidationError('Укажите имя держателя карты.')
        return value
