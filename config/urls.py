# config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('shop.urls')),
    path('', include('orders.urls')),
    path('dashboard/', include('dashboard.urls')),
]

if settings.DEBUG:  # chỉ dùng khi phát triển; khi deploy cấu hình riêng ở tuần 7
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)