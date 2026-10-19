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
