from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models

from shop.models import Product


class Cart(models.Model):
    # Chỉ cho khách đã đăng nhập; khách vãng lai dùng session
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Giỏ hàng của {self.user}'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_cart_product'),
        ]

    def __str__(self):
        return f'{self.product} x {self.quantity}'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ xác nhận'
        CONFIRMED = 'CONFIRMED', 'Đã xác nhận'
        SHIPPING = 'SHIPPING', 'Đang giao'
        DELIVERED = 'DELIVERED', 'Đã giao'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    class PaymentMethod(models.TextChoices):
        COD = 'COD', 'Thanh toán khi nhận hàng'
        VNPAY = 'VNPAY', 'VNPay'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'UNPAID', 'Chưa thanh toán'
        PAID = 'PAID', 'Đã thanh toán'
        REFUNDED = 'REFUNDED', 'Hoàn tiền'

    code = models.CharField('Mã đơn', max_length=20, unique=True)
    # SET_NULL: xóa user vẫn giữ đơn; null cho khách vãng lai
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    full_name = models.CharField('Họ tên người nhận', max_length=100)
    phone = models.CharField('Số điện thoại', max_length=15, db_index=True)
    address = models.CharField('Địa chỉ giao', max_length=255)
    total_amount = models.DecimalField('Tổng tiền', max_digits=12, decimal_places=0)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField('Tên lúc mua', max_length=200)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField('Giá lúc mua', max_digits=12, decimal_places=0)

    def __str__(self):
        return f'{self.product_name} x {self.quantity}'


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    from_status = models.CharField(max_length=20, blank=True)  # trống khi đơn vừa tạo
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['changed_at']

    def __str__(self):
        return f'{self.order}: {self.from_status or "-"} → {self.to_status}'


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Đang chờ'
        SUCCESS = 'SUCCESS', 'Thành công'
        FAILED = 'FAILED', 'Thất bại'

    # PROTECT: giữ lịch sử thanh toán để đối soát
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments')
    vnp_txn_ref = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    response_code = models.CharField(max_length=10, blank=True)
    vnp_transaction_no = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)  # toàn bộ tham số VNPay gửi về

    def __str__(self):
        return f'{self.vnp_txn_ref} ({self.get_status_display()})'
