# shop/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, SignUpForm, UserInfoForm
from .models import Brand, Category, Product, Profile


def active_products():
    """Sản phẩm đang bán + cột tính sẵn final_price = giá KM nếu có, không thì giá gốc."""
    return (Product.objects.filter(is_active=True)
            .select_related('category', 'brand')
            .annotate(final_price=Coalesce('sale_price', 'price')))


def home(request):
    featured = active_products()[:8]                      # 8 sản phẩm mới nhất
    sections = []
    for c in Category.objects.order_by('name'):
        items = active_products().filter(category=c)[:4]  # 4 sản phẩm mỗi danh mục
        if items:
            sections.append((c, items))
    return render(request, 'shop/home.html', {'featured': featured, 'sections': sections})


SORTS = {
    'new': '-created_at',
    'price_asc': 'final_price',
    'price_desc': '-final_price',
}


def product_list(request):
    qs = active_products()
    g = request.GET                                # các tham số sau dấu ? trên URL

    q = g.get('q', '').strip()                     # tìm kiếm
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__name__icontains=q))
    if g.get('category'):
        qs = qs.filter(category__slug=g['category'])
    if g.get('brand'):
        qs = qs.filter(brand__slug=g['brand'])
    if g.get('min_price', '').isdigit():
        qs = qs.filter(final_price__gte=int(g['min_price']))
    if g.get('max_price', '').isdigit():
        qs = qs.filter(final_price__lte=int(g['max_price']))

    sort = g.get('sort', 'new')
    qs = qs.order_by(SORTS.get(sort, '-created_at'))

    page = Paginator(qs, 12).get_page(g.get('page'))   # 12 sản phẩm / trang

    params = g.copy()                              # giữ bộ lọc khi bấm sang trang khác
    params.pop('page', None)

    return render(request, 'shop/product_list.html', {
        'page': page,
        'q': q,
        'sort': sort,
        'categories': Category.objects.order_by('name'),
        'brands': Brand.objects.order_by('name'),
        'querystring': params.urlencode(),
    })


def product_detail(request, slug):
    product = get_object_or_404(active_products(), slug=slug)   # không có → trang 404
    related = active_products().filter(category=product.category).exclude(pk=product.pk)[:4]
    return render(request, 'shop/product_detail.html', {'product': product, 'related': related})


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':                   # người dùng bấm "Đăng ký"
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)                   # đăng nhập luôn sau khi đăng ký
            messages.success(request, 'Đăng ký thành công. Chào mừng bạn!')
            return redirect('home')
    else:                                          # lần đầu mở trang
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required                                    # chưa đăng nhập → chuyển về trang đăng nhập
def account(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)   # superuser chưa có hồ sơ
    if request.method == 'POST':
        user_form = UserInfoForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Đã lưu thông tin.')
            return redirect('account')
    else:
        user_form = UserInfoForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render(request, 'shop/account.html', {'user_form': user_form, 'profile_form': profile_form})