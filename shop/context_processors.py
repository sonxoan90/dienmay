# shop/context_processors.py
from orders import cart

from .models import Category


def menu(request):
    """Biến dùng chung cho MỌI template: danh mục trên menu, số món trong giỏ."""
    return {
        'menu_categories': Category.objects.order_by('name'),
        'cart_count': cart.count(request),
    }