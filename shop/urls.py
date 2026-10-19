# shop/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path('', views.home, name='home'),
    path('san-pham/', views.product_list, name='product_list'),
    path('san-pham/<slug:slug>/', views.product_detail, name='product_detail'),
    path('dang-ky/', views.signup, name='signup'),
    path('dang-nhap/', auth_views.LoginView.as_view(authentication_form=LoginForm), name='login'),
    path('dang-xuat/', auth_views.LogoutView.as_view(), name='logout'),
    path('tai-khoan/', views.account, name='account'),
]