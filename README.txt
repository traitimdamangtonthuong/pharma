PHARMA MANAGER - HỆ THỐNG QUẢN LÝ NHÀ THUỐC
===========================================

I. CÁC FILE TRONG GÓI CẬP NHẬT
- app.py: 
  + Giữ nguyên các route tìm kiếm (/search), tồn kho (/inventory), hạn dùng (/expiry); bổ sung DATEDIFF hiển thị số ngày còn lại của từng lô.
  + Tích hợp route Quản lý Thuốc và Lô thuốc (/medicines): xử lý thêm, sửa, xóa (CRUD) Thuốc & Lô thuốc, áp dụng SQL Transaction tự động đồng bộ tồn kho.
- templates/base.html: Bố cục sidebar và thanh điều hướng chung.
- templates/medicines.html: Giao diện Quản lý Thuốc và Nhập lô thuốc (Form 1).
- templates/search.html: Giao diện tìm kiếm và bộ lọc hạn sử dụng.
- templates/inventory.html: Giao diện báo cáo tồn kho và thẻ thống kê.
- templates/expiry.html: Giao diện cảnh báo hạn sử dụng.
- static/css/style.css: Bộ nhận diện giao diện chung, responsive và tinh chỉnh UI/UX cho các ô nhập liệu (.form-input, .form-panel).
- TruyVan_QuanLyThuoc_LoThuoc.sql: Kịch bản SQL chuẩn hóa độ dài cột (VARCHAR), bảng mã tiếng Việt (utf8mb4), nạp dữ liệu mẫu (Seeding) và mô phỏng truy vấn CRUD / Transaction của Form 1.
- TruyVan_TimKiem_BaoCao.sql: Các câu truy vấn tìm kiếm, báo cáo tồn kho và cảnh báo hạn sử dụng.

II. CÁCH CÀI ĐẶT VÀ CẬP NHẬT MÃ NGUỒN
1. Dừng server Flask đang chạy bằng tổ hợp phím Ctrl + C.
2. Sao lưu thư mục templates, file static/css/style.css và app.py hiện tại (nếu cần).
3. Giải nén / chép gói này vào thư mục gốc của project (ví dụ: F:\CSDL\BTL hoặc D:\BTL_CSDL\QuanLyNhaThuoc) và cho phép ghi đè các file trùng tên.
4. KHÔNG xóa hoặc thay thế db.py, .env, .venv hay cấu hình kết nối MySQL hiện có.

III. CẬP NHẬT CƠ SỞ DỮ LIỆU CHO PHẦN QUẢN LÝ THUỐC & LÔ THUỐC (QUAN TRỌNG)
Để tránh lỗi tên Nhà cung cấp/Nhân viên/Danh mục bị cắt chữ (chỉ hiện chữ "C") hoặc lỗi tiếng Việt biến thành dấu "?" khi copy-paste vào cửa sổ dòng lệnh Windows, vui lòng nạp file SQL bằng lệnh `source` như sau:

1. Mở ứng dụng "MySQL 8.0 Command Line Client" và nhập mật khẩu root.
2. Chạy lệnh nạp trực tiếp file kịch bản (lưu ý đổi dấu "\" trong đường dẫn thành dấu "/"):
   source F:/CSDL/BTL/TruyVan_QuanLyThuoc_LoThuoc.sql
   *(Thay "F:/CSDL/BTL/" bằng đường dẫn thư mục project thực tế trên máy của bạn)*
3. Khi màn hình báo "Query OK" nghĩa là các bảng (DANH_MUC, NHA_CUNG_CAP, NHAN_VIEN, THUOC, LO_THUOC) đã được nới rộng kích thước VARCHAR(255), chuyển sang utf8mb4 và nạp sẵn dữ liệu mẫu thành công.

IV. KHỞI CHẠY VÀ KIỂM TRA HỆ THỐNG
1. Mở Terminal tại thư mục project và kiểm tra cú pháp / chạy server:
   python -m compileall -q app.py db.py
   python app.py   (hoặc: py app.py)
2. Truy cập và kiểm tra các trang chức năng trên trình duyệt (nhấn Ctrl + F5 để làm mới CSS):
   - Quản lý Thuốc & Lô thuốc (Form 1): http://127.0.0.1:5000/medicines
   - Tìm kiếm & Lọc thuốc:             http://127.0.0.1:5000/search
   - Báo cáo tồn kho:                  http://127.0.0.1:5000/inventory
   - Cảnh báo hạn sử dụng:             http://127.0.0.1:5000/expiry

V. LƯU Ý VỀ DỮ LIỆU & NGHIỆP VỤ
- THUOC.SoLuongTon là tổng tồn kho theo từng loại thuốc, không phải tồn riêng của từng lô.
- LO_THUOC.SoLuongThuocNhap là số lượng nhập ban đầu của lô, không phải số lượng còn lại của lô.
- Cơ chế Transaction tại trang /medicines:
  + Khi Nhập lô thuốc mới: Hệ thống tự động INSERT vào bảng LO_THUOC đồng thời UPDATE cộng dồn số lượng vừa nhập vào cột SoLuongTon của bảng THUOC.
  + Khi Xóa lô thuốc: Hệ thống tự động trừ số lượng của lô đó khỏi THUOC.SoLuongTon trước khi DELETE bản ghi khỏi bảng LO_THUOC.
- GiaTriTonKho trong báo cáo đang tính theo (DonGiaBan * SoLuongTon), không phải giá trị theo giá nhập.

Gói này không chứa file .env hoặc mật khẩu đăng nhập MySQL cá nhân.