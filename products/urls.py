from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('cars/', views.CarListView.as_view(), name='cars'),
    path('cars/<slug:category_slug>/', views.CarListView.as_view(), name='cars_by_category'),    path('car/<slug:slug>/', views.CarDetailView.as_view(), name='car_detail'),
    path('car/<slug:slug>/order/', views.create_order, name='create_order'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('useful/', views.UsefulView.as_view(), name='useful'),
    path('contacts/', views.ContactsView.as_view(), name='contacts'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-orders/<int:pk>/pay/', views.pay_order, name='pay_order'),
    path('my-orders/<int:pk>/cancel/', views.cancel_order, name='cancel_order'),
]
