USE quan_ly_nha_thuoc;
SET NAMES utf8mb4;

ALTER TABLE DANH_MUC MODIFY TenDanhMuc VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
INSERT INTO DANH_MUC (MaDanhMuc, TenDanhMuc) VALUES 
('DM01', 'Thuốc giảm đau - hạ sốt'),
('DM02', 'Thuốc kháng sinh'),
('DM03', 'Thuốc ho - hô hấp'),
('DM04', 'Thực phẩm chức năng & Vitamin'),
('DM05', 'Thuốc tiêu hóa')
ON DUPLICATE KEY UPDATE TenDanhMuc = VALUES(TenDanhMuc);

-- 2. Sửa và cập nhật Nhà cung cấp (mở rộng cả TenNCC, Diachi, Email)
ALTER TABLE NHA_CUNG_CAP 
    MODIFY TenNCC VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    MODIFY Diachi VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    MODIFY SDT VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    MODIFY Email VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT INTO NHA_CUNG_CAP (MaNCC, TenNCC, Diachi, SDT, Email) VALUES 
('NCC01', 'Công ty Cổ phần Dược Hậu Giang (DHG)', 'Cần Thơ', '02923891433', 'dhg@dhgpharma.com.vn'),
('NCC02', 'Công ty CP Traphaco', 'Hà Nội', '02436815097', 'info@traphaco.com.vn'),
('NCC03', 'Công ty Dược phẩm Sanofi Việt Nam', 'TP. Hồ Chí Minh', '02838298526', 'contact@sanofi.com')
ON DUPLICATE KEY UPDATE 
    TenNCC = VALUES(TenNCC),
    Diachi = VALUES(Diachi),
    SDT = VALUES(SDT),
    Email = VALUES(Email);

-- 3. Sửa và cập nhật Nhân viên (mở rộng cả TenNV và VaiTro)
ALTER TABLE NHAN_VIEN 
    MODIFY TenNV VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    MODIFY VaiTro VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT INTO NHAN_VIEN (MaNV, TenNV, SDT, Email, VaiTro, Luong) VALUES 
('NV01', 'Nguyễn Văn An', '0901000001', 'annv@pharma.vn', 'Dược sĩ', 12000000.00),
('NV02', 'Trần Thị Bình', '0901000002', 'binhtt@pharma.vn', 'Bán hàng', 8500000.00),
('NV03', 'Lê Hoàng Nam', '0901000003', 'namlh@pharma.vn', 'Quản lý kho', 10000000.00)
ON DUPLICATE KEY UPDATE 
    TenNV = VALUES(TenNV),
    VaiTro = VALUES(VaiTro);

ALTER TABLE THUOC 
    MODIFY TenThuoc VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    MODIFY ThanhPhan VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    MODIFY ChiDinh VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc) VALUES 
('T001', 'Hapacol 650', 'Paracetamol 650mg', 'Giảm đau, hạ sốt', 25000.00, 100, 'DM01'),
('T002', 'Augmentin 625mg', 'Amoxicillin 500mg, Acid Clavulanic 125mg', 'Điều trị nhiễm khuẩn', 145000.00, 50, 'DM02'),
('T003', 'Siro ho Prospan', 'Cao khô lá thường xuân', 'Trị ho, viêm đường hô hấp', 78000.00, 30, 'DM03')
ON DUPLICATE KEY UPDATE 
    TenThuoc = VALUES(TenThuoc), 
    ThanhPhan = VALUES(ThanhPhan), 
    ChiDinh = VALUES(ChiDinh);

ALTER TABLE LO_THUOC 
    MODIFY SoLo VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV) VALUES 
('T001', 'LO-2025-A1', 100, '2025-06-01', '2027-06-01', 18000.00, '2025-06-15', 'NCC01', 'NV03'),
('T002', 'LO-2025-B1', 50, '2025-05-10', '2026-11-20', 115000.00, '2025-05-20', 'NCC03', 'NV03'),
('T003', 'LO-2024-C1', 30, '2024-10-01', '2026-10-01', 58000.00, '2024-10-15', 'NCC02', 'NV01')
ON DUPLICATE KEY UPDATE 
    SoLo = VALUES(SoLo);

