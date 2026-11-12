# orders/services.py
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from shop.models import Product

from .models import Order, OrderItem, OrderStatusHistory

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


class OrderError(Exception):
    """Lỗi nghiệp vụ khi đặt hàng (hết hàng, giỏ rỗng...) — hiển thị cho khách."""


def _new_code():
    """Mã đơn dạng DM20261026001: DM + ngày + số thứ tự trong ngày."""
    prefix = 'DM' + timezone.localdate().strftime('%Y%m%d')
    last = Order.objects.filter(code__startswith=prefix).order_by('-code').values_list('code', flat=True).first()
    seq = int(last[len(prefix):]) + 1 if last else 1
    return f'{prefix}{seq:03d}'


def create_order(user, full_name, phone, address, items, payment_method=Order.PaymentMethod.COD, note=''):
    """Tạo đơn từ danh sách [(product_id, số lượng)].
    Giá và tổng tiền luôn lấy từ DB (không tin dữ liệu từ trình duyệt);
    kiểm tra và trừ tồn kho trong cùng một giao dịch."""
    from shop.models import Product

    if not items:
        raise OrderError('Giỏ hàng đang trống.')
    with transaction.atomic():
        ids = sorted(pid for pid, _ in items)
        # khóa các dòng sản phẩm: 2 người mua món cuối cùng sẽ phải xếp hàng, người sau báo hết hàng
        products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids, is_active=True)}
        total = 0
        rows = []
        for pid, qty in items:
            p = products.get(pid)
            if p is None or qty < 1:
                raise OrderError('Có sản phẩm không còn bán.')
            if qty > p.stock:
                raise OrderError(f'"{p.name}" chỉ còn {p.stock} sản phẩm.')
            price = p.sale_price or p.price
            total += price * qty
            rows.append((p, qty, price))

        order = Order.objects.create(
            code=_new_code(), user=user if getattr(user, 'is_authenticated', False) else None,
            full_name=full_name, phone=phone, address=address if not note else f'{address} (Ghi chú: {note})'[:255],
            total_amount=total, payment_method=payment_method,
        )
        for p, qty, price in rows:
            OrderItem.objects.create(order=order, product=p, product_name=p.name, quantity=qty, unit_price=price)
            Product.objects.filter(pk=p.pk).update(stock=F('stock') - qty)
        OrderStatusHistory.objects.create(order=order, from_status='', to_status=order.status,
                                          changed_by=order.user, note='Khách đặt hàng')
    return order
