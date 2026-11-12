from django.urls import path

from . import views

urlpatterns = [
    path('gio-hang/', views.cart_detail, name='cart'),
    path('gio-hang/them/<int:product_id>/', views.cart_add, name='cart_add'),
    path('gio-hang/sua/<int:product_id>/', views.cart_update, name='cart_update'),
    path('gio-hang/xoa/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('mua-ngay/<int:product_id>/', views.buy_now, name='buy_now'),
    path('thanh-toan/', views.checkout, name='checkout'),
    path('dat-hang-thanh-cong/<str:code>/', views.order_success, name='order_success'),
    path('don-hang-cua-toi/', views.my_orders, name='my_orders'),
    path('tra-cuu-don/', views.order_lookup, name='order_lookup'),
    path('don-hang/<str:code>/', views.order_detail, name='order_detail'),
    path('don-hang/<str:code>/huy/', views.order_cancel, name='order_cancel'),
]
