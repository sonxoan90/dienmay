from django.contrib.auth.models import User
from django.test import TestCase

from shop.models import Brand, Category, Product

from .models import Order, OrderItem, OrderStatusHistory
from .services import change_status

S = Order.Status


class ChangeStatusTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Tivi', slug='tivi')
        brand = Brand.objects.create(name='LG', slug='lg')
        self.product = Product.objects.create(
            category=cat, brand=brand, name='Tivi LG', slug='tivi-lg', price=1000000, stock=5)
        self.admin = User.objects.create_superuser('admin', 'a@a.com', 'x')

    def make_order(self, code, method=Order.PaymentMethod.COD):
        order = Order.objects.create(
            code=code, full_name='A', phone='0900000001', address='HN',
            total_amount=1000000, payment_method=method)
        OrderItem.objects.create(order=order, product=self.product, product_name='Tivi LG',
                                 quantity=2, unit_price=1000000)
        return order

    def test_full_flow_cod_marks_paid_and_logs_history(self):
        o = self.make_order('T1')
        for s in (S.CONFIRMED, S.SHIPPING, S.DELIVERED):
            o = change_status(o, s, user=self.admin)
        self.assertEqual(o.status, S.DELIVERED)
        self.assertEqual(o.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(OrderStatusHistory.objects.filter(order=o).count(), 3)

    def test_cancel_restores_stock(self):
        o = self.make_order('T2')
        change_status(o, S.CANCELLED, user=self.admin)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

    def test_invalid_transition_rejected(self):
        o = self.make_order('T3')
        change_status(o, S.CANCELLED)
        with self.assertRaises(ValueError):
            change_status(o, S.SHIPPING)
        self.assertEqual(OrderStatusHistory.objects.filter(order=o).count(), 1)


from django.urls import reverse

from .models import Cart

PW = 'Mk-rat-manh-123'
INFO = {'full_name': 'Nguyen A', 'phone': '0912345678', 'address': 'Ha Noi',
        'note': '', 'payment_method': 'COD'}


class StorefrontOrderTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Tivi', slug='tivi')
        brand = Brand.objects.create(name='LG', slug='lg')
        self.p1 = Product.objects.create(category=cat, brand=brand, name='Tivi 1', slug='tivi-1',
                                         price=1000000, sale_price=900000, stock=3)
        self.p2 = Product.objects.create(category=cat, brand=brand, name='Tivi 2', slug='tivi-2',
                                         price=2000000, stock=5)

    def add(self, p, qty=1):
        return self.client.post(reverse('cart_add', args=[p.pk]), {'quantity': qty})

    def test_guest_cart_in_session_capped_by_stock(self):
        self.add(self.p1, 2)
        self.add(self.p1, 5)
        self.assertEqual(self.client.session['cart'], {str(self.p1.pk): 3})
        self.assertEqual(self.client.get(reverse('cart')).context['total'], 2700000)
        self.client.post(reverse('cart_remove', args=[self.p1.pk]))
        self.assertEqual(self.client.session['cart'], {})

    def test_cart_merged_into_db_on_login(self):
        user = User.objects.create_user('u', password=PW)
        Cart.objects.create(user=user).items.create(product=self.p1, quantity=1)
        self.add(self.p1, 1)
        self.add(self.p2, 2)
        self.client.login(username='u', password=PW)
        items = {i.product_id: i.quantity for i in user.cart.items.all()}
        self.assertEqual(items, {self.p1.pk: 2, self.p2.pk: 2})
        self.assertNotIn('cart', self.client.session)

    def test_cod_checkout_guest_server_side_total_and_stock(self):
        self.add(self.p1, 2)
        r = self.client.post(reverse('checkout'), {**INFO, 'source': 'cart'})
        order = Order.objects.get()
        self.assertRedirects(r, reverse('order_success', args=[order.code]))
        self.assertEqual(order.total_amount, 1800000)       # giá khuyến mãi lấy từ DB
        self.assertTrue(order.code.startswith('DM') and len(order.code) == 13)
        self.assertIsNone(order.user)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 1)
        self.assertEqual(self.client.session['cart'], {})
        self.assertEqual(OrderStatusHistory.objects.filter(order=order).count(), 1)

    def test_buy_now_keeps_cart(self):
        self.add(self.p2, 1)
        self.client.post(reverse('buy_now', args=[self.p1.pk]), {'quantity': 1})
        self.client.post(reverse('checkout'), {**INFO, 'source': 'buy_now'})
        order = Order.objects.get()
        self.assertEqual([i.product_id for i in order.items.all()], [self.p1.pk])
        self.assertEqual(self.client.session['cart'], {str(self.p2.pk): 1})

    def test_cannot_oversell(self):
        from .services import OrderError, create_order
        Product.objects.filter(pk=self.p1.pk).update(stock=1)   # người khác mua trước
        with self.assertRaises(OrderError):
            create_order(None, 'A', '0912345678', 'HN', [(self.p1.pk, 3), (self.p2.pk, 1)])
        self.assertEqual(Order.objects.count(), 0)
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.stock, 5)                     # không trừ kho dở dang

    def test_checkout_page_caps_quantity_to_current_stock(self):
        self.add(self.p1, 3)
        Product.objects.filter(pk=self.p1.pk).update(stock=1)
        self.client.post(reverse('checkout'), {**INFO, 'source': 'cart'})
        self.assertEqual(Order.objects.get().items.get().quantity, 1)

    def test_guest_lookup_and_cancel_restores_stock(self):
        self.add(self.p1, 2)
        self.client.post(reverse('checkout'), {**INFO, 'source': 'cart'})
        order = Order.objects.get()
        other = self.client_class()                       # trình duyệt khác, chưa có quyền xem
        self.assertRedirects(other.get(reverse('order_detail', args=[order.code])), reverse('order_lookup'))
        bad = other.post(reverse('order_lookup'), {'code': order.code, 'phone': '0999999999'})
        self.assertEqual(bad.status_code, 200)
        ok = other.post(reverse('order_lookup'), {'code': order.code, 'phone': '0912345678'})
        self.assertRedirects(ok, reverse('order_detail', args=[order.code]))
        other.post(reverse('order_cancel', args=[order.code]))
        order.refresh_from_db()
        self.p1.refresh_from_db()
        self.assertEqual(order.status, S.CANCELLED)
        self.assertEqual(self.p1.stock, 3)

    def test_logged_in_user_sees_own_orders_and_cannot_cancel_confirmed(self):
        user = User.objects.create_user('u', password=PW)
        self.client.login(username='u', password=PW)
        self.add(self.p2, 1)
        self.client.post(reverse('checkout'), {**INFO, 'source': 'cart'})
        order = Order.objects.get()
        self.assertEqual(order.user, user)
        self.assertContains(self.client.get(reverse('my_orders')), order.code)
        change_status(order, S.CONFIRMED)
        self.client.post(reverse('order_cancel', args=[order.code]))
        order.refresh_from_db()
        self.assertEqual(order.status, S.CONFIRMED)
