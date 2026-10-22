from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Profile
from .utils import normalize_phone

TEXT_CLASS = 'form-control'


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label='E-mail',
        required=True,
        widget=forms.EmailInput(attrs={'class': TEXT_CLASS, 'placeholder': 'mail@example.com'}),
    )
    first_name = forms.CharField(
        label='Имя',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': 'Иван'}),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': 'Петров'}),
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': '+7 900 000-00-00'}),
    )
    birth_date = forms.DateField(
        label='Дата рождения',
        widget=forms.DateInput(attrs={'class': TEXT_CLASS, 'type': 'date'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': 'Логин'}),
            'email': forms.EmailInput(attrs={'class': TEXT_CLASS, 'placeholder': 'mail@example.com'}),
            'first_name': forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': 'Иван'}),
            'last_name': forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': 'Петров'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        order = ('username', 'first_name', 'last_name', 'email', 'phone', 'birth_date', 'password1', 'password2')
        self.fields = {name: self.fields[name] for name in order if name in self.fields}
        for name, field in self.fields.items():
            if name in {'password1', 'password2'}:
                field.widget.attrs['class'] = TEXT_CLASS
                field.widget.attrs['placeholder'] = 'Пароль'
            field.label = {
                'username': 'Логин',
                'email': 'E-mail',
                'first_name': 'Имя',
                'last_name': 'Фамилия',
                'password1': 'Пароль',
                'password2': 'Повторите пароль',
                'birth_date': 'Дата рождения',
            }.get(name, field.label)

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if not birth_date:
            return birth_date
        today = timezone.localdate()
        if birth_date > today:
            raise forms.ValidationError('Дата рождения не может быть в будущем.')
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 19:
            raise forms.ValidationError('Регистрация доступна с 19 лет. Укажите корректную дату рождения.')
        return birth_date

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            return ''
        normalized = normalize_phone(phone)
        if not normalized:
            raise forms.ValidationError('Введите корректный номер телефона, например +7 900 000-00-00')
        if Profile.objects.filter(phone__in=[phone, normalized]).exists():
            raise forms.ValidationError('Этот номер телефона уже зарегистрирован')
        return normalized

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
            Profile.objects.filter(user=user).update(
                phone=self.cleaned_data.get('phone', ''),
                birth_date=self.cleaned_data.get('birth_date'),
            )
        return user


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин или телефон',
        widget=forms.TextInput(attrs={'class': TEXT_CLASS}),
    )
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': TEXT_CLASS}))
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Неверное имя пользователя или пароль.',
    }

    def clean(self):
        raw = (self.cleaned_data.get('username') or '').strip()
        if raw:
            normalized = normalize_phone(raw)
            profile = None
            if normalized:
                profile = Profile.objects.filter(phone=normalized).select_related('user').first()
            if profile is None and normalized:
                profile = Profile.objects.filter(phone=raw).select_related('user').first()
            if profile is None and normalized:
                for p in Profile.objects.exclude(phone='').select_related('user'):
                    if normalize_phone(p.phone) == normalized:
                        profile = p
                        break
            if profile is not None:
                self.cleaned_data['username'] = profile.user.username
            elif not User.objects.filter(username__iexact=raw).exists():
                raise forms.ValidationError('Пользователь не зарегистрирован')
        return super().clean()


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone', 'birth_date', 'driver_license', 'about')
        widgets = {
            'phone': forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': '+7 900 000-00-00'}),
            'birth_date': forms.DateInput(attrs={'class': TEXT_CLASS, 'type': 'date'}),
            'driver_license': forms.TextInput(attrs={'class': TEXT_CLASS, 'placeholder': '99 12 345678'}),
            'about': forms.Textarea(attrs={'class': TEXT_CLASS, 'rows': 4}),
        }
        labels = {
            'phone': 'Телефон',
            'birth_date': 'Дата рождения',
            'driver_license': 'Водительское удостоверение',
            'about': 'О себе',
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone:
            return ''
        normalized = normalize_phone(phone)
        if not normalized:
            raise forms.ValidationError('Введите корректный номер телефона, например +7 900 000-00-00')
        duplicate = Profile.objects.filter(phone__in=[phone, normalized]).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError('Этот номер телефона уже используется другим пользователем')
        return normalized

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date and birth_date > timezone.localdate():
            raise forms.ValidationError('Дата рождения не может быть в будущем.')
        return birth_date
