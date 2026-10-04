# shop/urls.py (orders/urls.py và dashboard/urls.py viết giống hệt)
from django.urls import path

urlpatterns = [
    # các đường dẫn sẽ thêm ở tuần 3–6
]

# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('shop.urls')),
    path('', include('orders.urls')),
    path('dashboard/', include('dashboard.urls')),
]
