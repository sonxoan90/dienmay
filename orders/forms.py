from django import forms

from shop.forms import BootstrapMixin

from .models import Order


class CheckoutForm(BootstrapMixin, forms.Form):
    full_name = forms.CharField(label='Họ tên người nhận', max_length=100)
    phone = forms.CharField(label='Số điện thoại', max_length=15)
    address = forms.CharField(label='Địa chỉ giao hàng', max_length=200)
    note = forms.CharField(label='Ghi chú', max_length=50, required=False)
    # Tuần 4 chỉ có COD; VNPay thêm ở tuần 5
    payment_method = forms.ChoiceField(
        label='Phương thức thanh toán',
        choices=[(Order.PaymentMethod.COD, 'Thanh toán khi nhận hàng (COD)')],
        initial=Order.PaymentMethod.COD, widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].widget.attrs['class'] = 'form-check-input'

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not (phone.isdigit() and len(phone) == 10 and phone.startswith('0')):
            raise forms.ValidationError('Số điện thoại gồm 10 chữ số, bắt đầu bằng 0.')
        return phone


class LookupForm(BootstrapMixin, forms.Form):
    code = forms.CharField(label='Mã đơn hàng', max_length=20)
    phone = forms.CharField(label='Số điện thoại đặt hàng', max_length=15)
