-- ===========================================================================
-- BTL CSDL: HỆ THỐNG QUẢN LÝ NHÀ THUỐC
-- File   : init_schema.sql
-- Mục đích: Tạo database và toàn bộ bảng từ đầu (chạy lần đầu khi cài đặt)
-- Chạy   : source /đường/dẫn/đến/init_schema.sql   (trong MySQL CLI)
-- Thứ tự : DANH_MUC → NHA_CUNG_CAP → NHAN_VIEN → KHACH_HANG
--           → THUOC → LO_THUOC → HOA_DON → CHI_TIET_HOA_DON
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. TẠO DATABASE
-- ---------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS quan_ly_nha_thuoc
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE quan_ly_nha_thuoc;

-- ---------------------------------------------------------------------------
-- 2. BẢNG DANH_MUC (không phụ thuộc bảng nào → tạo trước)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS DANH_MUC (
    MaDanhMuc   VARCHAR(20)  NOT NULL,
    TenDanhMuc  VARCHAR(255) NOT NULL,
    PRIMARY KEY (MaDanhMuc)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 3. BẢNG NHA_CUNG_CAP
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS NHA_CUNG_CAP (
    MaNCC   VARCHAR(20)  NOT NULL,
    TenNCC  VARCHAR(255) NOT NULL,
    Diachi  VARCHAR(255),
    SDT     VARCHAR(20),
    Email   VARCHAR(100),
    PRIMARY KEY (MaNCC)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 4. BẢNG NHAN_VIEN
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS NHAN_VIEN (
    MaNV    VARCHAR(20)    NOT NULL,
    TenNV   VARCHAR(255)   NOT NULL,
    SDT     VARCHAR(20),
    Email   VARCHAR(100),
    VaiTro  VARCHAR(100),
    Luong   DECIMAL(15, 2) DEFAULT 0,
    PRIMARY KEY (MaNV)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 5. BẢNG KHACH_HANG
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS KHACH_HANG (
    MaKH    VARCHAR(20)  NOT NULL,
    TenKH   VARCHAR(255) NOT NULL,
    SDT     VARCHAR(20),
    PRIMARY KEY (MaKH)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 6. BẢNG THUOC (FK → DANH_MUC)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS THUOC (
    MaThuoc     VARCHAR(20)    NOT NULL,
    TenThuoc    VARCHAR(255)   NOT NULL,
    ThanhPhan   VARCHAR(255),
    ChiDinh     VARCHAR(255),
    DonGiaBan   DECIMAL(15, 2) NOT NULL DEFAULT 0,
    SoLuongTon  INT            NOT NULL DEFAULT 0,
    MaDanhMuc   VARCHAR(20)    NOT NULL,
    PRIMARY KEY (MaThuoc),
    CONSTRAINT fk_thuoc_danhmuc
        FOREIGN KEY (MaDanhMuc) REFERENCES DANH_MUC(MaDanhMuc)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 7. BẢNG LO_THUOC (FK → THUOC, NHA_CUNG_CAP, NHAN_VIEN)
--    Khóa chính tổ hợp: (MaThuoc, SoLo) — mỗi thuốc có thể có nhiều lô,
--    nhưng số lô phải duy nhất trong cùng một loại thuốc.
--    MaNV: nhân viên tiếp nhận lô hàng (mở rộng ngoài ER, đang dùng trong app)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS LO_THUOC (
    MaThuoc           VARCHAR(20)    NOT NULL,
    SoLo              VARCHAR(100)   NOT NULL,
    SoLuongThuocNhap  INT            NOT NULL DEFAULT 0,
    NSX               DATE,
    HSD               DATE,
    DonGiaNhap        DECIMAL(15, 2) NOT NULL DEFAULT 0,
    NgayNhap          DATE,
    MaNCC             VARCHAR(20),
    MaNV              VARCHAR(20),
    PRIMARY KEY (MaThuoc, SoLo),
    CONSTRAINT fk_lothuoc_thuoc
        FOREIGN KEY (MaThuoc) REFERENCES THUOC(MaThuoc)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_lothuoc_ncc
        FOREIGN KEY (MaNCC) REFERENCES NHA_CUNG_CAP(MaNCC)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_lothuoc_nv
        FOREIGN KEY (MaNV) REFERENCES NHAN_VIEN(MaNV)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 8. BẢNG HOA_DON (FK → KHACH_HANG, NHAN_VIEN)
--    Quan hệ: KhachHang (1) —Mua— (N) HoaDon
--             NhanVien  (1) —Xuat— (N) HoaDon
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS HOA_DON (
    MaHD      VARCHAR(20)    NOT NULL,
    NgayBan   DATE,
    TongTien  DECIMAL(15, 2) NOT NULL DEFAULT 0,
    MaKH      VARCHAR(20),
    MaNV      VARCHAR(20),
    PRIMARY KEY (MaHD),
    CONSTRAINT fk_hoadon_khachhang
        FOREIGN KEY (MaKH) REFERENCES KHACH_HANG(MaKH)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_hoadon_nhanvien
        FOREIGN KEY (MaNV) REFERENCES NHAN_VIEN(MaNV)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 9. BẢNG CHI_TIET_HOA_DON (bảng trung gian N:N giữa HOA_DON và THUOC)
--    Thuộc tính quan hệ CoTrongHoaDon: SoLuongBan
--    FK → HOA_DON (CASCADE — xóa hóa đơn thì xóa luôn chi tiết)
--    FK → THUOC   (RESTRICT — không xóa thuốc nếu còn trong hóa đơn)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CHI_TIET_HOA_DON (
    MaHD        VARCHAR(20) NOT NULL,
    MaThuoc     VARCHAR(20) NOT NULL,
    SoLuongBan  INT         NOT NULL DEFAULT 1,
    PRIMARY KEY (MaHD, MaThuoc),
    CONSTRAINT fk_cthd_hoadon
        FOREIGN KEY (MaHD)    REFERENCES HOA_DON(MaHD)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_cthd_thuoc
        FOREIGN KEY (MaThuoc) REFERENCES THUOC(MaThuoc)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
