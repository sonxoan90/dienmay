# orders/cart.py
"""Giỏ hàng dùng chung cho 2 loại khách:
- chưa đăng nhập: lưu trong session  {'<product_id>': số_lượng}
- đã đăng nhập: lưu trong bảng Cart / CartItem
Các view chỉ gọi các hàm ở đây, không cần biết giỏ nằm ở đâu."""
from shop.models import Product

from .models import Cart, CartItem

SESSION_KEY = 'cart'


def _session_cart(request):
    return request.session.setdefault(SESSION_KEY, {})


def _db_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _quantities(request):
    """Trả về dict {product_id: số lượng} từ nơi đang lưu giỏ."""
    if request.user.is_authenticated:
        return {i.product_id: i.quantity for i in _db_cart(request.user).items.all()}
    return {int(pid): q for pid, q in _session_cart(request).items()}


def _save(request, pid, qty):
    """Ghi số lượng của 1 sản phẩm; qty <= 0 thì xóa khỏi giỏ."""
    if request.user.is_authenticated:
        cart = _db_cart(request.user)
        if qty <= 0:
            CartItem.objects.filter(cart=cart, product_id=pid).delete()
        else:
            CartItem.objects.update_or_create(cart=cart, product_id=pid, defaults={'quantity': qty})
    else:
        data = _session_cart(request)
        if qty <= 0:
            data.pop(str(pid), None)
        else:
            data[str(pid)] = qty
        request.session.modified = True


def add(request, product, qty=1):
    """Thêm vào giỏ (cộng dồn), không vượt tồn kho. Trả về số lượng thực tế trong giỏ."""
    new_qty = min(_quantities(request).get(product.pk, 0) + qty, product.stock)
    _save(request, product.pk, new_qty)
    return new_qty


def set_quantity(request, product, qty):
    _save(request, product.pk, min(qty, product.stock))


def remove(request, product_id):
    _save(request, product_id, 0)


def clear(request):
    if request.user.is_authenticated:
        _db_cart(request.user).items.all().delete()
    else:
        request.session.pop(SESSION_KEY, None)


def lines(request):
    """Danh sách dòng trong giỏ kèm giá lấy từ DB: [{'product','quantity','unit_price','subtotal'}]."""
    qty = _quantities(request)
    products = Product.objects.filter(pk__in=qty, is_active=True)
    result = []
    for p in products:
        q = min(qty[p.pk], p.stock)           # tồn kho có thể đã giảm từ lúc thêm
        if q <= 0:
            continue
        price = p.sale_price or p.price
        result.append({'product': p, 'quantity': q, 'unit_price': price, 'subtotal': price * q})
    return result


def total(line_list):
    return sum(l['subtotal'] for l in line_list)


def count(request):
    return sum(_quantities(request).values())


def merge_session_into_db(request, user):
    """Khi đăng nhập: cộng dồn giỏ session vào giỏ DB rồi xóa giỏ session."""
    data = request.session.pop(SESSION_KEY, None)
    if not data:
        return
    cart = _db_cart(user)
    existing = {i.product_id: i for i in cart.items.all()}
    for pid, q in data.items():
        product = Product.objects.filter(pk=int(pid), is_active=True).first()
        if not product:
            continue
        item = existing.get(product.pk)
        new_qty = min((item.quantity if item else 0) + q, product.stock)
        if new_qty > 0:
            CartItem.objects.update_or_create(cart=cart, product=product, defaults={'quantity': new_qty})