-- =======================================================================================
-- CÁC LỆNH SQL MÔ PHỎNG HÀNH ĐỘNG CỦA NÚT BẤM TRÊN WEB (DÀNH CHO CHẤM ĐIỂM)
-- =======================================================================================

-- --------------------------------------------------------
-- I. CHỨC NĂNG QUẢN LÝ THUỐC (FORM THÔNG TIN THUỐC)
-- --------------------------------------------------------

-- 1. Nút "Lưu Thuốc Mới" (Thêm mới một loại thuốc vào danh mục)
INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc) 
VALUES ('T099', 'Thuốc Test Demo', 'Paracetamol 500mg', 'Giảm đau nhẹ', 15000.00, 0, 'DM01');

-- 2. Nút "Cập nhật Thuốc" (Sửa thông tin khi người dùng thay đổi giá hoặc thành phần)
UPDATE THUOC 
SET TenThuoc = 'Thuốc Test Demo (Đã sửa)', 
    DonGiaBan = 18000.00, 
    ThanhPhan = 'Paracetamol 500mg, Cafein' 
WHERE MaThuoc = 'T099';

-- 3. Nút "Xóa Thuốc" (Xóa một loại thuốc ra khỏi hệ thống)
DELETE FROM THUOC 
WHERE MaThuoc = 'T099';

-- --------------------------------------------------------
-- II. CHỨC NĂNG QUẢN LÝ LÔ THUỐC VÀ NHẬP KHO (TRANSACTION)
-- --------------------------------------------------------

-- 1. Nút "Nhập Lô Thuốc Mới" (Yêu cầu dùng TRANSACTION để đảm bảo toàn vẹn dữ liệu)
-- Hành động: Thêm lô mới -> Tự động cộng dồn số lượng vào kho tổng của Thuốc đó
START TRANSACTION;
    -- B1: Thêm dòng dữ liệu vào bảng LO_THUOC
    INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV) 
    VALUES ('T001', 'LO-TEST-2026', 200, '2026-11-01', '2028-11-01', 12000.00, '2026-11-07', 'NCC01', 'NV01');
    
    -- B2: Cộng dồn số lượng nhập (200) vào cột SoLuongTon của bảng THUOC
    UPDATE THUOC 
    SET SoLuongTon = SoLuongTon + 200 
    WHERE MaThuoc = 'T001';
COMMIT;
-- (Nếu có lỗi xảy ra ở B1 hoặc B2, gọi lệnh ROLLBACK để hủy thao tác)

-- 2. Nút "Sửa thông tin Lô Thuốc" (Chỉ sửa ngày tháng hoặc giá nhập, không sửa số lượng)
UPDATE LO_THUOC 
SET NSX = '2026-11-05', 
    DonGiaNhap = 11500.00 
WHERE MaThuoc = 'T001' AND SoLo = 'LO-TEST-2026';

-- 3. Nút "Xóa Lô Thuốc" (Yêu cầu dùng TRANSACTION)
-- Hành động: Trừ đi số lượng của lô sắp xóa khỏi kho tổng -> Sau đó mới xóa lô
START TRANSACTION;
    -- B1: Trừ số lượng tồn trong kho tổng tương ứng với số lượng của lô cần xóa
    UPDATE THUOC 
    SET SoLuongTon = SoLuongTon - (SELECT SoLuongThuocNhap FROM LO_THUOC WHERE MaThuoc = 'T001' AND SoLo = 'LO-TEST-2026')
    WHERE MaThuoc = 'T001';
    
    -- B2: Xóa lô thuốc khỏi bảng LO_THUOC
    DELETE FROM LO_THUOC 
    WHERE MaThuoc = 'T001' AND SoLo = 'LO-TEST-2026';
COMMIT;

-- --------------------------------------------------------
-- III. CHỨC NĂNG QUẢN LÝ DANH MỤC THUỐC (FORM 3)
-- --------------------------------------------------------

