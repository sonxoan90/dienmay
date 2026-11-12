# orders/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from shop.models import Product

from . import cart
from .forms import CheckoutForm, LookupForm
from .models import Order
from .services import OrderError, change_status, create_order

BUY_NOW_KEY = 'buy_now'        # mua ngay: lưu riêng trong session, không đụng vào giỏ
ACCESS_KEY = 'order_access'    # mã các đơn khách vãng lai được phép xem


def _qty(request):
    q = request.POST.get('quantity', '1')
    return int(q) if q.isdigit() and int(q) > 0 else 1


def _grant_access(request, order):
    codes = request.session.get(ACCESS_KEY, [])
    if order.code not in codes:
        request.session[ACCESS_KEY] = codes + [order.code]


def _can_view(request, order):
    if request.user.is_authenticated and order.user_id == request.user.pk:
        return True
    return order.code in request.session.get(ACCESS_KEY, [])


# ---------- Giỏ hàng ----------
def cart_detail(request):
    line_list = cart.lines(request)
    return render(request, 'orders/cart.html', {'lines': line_list, 'total': cart.total(line_list)})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if product.stock < 1:
        messages.error(request, 'Sản phẩm đã hết hàng.')
        return redirect('product_detail', slug=product.slug)
    got = cart.add(request, product, _qty(request))
    messages.success(request, f'Đã thêm vào giỏ ({got} × {product.name}).')
    return redirect('cart')


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    qty = request.POST.get('quantity', '')
    cart.set_quantity(request, product, int(qty) if qty.isdigit() else 1)
    return redirect('cart')


@require_POST
def cart_remove(request, product_id):
    cart.remove(request, product_id)
    return redirect('cart')


# ---------- Mua ngay + thanh toán ----------
@require_POST
def buy_now(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    qty = min(_qty(request), product.stock)
    if qty < 1:
        messages.error(request, 'Sản phẩm đã hết hàng.')
        return redirect('product_detail', slug=product.slug)
    request.session[BUY_NOW_KEY] = {'product_id': product.pk, 'quantity': qty}
    return redirect('/thanh-toan/?mua-ngay=1')


def _buy_now_lines(request):
    bn = request.session.get(BUY_NOW_KEY)
    if not bn:
        return []
    p = Product.objects.filter(pk=bn['product_id'], is_active=True).first()
    if not p or p.stock < 1:
        return []
    q = min(bn['quantity'], p.stock)
    price = p.sale_price or p.price
    return [{'product': p, 'quantity': q, 'unit_price': price, 'subtotal': price * q}]


def checkout(request):
    buy_now_mode = request.GET.get('mua-ngay') == '1' or request.POST.get('source') == 'buy_now'
    line_list = _buy_now_lines(request) if buy_now_mode else cart.lines(request)
    items = [(l['product'].pk, l['quantity']) for l in line_list]
    if not line_list:
        messages.info(request, 'Chưa có sản phẩm để thanh toán.')
        return redirect('cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                order = create_order(request.user, d['full_name'], d['phone'], d['address'],
                                     items, d['payment_method'], d['note'])
            except OrderError as e:
                messages.error(request, str(e))
                return redirect('/thanh-toan/?mua-ngay=1' if buy_now_mode else 'cart')
            if buy_now_mode:
                request.session.pop(BUY_NOW_KEY, None)   # mua ngay: giỏ giữ nguyên
            else:
                cart.clear(request)
            _grant_access(request, order)
            return redirect('order_success', code=order.code)
    else:
        initial = {}
        if request.user.is_authenticated:                 # điền sẵn cho khách đã đăng nhập
            profile = getattr(request.user, 'profile', None)
            initial = {'full_name': request.user.first_name,
                       'phone': profile.phone if profile else '',
                       'address': profile.address if profile else ''}
        form = CheckoutForm(initial=initial)
    return render(request, 'orders/checkout.html', {
        'form': form, 'lines': line_list, 'total': cart.total(line_list),
        'source': 'buy_now' if buy_now_mode else 'cart'})


# ---------- Theo dõi đơn ----------
def order_success(request, code):
    order = get_object_or_404(Order, code=code)
    if not _can_view(request, order):
        return redirect('order_lookup')
    return render(request, 'orders/success.html', {'order': order})


@login_required
def my_orders(request):
    return render(request, 'orders/my_orders.html', {'orders': request.user.orders.order_by('-created_at')})


def order_lookup(request):
    form = LookupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        order = Order.objects.filter(code=form.cleaned_data['code'].strip().upper(),
                                     phone=form.cleaned_data['phone'].strip()).first()
        if order:
            _grant_access(request, order)
            return redirect('order_detail', code=order.code)
        messages.error(request, 'Không tìm thấy đơn hàng khớp mã và số điện thoại.')
    return render(request, 'orders/lookup.html', {'form': form})


def order_detail(request, code):
    order = get_object_or_404(Order, code=code)
    if not _can_view(request, order):
        return redirect('order_lookup')
    return render(request, 'orders/order_detail.html', {
        'order': order, 'items': order.items.all(), 'history': order.history.all()})


@require_POST
def order_cancel(request, code):
    order = get_object_or_404(Order, code=code)
    if not _can_view(request, order):
        return redirect('order_lookup')
    if order.status != Order.Status.PENDING:        # khách chỉ hủy khi còn Chờ xác nhận
        messages.error(request, 'Đơn đã được xử lý, không thể tự hủy. Vui lòng liên hệ cửa hàng.')
    else:
        change_status(order, Order.Status.CANCELLED,
                      user=request.user if request.user.is_authenticated else None, note='Khách tự hủy')
        messages.success(request, 'Đã hủy đơn hàng.')
    return redirect('order_detail', code=code)
