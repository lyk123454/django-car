from django.contrib import admin
from django.utils.html import format_html

from .models import Car, CarCategory, RentalOrder


@admin.register(CarCategory)
class CarCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'cars_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    @admin.display(description='Автомобилей')
    def cars_count(self, obj):
        return obj.cars.count()


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'year', 'category', 'price_per_day', 'is_available', 'photo')
    list_filter = ('category', 'transmission', 'fuel_type', 'is_available')
    search_fields = ('name', 'brand', 'model')
    prepopulated_fields = {'slug': ('brand', 'model', 'year')}
    list_editable = ('price_per_day', 'is_available')
    readonly_fields = ('created_at', 'photo_preview')

    @admin.display(description='Фото')
    def photo_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:80px;border-radius:6px" />', obj.image.url)
        return '—'

    @admin.display(boolean=True, description='Есть фото')
    def photo(self, obj):
        return bool(obj.image)


@admin.register(RentalOrder)
class RentalOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'car', 'start_date', 'end_date', 'days', 'total_price', 'status', 'is_paid')
    list_filter = ('status', 'is_paid', 'car__category')
    search_fields = ('user__username', 'user__email', 'car__brand', 'car__model')
    list_editable = ('status', 'is_paid')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at',)
