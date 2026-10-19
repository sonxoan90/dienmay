# shop/context_processors.py
from .models import Category


def menu(request):
    """Biến dùng chung cho MỌI template: danh mục trên menu, số món trong giỏ."""
    return {
        'menu_categories': Category.objects.order_by('name'),
        'cart_count': 0,  # tuần 4 thay bằng số lượng thật trong giỏ
    }