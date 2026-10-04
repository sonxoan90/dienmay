from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField('Tên danh mục', max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField('Mô tả', blank=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField('Tên nhãn hàng', max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    # PROTECT: không cho xóa danh mục/nhãn hàng khi còn sản phẩm
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    name = models.CharField('Tên sản phẩm', max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    price = models.DecimalField('Giá', max_digits=12, decimal_places=0)
    sale_price = models.DecimalField('Giá khuyến mãi', max_digits=12, decimal_places=0, null=True, blank=True)
    stock = models.PositiveIntegerField('Tồn kho', default=0)
    image = models.ImageField(upload_to='products/', blank=True)
    specs = models.TextField('Thông số', blank=True)
    is_active = models.BooleanField('Đang bán', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Profile(models.Model):
    # Quan hệ 1-1 với User có sẵn của Django
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField('Số điện thoại', max_length=15, blank=True)
    address = models.CharField('Địa chỉ', max_length=255, blank=True)

    def __str__(self):
        return f'Hồ sơ {self.user}'