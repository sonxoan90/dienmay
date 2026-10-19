# orders/services.py
from django.db import transaction
from django.db.models import F

from shop.models import Product

from .models import Order, OrderStatusHistory

S = Order.Status

# Luồng hợp lệ: trạng thái hiện tại -> các trạng thái được phép chuyển tới
ALLOWED = {
    S.PENDING: {S.CONFIRMED, S.CANCELLED},
    S.CONFIRMED: {S.SHIPPING, S.CANCELLED},
    S.SHIPPING: {S.DELIVERED, S.CANCELLED},
    S.DELIVERED: set(),   # trạng thái cuối
    S.CANCELLED: set(),   # trạng thái cuối
}


def change_status(order, new_status, user=None, note=''):
    """Đổi trạng thái đơn; sai luồng thì báo lỗi ValueError."""
    with transaction.atomic():  # tất cả thành công, hoặc không có gì thay đổi
        # khóa dòng đơn này cho tới khi xong, tránh 2 người đổi cùng lúc
        order = Order.objects.select_for_update().get(pk=order.pk)
        if new_status not in ALLOWED[order.status]:
            raise ValueError(
                f'Đơn {order.code}: không thể chuyển từ "{order.get_status_display()}" sang "{S(new_status).label}"'
            )
        old_status = order.status
        order.status = new_status

        if new_status == S.CANCELLED:
            # hoàn lại tồn kho; F() cộng ngay trong database, không bị ghi đè
            for item in order.items.all():
                Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)

        if new_status == S.DELIVERED and order.payment_method == Order.PaymentMethod.COD:
            order.payment_status = Order.PaymentStatus.PAID  # COD: thu tiền khi giao xong

        order.save(update_fields=['status', 'payment_status'])
        OrderStatusHistory.objects.create(
            order=order, from_status=old_status, to_status=new_status, changed_by=user, note=note
        )
    return order