-- 1. Hiển thị danh sách Danh mục kèm số lượng thuốc thuộc mỗi danh mục
SELECT dm.MaDanhMuc, dm.TenDanhMuc, COUNT(t.MaThuoc) AS SoThuoc
FROM DANH_MUC dm
LEFT JOIN THUOC t ON t.MaDanhMuc = dm.MaDanhMuc
GROUP BY dm.MaDanhMuc, dm.TenDanhMuc
ORDER BY dm.MaDanhMuc;

-- 2. Thêm mới Danh mục hợp lệ
INSERT INTO DANH_MUC (MaDanhMuc, TenDanhMuc) VALUES ('DM99', 'Thuốc tim mạch');

-- 3. Kiểm thử trùng khóa chính (DM01 đã là 'Thuốc giảm đau - hạ sốt', cố tình thêm mới DM01 = 'Thuốc đau đầu')
-- -> MySQL sẽ báo lỗi Error 1062 (23000): Duplicate entry 'DM01' for key 'PRIMARY' và KHÔNG ghi đè tên cũ:
-- INSERT INTO DANH_MUC (MaDanhMuc, TenDanhMuc) VALUES ('DM01', 'Thuốc đau đầu');

-- 4. Cập nhật tên Danh mục (Khi bấm nút Sửa)
UPDATE DANH_MUC SET TenDanhMuc = 'Thuốc tim mạch & huyết áp' WHERE MaDanhMuc = 'DM99';

-- 5. Xóa Danh mục (chỉ cho phép xóa khi không còn thuốc nào thuộc danh mục đó)
DELETE FROM DANH_MUC WHERE MaDanhMuc = 'DM99';

-- --------------------------------------------------------
-- IV. CHỨC NĂNG QUẢN LÝ NHÀ CUNG CẤP (FORM 4)
-- --------------------------------------------------------

-- 1. Hiển thị danh sách Nhà cung cấp đầy đủ thông tin kèm số lô đã nhập
SELECT ncc.MaNCC, ncc.TenNCC, ncc.Diachi, ncc.SDT, ncc.Email, COUNT(lt.SoLo) AS SoLo
FROM NHA_CUNG_CAP ncc
LEFT JOIN LO_THUOC lt ON lt.MaNCC = ncc.MaNCC
GROUP BY ncc.MaNCC, ncc.TenNCC, ncc.Diachi, ncc.SDT, ncc.Email
ORDER BY ncc.MaNCC;

-- 2. Thêm mới Nhà cung cấp đầy đủ thông tin (Mã, Tên, Địa chỉ, SĐT, Email)
INSERT INTO NHA_CUNG_CAP (MaNCC, TenNCC, Diachi, SDT, Email)
VALUES ('NCC99', 'Công ty CP Dược phẩm OPC', 'TP. Hồ Chí Minh', '02838754611', 'contact@opcpharma.com');

-- 3. Kiểm thử trùng khóa chính (NCC01 đã tồn tại, cố tình thêm mới NCC01 với tên công ty khác)
-- -> MySQL sẽ báo lỗi Error 1062 (23000): Duplicate entry 'NCC01' for key 'PRIMARY' và KHÔNG ghi đè:
-- INSERT INTO NHA_CUNG_CAP (MaNCC, TenNCC, Diachi, SDT, Email) VALUES ('NCC01', 'Công ty Dược Test', 'Đà Nẵng', '0909123456', 'test@ncc.vn');

-- 4. Cập nhật Nhà cung cấp
UPDATE NHA_CUNG_CAP
SET TenNCC = 'Công ty Cổ phần Dược phẩm OPC', Diachi = 'Quận 6, TP. Hồ Chí Minh', SDT = '02838754611', Email = 'info@opcpharma.com'
WHERE MaNCC = 'NCC99';

-- 5. Xóa Nhà cung cấp (chỉ xóa khi chưa có lô thuốc nào tham chiếu)
DELETE FROM NHA_CUNG_CAP WHERE MaNCC = 'NCC99';