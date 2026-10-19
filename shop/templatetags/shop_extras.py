# shop/templatetags/shop_extras.py
from django import template

register = template.Library()


@register.filter
def vnd(value):
    """15990000 -> '15.990.000 đ'"""
    if value in (None, ''):
        return ''
    return f'{int(value):,}'.replace(',', '.') + ' đ'