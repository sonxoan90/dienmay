# shop/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class BootstrapMixin:
    """Gắn class 'form-control' của Bootstrap cho mọi ô nhập."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class LoginForm(BootstrapMixin, AuthenticationForm):
    pass


class SignUpForm(BootstrapMixin, UserCreationForm):
    # Thêm 4 ô ngoài username + 2 ô mật khẩu có sẵn của UserCreationForm
    full_name = forms.CharField(label='Họ tên', max_length=100)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='Số điện thoại', max_length=15)
    address = forms.CharField(label='Địa chỉ', max_length=255)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'full_name', 'email', 'phone', 'address')

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not (phone.isdigit() and len(phone) == 10 and phone.startswith('0')):
            raise forms.ValidationError('Số điện thoại gồm 10 chữ số, bắt đầu bằng 0.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)          # tạo User, mật khẩu đã được băm
        user.first_name = self.cleaned_data['full_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Profile.objects.create(                  # tạo luôn hồ sơ 1-1
                user=user,
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address'],
            )
        return user


class UserInfoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'email')
        labels = {'first_name': 'Họ tên', 'email': 'Email'}


class ProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone', 'address')