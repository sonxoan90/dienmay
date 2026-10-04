# shop/management/commands/seed.py
import random

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shop.models import Brand, Category, Product

CATEGORIES = ['Tivi', 'Tủ lạnh', 'Máy giặt', 'Điều hòa', 'Gia dụng']
BRANDS = ['Samsung', 'LG', 'Sony', 'Panasonic', 'Toshiba', 'Sharp']
PRICE_RANGE = {  # đơn vị: triệu đồng
    'Tivi': (5, 40), 'Tủ lạnh': (6, 30), 'Máy giặt': (5, 20),
    'Điều hòa': (6, 25), 'Gia dụng': (1, 8),
}


def vn_slug(text):
    # slugify bỏ mất chữ Đ, nên đổi sang D trước
    return slugify(text.replace('Đ', 'D').replace('đ', 'd'))


class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu: 5 danh mục, 6 nhãn hàng, 30 sản phẩm'

    def handle(self, *args, **options):
        random.seed(42)  # cố định để lần nào chạy cũng ra cùng dữ liệu
        cats = [Category.objects.get_or_create(slug=vn_slug(n), defaults={'name': n})[0] for n in CATEGORIES]
        brands = [Brand.objects.get_or_create(slug=vn_slug(n), defaults={'name': n})[0] for n in BRANDS]
        created = 0
        for i in range(1, 31):
            cat = cats[(i - 1) % len(cats)]  # chia đều 6 sản phẩm mỗi danh mục
            brand = random.choice(brands)
            name = f'{cat.name} {brand.name} mẫu {i:02d}'
            low, high = PRICE_RANGE[cat.name]
            price = random.randint(low, high) * 1_000_000
            _, is_new = Product.objects.get_or_create(
                slug=vn_slug(name),
                defaults={
                    'name': name, 'category': cat, 'brand': brand, 'price': price,
                    'sale_price': price * 9 // 10 if i % 3 == 0 else None,
                    'stock': random.randint(0, 50), 'specs': 'Thông số mẫu',
                },
            )
            created += is_new
        self.stdout.write(self.style.SUCCESS(f'Đã tạo {created} sản phẩm mới'))