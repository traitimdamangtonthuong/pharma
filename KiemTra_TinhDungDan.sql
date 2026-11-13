-- ===========================================================================
-- BTL CSDL: HỆ THỐNG QUẢN LÝ NHÀ THUỐC
-- File   : KiemTra_TinhDungDan.sql
-- Mục đích: Demo kiểm tra tính đúng đắn dữ liệu cho 2 màn hình nhập liệu
--           Màn hình 1: Quản lý Thuốc (/medicines)
--           Màn hình 2: Nhập Lô Thuốc (/medicines → Form nhập kho)
-- Chạy   : source /đường/dẫn/đến/KiemTra_TinhDungDan.sql
-- ===========================================================================
USE quan_ly_nha_thuoc;
SET NAMES utf8mb4;

-- ===========================================================================
-- MÀN HÌNH 1: QUẢN LÝ THUỐC (CRUD bảng THUOC)
-- ===========================================================================

SELECT '=== MAN HINH 1: QUAN LY THUOC ===' AS '';

-- -------------------------------------------------------------------------
-- TEST 1 ✅: Thêm thuốc HỢP LỆ → Thành công
-- -------------------------------------------------------------------------
SELECT '--- TEST 1: Them thuoc hop le (ky vong: thanh cong) ---' AS '';

INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc)
VALUES ('T099', 'Thuốc Test Demo', 'Paracetamol 500mg', 'Giảm đau nhẹ', 15000.00, 0, 'DM01');

SELECT MaThuoc, TenThuoc, DonGiaBan, MaDanhMuc
FROM THUOC WHERE MaThuoc = 'T099';
-- Kỳ vọng: 1 dòng trả về ✅

-- -------------------------------------------------------------------------
-- TEST 2 ❌: Thêm thuốc TRÙNG MÃ → ERROR 1062 (Duplicate PRIMARY KEY)
-- -------------------------------------------------------------------------
SELECT '--- TEST 2: Them thuoc trung ma (ky vong: ERROR 1062) ---' AS '';

INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc)
VALUES ('T099', 'Thuốc Trùng Mã', 'ABC', 'Test', 10000.00, 0, 'DM01');
-- Kỳ vọng: ERROR 1062 — Duplicate entry 'T099' for key 'PRIMARY' ❌

-- -------------------------------------------------------------------------
-- TEST 3 ❌: Thêm thuốc với DANH MỤC KHÔNG TỒN TẠI → ERROR 1452 (FK)
-- -------------------------------------------------------------------------
SELECT '--- TEST 3: Them thuoc voi DanhMuc khong ton tai (ky vong: ERROR 1452) ---' AS '';

INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc)
VALUES ('T098', 'Thuốc FK Test', 'ABC', 'Test', 10000.00, 0, 'DM99');
-- Kỳ vọng: ERROR 1452 — Foreign key constraint fails (MaDanhMuc='DM99' không tồn tại) ❌

-- -------------------------------------------------------------------------
-- TEST 4 ❌: Thêm thuốc THIẾU TenThuoc (NOT NULL) → ERROR 1048
-- -------------------------------------------------------------------------
SELECT '--- TEST 4: Them thuoc thieu TenThuoc (ky vong: ERROR 1048) ---' AS '';

INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc)
VALUES ('T097', NULL, 'ABC', 'Test', 10000.00, 0, 'DM01');
-- Kỳ vọng: ERROR 1048 — Column 'TenThuoc' cannot be null ❌

-- -------------------------------------------------------------------------
-- TEST 5 ✅: Cập nhật thuốc HỢP LỆ → Thành công
-- -------------------------------------------------------------------------
SELECT '--- TEST 5: Cap nhat thuoc hop le (ky vong: thanh cong) ---' AS '';

SELECT MaThuoc, TenThuoc, DonGiaBan FROM THUOC WHERE MaThuoc = 'T099';
-- Trước khi sửa

UPDATE THUOC
SET TenThuoc  = 'Thuốc Test Demo (Đã sửa)',
    DonGiaBan = 18000.00,
    ThanhPhan = 'Paracetamol 500mg, Cafein'
WHERE MaThuoc = 'T099';

SELECT MaThuoc, TenThuoc, DonGiaBan FROM THUOC WHERE MaThuoc = 'T099';
-- Kỳ vọng: DonGiaBan = 18000, TenThuoc đổi thành '...Đã sửa' ✅

-- -------------------------------------------------------------------------
-- TEST 6 ✅: Xóa thuốc KHÔNG vướng ràng buộc → Thành công
-- -------------------------------------------------------------------------
SELECT '--- TEST 6: Xoa thuoc khong vuong rang buoc (ky vong: thanh cong) ---' AS '';

DELETE FROM THUOC WHERE MaThuoc = 'T099';

SELECT * FROM THUOC WHERE MaThuoc = 'T099';
-- Kỳ vọng: 0 dòng trả về (xóa thành công) ✅


