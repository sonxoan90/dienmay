# orders/admin.py
from django.contrib import admin, messages

from .models import Order, OrderItem, OrderStatusHistory, Payment
from .services import change_status


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrderItemInline(ReadOnlyInline):
    model = OrderItem
    fields = readonly_fields = ('product', 'product_name', 'quantity', 'unit_price')


class PaymentInline(ReadOnlyInline):
    model = Payment
    fields = readonly_fields = ('vnp_txn_ref', 'amount', 'status', 'response_code', 'created_at', 'paid_at')


class HistoryInline(ReadOnlyInline):
    model = OrderStatusHistory
    fields = readonly_fields = ('from_status', 'to_status', 'changed_by', 'changed_at', 'note')


def _bulk_change(modeladmin, request, queryset, new_status):
    """Đổi trạng thái nhiều đơn; đơn nào sai luồng thì báo lỗi riêng."""
    ok = 0
    for order in queryset:
        try:
            change_status(order, new_status, user=request.user)
            ok += 1
        except ValueError as e:
            modeladmin.message_user(request, str(e), messages.ERROR)
    if ok:
        modeladmin.message_user(request, f'Đã cập nhật {ok} đơn.', messages.SUCCESS)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('code', 'full_name', 'phone', 'total_amount', 'payment_method',
                    'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('code', 'phone', 'full_name')
    date_hierarchy = 'created_at'
    # trạng thái chỉ đổi qua action; vẫn cho sửa họ tên, số điện thoại, địa chỉ giao
    readonly_fields = ('code', 'user', 'total_amount', 'payment_method', 'status', 'payment_status', 'created_at')
    inlines = (OrderItemInline, PaymentInline, HistoryInline)
    actions = ('xac_nhan', 'giao_hang', 'hoan_tat', 'huy_don')

    def has_add_permission(self, request):
        return False  # đơn chỉ được tạo từ website

    def has_delete_permission(self, request, obj=None):
        return False  # không xóa đơn, chỉ hủy

    @admin.action(description='Xác nhận đơn', permissions=['change'])
    def xac_nhan(self, request, queryset):
        _bulk_change(self, request, queryset, Order.Status.CONFIRMED)

    @admin.action(description='Chuyển sang Đang giao', permissions=['change'])
    def giao_hang(self, request, queryset):
        _bulk_change(self, request, queryset, Order.Status.SHIPPING)

    @admin.action(description='Hoàn tất (Đã giao)', permissions=['change'])
    def hoan_tat(self, request, queryset):
        _bulk_change(self, request, queryset, Order.Status.DELIVERED)

    @admin.action(description='Hủy đơn', permissions=['change'])
    def huy_don(self, request, queryset):
        _bulk_change(self, request, queryset, Order.Status.CANCELLED)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Chỉ xem: dữ liệu thanh toán là bằng chứng đối soát, không cho sửa."""
    list_display = ('vnp_txn_ref', 'order', 'amount', 'status', 'response_code', 'created_at')
    list_filter = ('status',)
    search_fields = ('vnp_txn_ref', 'order__code')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False