-- =====================================================================================
-- BÀI TẬP LỚN CSDL: PHÂN HỆ LẬP HÓA ĐƠN BÁN HÀNG (FORM 2)
-- Sinh viên thực hiện: B24DCCN...
-- =====================================================================================

USE quan_ly_nha_thuoc;

-- -------------------------------------------------------------------------------------
-- 1. TRUY VẤN LẤY THÔNG TIN ĐỔ VÀO GIAO DIỆN (NẠP DỮ LIỆU LÊN FORM)
-- -------------------------------------------------------------------------------------

-- Lấy danh sách thuốc còn hàng trong kho để khách lựa chọn
SELECT MaThuoc, TenThuoc, DonGiaBan, SoLuongTon 
FROM THUOC 
WHERE SoLuongTon > 0 
ORDER BY TenThuoc ASC;

-- Lấy danh sách nhân viên để chọn người lập hóa đơn
SELECT MaNV, TenNV, VaiTro 
FROM NHAN_VIEN 
ORDER BY TenNV ASC;

-- Lấy danh sách khách hàng
SELECT MaKH, TenKH, SDT 
FROM KHACH_HANG 
ORDER BY TenKH ASC;


-- -------------------------------------------------------------------------------------
-- 2. CÂU LỆNH SAU NÚT BẤM "LƯU & XUẤT HÓA ĐƠN" (TRANSACTION BÁN HÀNG & TRỪ KHO)
-- Hành động: Ghi Hóa đơn -> Ghi Chi tiết từng món -> Cập nhật giảm Tồn kho ở bảng THUOC
-- -------------------------------------------------------------------------------------

START TRANSACTION;

    -- Bước 2.1: Kiểm tra tồn kho của thuốc trước khi xuất bán (Tránh bán âm kho)
    SELECT SoLuongTon, TenThuoc 
    FROM THUOC 
    WHERE MaThuoc = 'T001' FOR UPDATE;

    -- Bước 2.2: Thêm mới hóa đơn vào bảng HOA_DON (Master)
    INSERT INTO HOA_DON (MaHD, NgayBan, TongTien, MaNV, MaKH)
    VALUES ('HD001', NOW(), 170000.00, 'NV01', 'KH02');

    -- Bước 2.3: Thêm món thuốc 1 vào chi tiết hóa đơn (Detail)
    INSERT INTO CHI_TIET_HOA_DON (MaHD, MaThuoc, SoLuongBan)
    VALUES ('HD001', 'T001', 2);

    -- Bước 2.4: Trừ số lượng tồn kho của thuốc 1 trong bảng THUOC
    UPDATE THUOC 
    SET SoLuongTon = SoLuongTon - 2 
    WHERE MaThuoc = 'T001';

    -- Bước 2.5: Thêm món thuốc 2 vào chi tiết hóa đơn
    INSERT INTO CHI_TIET_HOA_DON (MaHD, MaThuoc, SoLuongBan)
    VALUES ('HD001', 'T002', 1);

    -- Bước 2.6: Trừ số lượng tồn kho của thuốc 2
    UPDATE THUOC 
    SET SoLuongTon = SoLuongTon - 1 
    WHERE MaThuoc = 'T002';

-- Xác nhận lưu vĩnh viễn vào CSDL nếu không có lỗi
COMMIT;

-- (Nếu xảy ra lỗi thiếu hàng hoặc lỗi mạng thì hệ thống tự động ROLLBACK để hủy bỏ)


-- -------------------------------------------------------------------------------------
-- 3. CÂU LỆNH HỦY / XÓA HÓA ĐƠN (NẾU KHÁCH TRẢ HÀNG HOẶC HỦY ĐƠN)
-- Hành động: Hoàn trả lại số lượng tồn kho -> Sau đó mới xóa hóa đơn
-- -------------------------------------------------------------------------------------

START TRANSACTION;

    -- Hoàn trả lại số lượng tồn kho cho các thuốc trong hóa đơn cần xóa
    UPDATE THUOC t
    INNER JOIN CHI_TIET_HOA_DON ct ON t.MaThuoc = ct.MaThuoc
    SET t.SoLuongTon = t.SoLuongTon + ct.SoLuongBan
    WHERE ct.MaHD = 'HD001';

    -- Xóa dữ liệu trong bảng CHI_TIET_HOA_DON trước (ràng buộc FK)
    DELETE FROM CHI_TIET_HOA_DON WHERE MaHD = 'HD001';

    -- Xóa hóa đơn chính
    DELETE FROM HOA_DON WHERE MaHD = 'HD001';

COMMIT;