# shop/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.utils.html import format_html

from .models import Brand, Category, Product, Profile

admin.site.site_header = 'Quản trị Điện máy'
admin.site.site_title = 'Quản trị Điện máy'
admin.site.index_title = 'Bảng điều khiển'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'so_san_pham')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}  # gõ tên, slug tự sinh

    def get_queryset(self, request):
        # đếm sản phẩm bằng 1 câu SQL (GROUP BY) thay vì đếm từng dòng
        return super().get_queryset(request).annotate(_so_sp=Count('products'))

    @admin.display(description='Số sản phẩm', ordering='_so_sp')
    def so_san_pham(self, obj):
        return obj._so_sp


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('anh', 'name', 'category', 'brand', 'price', 'sale_price', 'stock', 'is_active')
    list_display_links = ('name',)
    list_editable = ('price', 'stock', 'is_active')  # sửa nhanh ngay trên danh sách
    list_filter = ('category', 'brand', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    list_per_page = 20

    @admin.display(description='Ảnh')
    def anh(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px">', obj.image.url)
        return '—'


# ---- Quản lý user: hiện kèm hồ sơ, thêm action khóa/mở ----
User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Hồ sơ'


admin.site.unregister(User)  # bỏ trang User mặc định để thay bằng bản bên dưới


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined')
    actions = ('khoa_tai_khoan', 'mo_tai_khoan')

    @admin.action(description='Khóa tài khoản đã chọn')
    def khoa_tai_khoan(self, request, queryset):
        n = queryset.exclude(pk=request.user.pk).update(is_active=False)  # không tự khóa mình
        self.message_user(request, f'Đã khóa {n} tài khoản.')

    @admin.action(description='Mở khóa tài khoản đã chọn')
    def mo_tai_khoan(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f'Đã mở khóa {n} tài khoản.')