-- ===========================================================================
-- MÀN HÌNH 2: NHẬP LÔ THUỐC (TRANSACTION đồng bộ LO_THUOC ↔ THUOC.SoLuongTon)
-- ===========================================================================

SELECT '=== MAN HINH 2: NHAP LO THUOC ===' AS '';

-- -------------------------------------------------------------------------
-- TEST 7 ✅: Nhập lô THÀNH CÔNG → COMMIT, SoLuongTon tăng đúng
-- -------------------------------------------------------------------------
SELECT '--- TEST 7: Nhap lo thanh cong - COMMIT (ky vong: SoLuongTon tang 200) ---' AS '';

SELECT MaThuoc, TenThuoc, SoLuongTon FROM THUOC WHERE MaThuoc = 'T001';
-- Ghi nhận SoLuongTon TRƯỚC

START TRANSACTION;
    INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV)
    VALUES ('T001', 'LO-TEST-2026', 200, '2026-11-01', '2028-11-01', 12000.00, '2026-11-07', 'NCC01', 'NV01');
    UPDATE THUOC SET SoLuongTon = SoLuongTon + 200 WHERE MaThuoc = 'T001';
COMMIT;

SELECT MaThuoc, TenThuoc, SoLuongTon FROM THUOC WHERE MaThuoc = 'T001';
SELECT MaThuoc, SoLo, SoLuongThuocNhap FROM LO_THUOC WHERE MaThuoc = 'T001' AND SoLo = 'LO-TEST-2026';
-- Kỳ vọng: SoLuongTon tăng 200 | Lô mới có trong LO_THUOC ✅

-- -------------------------------------------------------------------------
-- TEST 8 ❌: Nhập lô TRÙNG SỐ LÔ → ERROR 1062, ROLLBACK, SoLuongTon KHÔNG đổi
-- -------------------------------------------------------------------------
SELECT '--- TEST 8: Nhap lo trung so lo - ROLLBACK (ky vong: SoLuongTon KHONG doi) ---' AS '';

SELECT SoLuongTon FROM THUOC WHERE MaThuoc = 'T001';
-- Ghi nhận SoLuongTon TRƯỚC (phải bằng giá trị sau TEST 7)

START TRANSACTION;
    INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV)
    VALUES ('T001', 'LO-TEST-2026', 999, '2026-01-01', '2028-01-01', 5000.00, '2026-01-01', 'NCC01', 'NV01');
    -- ❌ Bước này lỗi ERROR 1062 → transaction tự rollback
    UPDATE THUOC SET SoLuongTon = SoLuongTon + 999 WHERE MaThuoc = 'T001';
ROLLBACK;

SELECT SoLuongTon FROM THUOC WHERE MaThuoc = 'T001';
-- Kỳ vọng: SoLuongTon KHÔNG thay đổi (toàn vẹn dữ liệu được bảo đảm) ✅

-- -------------------------------------------------------------------------
-- TEST 9 ❌: Nhập lô cho THUỐC KHÔNG TỒN TẠI → ERROR 1452, ROLLBACK
-- -------------------------------------------------------------------------
SELECT '--- TEST 9: Nhap lo thuoc khong ton tai - ROLLBACK (ky vong: ERROR 1452) ---' AS '';

START TRANSACTION;
    INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV)
    VALUES ('T_GHOST', 'LO-GHOST-01', 100, '2026-01-01', '2028-01-01', 5000.00, '2026-01-01', 'NCC01', 'NV01');
    -- ❌ ERROR 1452: MaThuoc='T_GHOST' không có trong bảng THUOC
ROLLBACK;

SELECT * FROM LO_THUOC WHERE MaThuoc = 'T_GHOST';
-- Kỳ vọng: 0 dòng (không lô nào được thêm) ✅

-- -------------------------------------------------------------------------
-- TEST 10 ✅: Xóa lô thuốc → TRANSACTION trừ đúng SoLuongTon rồi mới xóa lô
-- -------------------------------------------------------------------------
SELECT '--- TEST 10: Xoa lo thuoc - COMMIT (ky vong: SoLuongTon giam 200, lo bien mat) ---' AS '';

SELECT SoLuongTon FROM THUOC WHERE MaThuoc = 'T001';
-- Ghi nhận TRƯỚC

START TRANSACTION;
    UPDATE THUOC
    SET SoLuongTon = SoLuongTon - (
        SELECT SoLuongThuocNhap FROM LO_THUOC
        WHERE MaThuoc = 'T001' AND SoLo = 'LO-TEST-2026'
    )
    WHERE MaThuoc = 'T001';

    DELETE FROM LO_THUOC WHERE MaThuoc = 'T001' AND SoLo = 'LO-TEST-2026';
COMMIT;

SELECT SoLuongTon FROM THUOC WHERE MaThuoc = 'T001';
SELECT * FROM LO_THUOC WHERE MaThuoc = 'T001' AND SoLo = 'LO-TEST-2026';
-- Kỳ vọng: SoLuongTon giảm 200 | 0 dòng lô (đã xóa thành công) ✅
