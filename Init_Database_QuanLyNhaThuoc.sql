
-- =====================================================================================
-- 3. NẠP DỮ LIỆU BAN ĐẦU (SEED DATA TỪ DỰ ÁN CỦA NHÓM)
-- =====================================================================================

-- 3.1. Dữ liệu danh mục
INSERT INTO DANH_MUC (MaDanhMuc, TenDanhMuc) VALUES 
('DM01', 'Thuốc giảm đau - hạ sốt'),
('DM02', 'Thuốc kháng sinh'),
('DM03', 'Thuốc ho - hô hấp'),
('DM04', 'Thực phẩm chức năng & Vitamin'),
('DM05', 'Thuốc tiêu hóa')
ON DUPLICATE KEY UPDATE TenDanhMuc = VALUES(TenDanhMuc);

-- 3.2. Dữ liệu nhà cung cấp
INSERT INTO NHA_CUNG_CAP (MaNCC, TenNCC, DiaChi, SDT, Email) VALUES 
('NCC01', 'Công ty Cổ phần Dược Hậu Giang (DHG)', 'Cần Thơ', '02923891433', 'dhg@dhgpharma.com.vn'),
('NCC02', 'Công ty CP Traphaco', 'Hà Nội', '02436815097', 'info@traphaco.com.vn'),
('NCC03', 'Công ty Dược phẩm Sanofi Việt Nam', 'TP. Hồ Chí Minh', '02838298526', 'contact@sanofi.com')
ON DUPLICATE KEY UPDATE TenNCC = VALUES(TenNCC);

-- 3.3. Dữ liệu nhân viên nhà thuốc
INSERT INTO NHAN_VIEN (MaNV, TenNV, SDT, Email, VaiTro, Luong) VALUES 
('NV01', 'Nguyễn Văn An', '0901000001', 'annv@pharma.vn', 'Dược sĩ', 12000000.00),
('NV02', 'Trần Thị Bình', '0901000002', 'binhtt@pharma.vn', 'Bán hàng', 8500000.00),
('NV03', 'Lê Hoàng Nam', '0901000003', 'namlh@pharma.vn', 'Quản lý kho', 10000000.00)
ON DUPLICATE KEY UPDATE TenNV = VALUES(TenNV);

-- 3.4. Dữ liệu khách hàng mẫu
INSERT INTO KHACH_HANG (MaKH, TenKH, SDT) VALUES
('KH01', 'Khách vãng lai', '0900000000'),
('KH02', 'Nguyễn Văn Hoàng', '0988123456'),
('KH03', 'Trần Thị Mai', '0912345678')
ON DUPLICATE KEY UPDATE TenKH = VALUES(TenKH);

-- 3.5. Dữ liệu thuốc mẫu trong kho
INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc) VALUES 
('T001', 'Hapacol 650', 'Paracetamol 650mg', 'Giảm đau, hạ sốt', 25000.00, 100, 'DM01'),
('T002', 'Augmentin 625mg', 'Amoxicillin 500mg, Acid Clavulanic 125mg', 'Điều trị nhiễm khuẩn', 145000.00, 50, 'DM02'),
('T003', 'Siro ho Prospan', 'Cao khô lá thường xuân', 'Trị ho, viêm đường hô hấp', 78000.00, 30, 'DM03')
ON DUPLICATE KEY UPDATE TenThuoc = VALUES(TenThuoc);

-- 3.6. Dữ liệu lô thuốc nhập kho (kèm hạn sử dụng)
INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV) VALUES 
('T001', 'LO-2025-A1', 100, '2025-06-01', '2027-06-01', 18000.00, '2025-06-15', 'NCC01', 'NV03'),
('T002', 'LO-2025-B1', 50, '2025-05-10', '2026-11-20', 115000.00, '2025-05-20', 'NCC03', 'NV03'),
('T003', 'LO-2024-C1', 30, '2024-10-01', '2026-10-01', 58000.00, '2024-10-15', 'NCC02', 'NV01')
ON DUPLICATE KEY UPDATE SoLo = VALUES(SoLo);