-- BTL CSDL: HE THONG QUAN LY NHA THUOC
-- Phan viec: Truy van & Tim kiem - Bao cao ton kho - Canh bao han su dung
-- CSDL: quan_ly_nha_thuoc
--
-- LUU Y MO HINH DU LIEU:
-- 1. THUOC.SoLuongTon la tong ton theo thuoc, khong phai ton theo tung lo.
-- 2. LO_THUOC.SoLuongThuocNhap la so luong nhap ban dau, khong phai so luong con lai.
-- 3. CHI_TIET_HOA_DON khong co SoLo, nen khong the tru doanh so ban theo tung lo.
-- 4. GiaTriTonKho ben duoi duoc tinh theo gia ban, khong phai gia von/ gia nhap.

USE quan_ly_nha_thuoc;

-- =========================================================
-- 1. TIM KIEM THUOC
-- JOIN: THUOC - DANH_MUC - LO_THUOC - NHA_CUNG_CAP
-- Thay doi @keyword va @expiry_status de thu nghiem.
-- @expiry_status: 'all' | 'expiring' | 'expired'
-- =========================================================
SET @keyword = '%para%' COLLATE utf8mb4_unicode_ci;
SET @expiry_status = 'all' COLLATE utf8mb4_unicode_ci;

SELECT
    t.MaThuoc,
    t.TenThuoc,
    t.ThanhPhan,
    t.ChiDinh,
    t.DonGiaBan,
    t.SoLuongTon,
    dm.TenDanhMuc,
    lt.SoLo,
    lt.NSX,
    lt.HSD,
    DATEDIFF(lt.HSD, CURDATE()) AS SoNgayConLai,
    ncc.TenNCC
FROM THUOC t
LEFT JOIN DANH_MUC dm ON t.MaDanhMuc = dm.MaDanhMuc
LEFT JOIN LO_THUOC lt ON t.MaThuoc = lt.MaThuoc
LEFT JOIN NHA_CUNG_CAP ncc ON lt.MaNCC = ncc.MaNCC
WHERE
    (
        @keyword IS NULL
        OR @keyword = ''
        OR t.MaThuoc LIKE @keyword
        OR t.TenThuoc LIKE @keyword
        OR dm.TenDanhMuc LIKE @keyword
    )
    AND
    (
        @expiry_status = 'all'
        OR (
            @expiry_status = 'expiring'
            AND lt.HSD IS NOT NULL
            AND lt.HSD >= CURDATE()
            AND lt.HSD <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
        )
        OR (
            @expiry_status = 'expired'
            AND lt.HSD IS NOT NULL
            AND lt.HSD < CURDATE()
        )
    )
ORDER BY t.TenThuoc, lt.HSD;

-- =========================================================
-- 2. BAO CAO TON KHO THEO THUOC
-- Gia tri ton kho = DonGiaBan * SoLuongTon.
-- =========================================================
SELECT
    t.MaThuoc,
    t.TenThuoc,
    dm.TenDanhMuc,
    t.DonGiaBan,
    COALESCE(t.SoLuongTon, 0) AS SoLuongTon,
    (t.DonGiaBan * COALESCE(t.SoLuongTon, 0)) AS GiaTriTonKho
FROM THUOC t
LEFT JOIN DANH_MUC dm ON t.MaDanhMuc = dm.MaDanhMuc
ORDER BY t.TenThuoc;

-- =========================================================
-- 3. TONG HOP TON KHO
-- =========================================================
SELECT
    COUNT(*) AS TongSoLoai,
    COALESCE(SUM(SoLuongTon), 0) AS TongSoLuong,
    COALESCE(SUM(DonGiaBan * SoLuongTon), 0) AS TongGiaTri
FROM THUOC;

-- =========================================================
-- 4. BAO CAO TON KHO THEO DANH MUC
-- =========================================================
SELECT
    dm.MaDanhMuc,
    dm.TenDanhMuc,
    COUNT(t.MaThuoc) AS SoLoaiThuoc,
    COALESCE(SUM(t.SoLuongTon), 0) AS TongSoLuong,
    COALESCE(SUM(t.DonGiaBan * t.SoLuongTon), 0) AS TongGiaTriTheoGiaBan
FROM DANH_MUC dm
LEFT JOIN THUOC t ON dm.MaDanhMuc = t.MaDanhMuc
GROUP BY dm.MaDanhMuc, dm.TenDanhMuc
ORDER BY dm.MaDanhMuc;

-- =========================================================
-- 5. CANH BAO LO THUOC DA HET HAN / SAP HET HAN 30 NGAY
-- JOIN: LO_THUOC - THUOC - DANH_MUC - NHA_CUNG_CAP
-- Dieu kien bao gom lo da het han va lo co HSD trong 30 ngay toi.
-- =========================================================
SELECT
    lt.MaThuoc,
    t.TenThuoc,
    dm.TenDanhMuc,
    lt.SoLo,
    lt.NSX,
    lt.HSD,
    lt.SoLuongThuocNhap,
    ncc.TenNCC,
    DATEDIFF(lt.HSD, CURDATE()) AS SoNgayConLai,
    CASE
        WHEN lt.HSD < CURDATE() THEN 'Da het han'
        ELSE 'Sap het han'
    END AS TrangThai
FROM LO_THUOC lt
JOIN THUOC t ON lt.MaThuoc = t.MaThuoc
LEFT JOIN DANH_MUC dm ON t.MaDanhMuc = dm.MaDanhMuc
LEFT JOIN NHA_CUNG_CAP ncc ON lt.MaNCC = ncc.MaNCC
WHERE
    lt.HSD IS NOT NULL
    AND lt.HSD <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
ORDER BY lt.HSD ASC;
