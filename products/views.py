from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, TemplateView

from .forms import PaymentForm, RentalOrderForm
from .models import Car, CarCategory, RentalOrder


class IndexView(ListView):
    template_name = 'products/index.html'
    context_object_name = 'featured_cars'

    def get_queryset(self):
        return Car.objects.filter(is_available=True).exclude(category__slug='collector')[:6]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = CarCategory.objects.all()
        context['collector_cars'] = Car.objects.filter(category__slug='collector')
        return context


class CarListView(ListView):
    model = Car
    template_name = 'products/products.html'
    context_object_name = 'cars'
    paginate_by = 9

    def get_queryset(self):
        queryset = Car.objects.select_related('category')
        self.category_slug = self.kwargs.get('category_slug')
        if self.category_slug:
            queryset = queryset.filter(category__slug=self.category_slug)

        self.query = self.request.GET.get('q', '').strip()
        if self.query:
            queryset = queryset.filter(
                Q(name__icontains=self.query)
                | Q(brand__icontains=self.query)
                | Q(model__icontains=self.query)
            )

        self.transmission = self.request.GET.get('transmission', '')
        if self.transmission in dict(Car.Transmission.choices):
            queryset = queryset.filter(transmission=self.transmission)

        self.only_available = self.request.GET.get('available') == '1'
        if self.only_available:
            queryset = queryset.filter(is_available=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'categories': CarCategory.objects.all(),
            'category': CarCategory.objects.filter(slug=self.category_slug).first(),
            'transmissions': Car.Transmission.choices,
            'query': self.query,
            'selected_transmission': self.transmission,
            'only_available': self.only_available,
        })
        return context


class CarDetailView(DetailView):
    model = Car
    template_name = 'products/car_detail.html'
    context_object_name = 'car'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = RentalOrderForm(car=self.object)
        context['similar_cars'] = Car.objects.filter(category=self.object.category).exclude(pk=self.object.pk)[:3]
        return context


class AboutView(TemplateView):
    template_name = 'products/about.html'


class TermsView(TemplateView):
    template_name = 'products/terms.html'


class UsefulView(TemplateView):
    template_name = 'products/useful.html'


class ContactsView(TemplateView):
    template_name = 'products/contacts.html'


@login_required
def create_order(request, slug):
    car = get_object_or_404(Car, slug=slug, is_available=True)
    form = RentalOrderForm(request.POST or None, car=car)

    if request.method == 'POST' and form.is_valid():
        order = form.save(commit=False)
        order.user = request.user
        order.car = car
        order.save()
        messages.success(request, f'Заказ на {car.brand} {car.model} создан. Перейдите к оплате.')
        return redirect('products:pay_order', pk=order.pk)

    return render(request, 'products/car_detail.html', {
        'car': car,
        'form': form,
        'similar_cars': Car.objects.filter(category=car.category).exclude(pk=car.pk)[:3],
    })


@login_required
def pay_order(request, pk):
    order = get_object_or_404(RentalOrder, pk=pk, user=request.user)
    if order.is_paid:
        messages.info(request, f'Заказ #{order.pk} уже оплачен.')
        return redirect('products:my_orders')

    form = PaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        order.is_paid = True
        order.save(update_fields=['is_paid'])
        messages.success(request, f'Заказ #{order.pk} оплачен. Спасибо!')
        return redirect('products:my_orders')

    return render(request, 'products/payment.html', {'order': order, 'form': form})


@login_required
def my_orders(request):
    orders = request.user.orders.select_related('car', 'car__category')
    return render(request, 'products/my_orders.html', {'orders': orders})


@login_required
def cancel_order(request, pk):
    order = get_object_or_404(RentalOrder, pk=pk, user=request.user)
    if order.status == RentalOrder.Status.COMPLETED:
        messages.error(request, 'Завершённый заказ нельзя отменить.')
    else:
        order.cancel()
        messages.success(request, 'Заказ отменён.')
    return redirect('products:my_orders')
