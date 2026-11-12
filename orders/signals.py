from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from . import cart


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    # request.session đã đổi khóa nhưng dữ liệu giỏ vẫn còn → gộp vào DB
    cart.merge_session_into_db(request, user)
