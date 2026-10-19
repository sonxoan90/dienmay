from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Brand, Category, Product, Profile


class StorefrontTests(TestCase):
    def setUp(self):
        self.tivi = Category.objects.create(name='Tivi', slug='tivi')
        self.tl = Category.objects.create(name='Tủ lạnh', slug='tu-lanh')
        self.ss = Brand.objects.create(name='Samsung', slug='samsung')
        self.lg = Brand.objects.create(name='LG', slug='lg')
        for i in range(14):
            Product.objects.create(category=self.tivi, brand=self.ss, name=f'Tivi Samsung {i}',
                                   slug=f'tivi-ss-{i}', price=1000000 + i, stock=3)
        Product.objects.create(category=self.tl, brand=self.lg, name='Tủ lạnh LG', slug='tu-lanh-lg',
                               price=500000, sale_price=400000, stock=1)
        Product.objects.create(category=self.tl, brand=self.lg, name='Đã ẩn', slug='da-an',
                               price=1, stock=1, is_active=False)

    def test_public_pages_ok_for_anonymous(self):
        for name in ('home', 'product_list', 'login', 'signup'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_pagination_12_per_page_and_hidden_excluded(self):
        r = self.client.get(reverse('product_list'))
        self.assertEqual(len(r.context['page']), 12)
        self.assertEqual(r.context['page'].paginator.count, 15)

    def test_search_filter_sort(self):
        r = self.client.get(reverse('product_list'), {'q': 'samsung'})
        self.assertEqual(r.context['page'].paginator.count, 14)
        r = self.client.get(reverse('product_list'), {'category': 'tu-lanh', 'brand': 'lg'})
        self.assertEqual(r.context['page'].paginator.count, 1)
        r = self.client.get(reverse('product_list'), {'sort': 'price_asc', 'min_price': 'abc'})
        prices = [p.final_price for p in r.context['page']]
        self.assertEqual(prices, sorted(prices))

    def test_detail_and_404(self):
        self.assertEqual(self.client.get(reverse('product_detail', args=['tu-lanh-lg'])).status_code, 200)
        self.assertEqual(self.client.get(reverse('product_detail', args=['da-an'])).status_code, 404)

    def test_signup_creates_user_and_profile_and_logs_in(self):
        r = self.client.post(reverse('signup'), {
            'username': 'khach1', 'full_name': 'Nguyen A', 'email': 'a@a.com',
            'phone': '0912345678', 'address': 'HN',
            'password1': 'Mk-rat-manh-123', 'password2': 'Mk-rat-manh-123'})
        self.assertRedirects(r, reverse('home'))
        self.assertEqual(Profile.objects.get(user__username='khach1').phone, '0912345678')
        self.assertEqual(self.client.get(reverse('account')).status_code, 200)

    def test_signup_rejects_bad_phone(self):
        r = self.client.post(reverse('signup'), {
            'username': 'k2', 'full_name': 'A', 'email': 'a@a.com', 'phone': '123', 'address': 'HN',
            'password1': 'Mk-rat-manh-123', 'password2': 'Mk-rat-manh-123'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='k2').exists())

    def test_account_requires_login_then_logout_is_post(self):
        r = self.client.get(reverse('account'))
        self.assertRedirects(r, '/dang-nhap/?next=/tai-khoan/')
        User.objects.create_user('u', password='Mk-rat-manh-123')
        self.client.login(username='u', password='Mk-rat-manh-123')
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 302)
