# NOTES – Web bán hàng điện máy

## Cách chạy dự án
1. cd dienmay
2. venv\Scripts\activate.bat
3. python manage.py runserver
4. Mở http://127.0.0.1:8000

## Cấu trúc thư mục
- manage.py: chạy các lệnh quản trị
- config/settings.py: cấu hình chung
- config/urls.py: định tuyến URL gốc

## Nhật ký theo tuần
### Tuần 0 – Môi trường
- Đã làm: cài Python, venv, Django, đẩy lên GitHub
- Hiểu được: venv tách thư viện của từng dự án
- Còn chưa rõ: ...

### Tuần 1 – Models, seed
- Đã làm: thiết kế 10 bảng (app shop + orders), migrate, viết lệnh `python manage.py seed` (5 danh mục, 6 nhãn hàng, 30 sản phẩm)
- Hiểu được: lệnh tự viết phải nằm trong `<app>/management/commands/` và có `__init__.py` thì Django mới nhận
- Còn chưa rõ: ...

## Vai trò các bảng
| App | Bảng | Vai trò (tự viết) | Quan hệ chính |
| --- | --- | --- | --- |
| shop | Category | Nhóm hàng như Tivi, Tủ lạnh; dùng để lọc và hiển thị menu | 1 danh mục – n sản phẩm |
| shop | Brand | Hãng sản xuất như Samsung, LG; dùng để lọc theo hãng | 1 nhãn hàng – n sản phẩm |
| shop | Product | Hàng đang bán: giá, giá khuyến mãi, tồn kho, thông số | thuộc 1 danh mục, 1 nhãn hàng (PROTECT, còn sản phẩm thì không xóa được) |
| shop | Profile | Thông tin thêm của người dùng (SĐT, địa chỉ) mà User có sẵn không có | 1–1 với User |
| orders | Cart | Giỏ hàng lưu trong DB của khách đã đăng nhập | 1–1 với User (chỉ khách đăng nhập) |
| orders | CartItem | Một sản phẩm và số lượng trong giỏ; mỗi sản phẩm chỉ một dòng trong một giỏ | n dòng trong 1 giỏ, mỗi dòng trỏ tới 1 sản phẩm |
| orders | Order | Đơn hàng: người nhận, tổng tiền, cách thanh toán, trạng thái đơn và trạng thái thanh toán | user có thể trống (khách vãng lai) |
| orders | OrderItem | Chi tiết đơn, chụp lại tên và giá tại lúc mua để sau này đổi giá không làm sai đơn cũ | n dòng trong 1 đơn, lưu giá và tên lúc mua |
| orders | OrderStatusHistory | Nhật ký đổi trạng thái đơn: từ đâu sang đâu, ai đổi, lúc nào, ghi chú | mỗi lần đổi trạng thái 1 dòng |
| orders | Payment | Mỗi lần thanh toán qua VNPay: mã giao dịch, số tiền, kết quả, dữ liệu gốc để đối soát | 0..n lần thanh toán cho 1 đơn |

## 3 truy vấn ORM và SQL tương đương
Đã chạy cả hai bên trên db.sqlite3 (30 sản phẩm), kết quả giống nhau (chỉ khác thứ tự dòng). Xem SQL Django sinh ra bằng `print(qs.query)`.

**1. Sản phẩm thuộc danh mục Tivi** (6 dòng)
```python
Product.objects.filter(category__slug='tivi')
```
```sql
SELECT p.name, p.price FROM shop_product p
JOIN shop_category c ON c.id = p.category_id WHERE c.slug = 'tivi';
```
Khác biệt: ORM lấy toàn bộ cột và thêm `ORDER BY created_at DESC` theo `Meta.ordering`.

**2. Đếm số sản phẩm theo nhãn hàng** (LG 6, Panasonic 2, Samsung 6, Sharp 9, Sony 6, Toshiba 1)
```python
Brand.objects.annotate(so_sp=Count('products')).values('name', 'so_sp')
```
```sql
SELECT b.name, COUNT(p.id) AS so_sp FROM shop_brand b
LEFT JOIN shop_product p ON p.brand_id = b.id GROUP BY b.id, b.name;
```
Dùng LEFT JOIN nên nhãn chưa có sản phẩm vẫn hiện với số 0.

**3. Giá trung bình và tổng tồn kho theo danh mục** (ví dụ Tivi: TB 15.000.000, tồn 115)
```python
Category.objects.annotate(gia_tb=Avg('products__price'), ton=Sum('products__stock')).values('name', 'gia_tb', 'ton')
```
```sql
SELECT c.name, AVG(p.price), SUM(p.stock) FROM shop_category c
LEFT JOIN shop_product p ON p.category_id = c.id GROUP BY c.id, c.name;
```
Khác biệt: ORM ép kiểu AVG sang Decimal, SQLite trả float.

