import re
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_db_connection

app = Flask(__name__)
app.secret_key = "pharma_secret_key_qlnt"  # Khóa bảo mật để dùng tính năng thông báo flash


# ===========================================================================
# HÀM TRUY VẤN DÙNG CHUNG
# ===========================================================================

def query_db(sql, params=()):
    """Chạy câu SELECT và trả về danh sách dict."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)

        return cursor.fetchall()

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def run_transaction(statements):
    """
    Chạy nhiều câu lệnh trong MỘT transaction: hoặc tất cả cùng thành công (COMMIT),
    hoặc có lỗi thì hủy toàn bộ (ROLLBACK).

    statements: danh sách (nhãn, sql, tham_số). Nhãn cho biết câu nào gây lỗi
                để báo lỗi dễ hiểu (vd: "DANH_MUC", "LO_THUOC").
    Trả về: (True, None, None) hoặc (False, ngoại_lệ, nhãn_câu_gây_lỗi)
    """
    connection = None
    cursor = None
    current = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        connection.start_transaction()
        for label, sql, params in statements:
            current = label
            cursor.execute(sql, params)
        connection.commit()
        return True, None, None
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        return False, exc, current
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# ===========================================================================
# TRA CỨU & BÁO CÁO (giữ nguyên)
# ===========================================================================

@app.route("/")
def index():
    return redirect(url_for("search_medicine"))


@app.route("/search")
def search_medicine():
    keyword = request.args.get("q", "").strip()
    expiry_status = request.args.get("expiry_status", "all")

    if expiry_status not in ("all", "expiring", "expired"):
        expiry_status = "all"

    sql = """
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
    """

    conditions = []
    params = []

    if keyword:
        pattern = f"%{keyword}%"
        conditions.append("""
            (
                t.MaThuoc LIKE %s
                OR t.TenThuoc LIKE %s
                OR dm.TenDanhMuc LIKE %s
            )
        """)
        params.extend([pattern, pattern, pattern])

    if expiry_status == "expiring":
        conditions.append("""
            lt.HSD IS NOT NULL
            AND lt.HSD >= CURDATE()
            AND lt.HSD <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
        """)

    elif expiry_status == "expired":
        conditions.append("""
            lt.HSD IS NOT NULL
            AND lt.HSD < CURDATE()
        """)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY t.TenThuoc, lt.HSD"

    medicines = query_db(sql, tuple(params))

    return render_template(
        "search.html",
        medicines=medicines,
        keyword=keyword,
        expiry_status=expiry_status
    )


@app.route("/inventory")
def inventory_report():
    sql = """
        SELECT
            t.MaThuoc,
            t.TenThuoc,
            dm.TenDanhMuc,
            t.DonGiaBan,
            t.SoLuongTon,
            (t.DonGiaBan * COALESCE(t.SoLuongTon, 0)) AS GiaTriTonKho
        FROM THUOC t
        LEFT JOIN DANH_MUC dm ON t.MaDanhMuc = dm.MaDanhMuc
        ORDER BY t.TenThuoc
    """

    inventory = query_db(sql)

    summary_sql = """
        SELECT
            COUNT(*) AS TongSoLoai,
            COALESCE(SUM(SoLuongTon), 0) AS TongSoLuong,
            COALESCE(SUM(DonGiaBan * SoLuongTon), 0) AS TongGiaTri
        FROM THUOC
    """

    summary = query_db(summary_sql)[0]

    return render_template(
        "inventory.html",
        inventory=inventory,
        summary=summary
    )


@app.route("/expiry")
def expiry_report():
    sql = """
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
                WHEN lt.HSD < CURDATE() THEN 'Đã hết hạn'
                ELSE 'Sắp hết hạn'
            END AS TrangThai
        FROM LO_THUOC lt
        JOIN THUOC t ON lt.MaThuoc = t.MaThuoc
        LEFT JOIN DANH_MUC dm ON t.MaDanhMuc = dm.MaDanhMuc
        LEFT JOIN NHA_CUNG_CAP ncc ON lt.MaNCC = ncc.MaNCC
        WHERE
            lt.HSD IS NOT NULL
            AND lt.HSD <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
        ORDER BY lt.HSD ASC
    """

    expiry_list = query_db(sql)

    return render_template(
        "expiry.html",
        expiry_list=expiry_list
    )


# ===========================================================================
# KIỂM TRA DỮ LIỆU ĐẦU VÀO (validation) - ném ValueError kèm thông báo tiếng Việt
# ===========================================================================

INT_MAX = 2_147_483_647                    # giới hạn kiểu INT của MySQL
MONEY_MAX = Decimal("9999999999999.99")    # giới hạn DECIMAL(15,2)
CODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s.\-]{7,19}$")


def clean(value):
    return (value or "").strip()


def check_len(value, max_len, label):
    if len(value) > max_len:
        raise ValueError(f"{label} tối đa {max_len} ký tự (bạn đang nhập {len(value)} ký tự).")


def validate_code(code, label):
    """Mã (khóa chính): bắt buộc, <= 20 ký tự, chỉ chữ không dấu/số/-/_ ; tự viết HOA."""
    if not code:
        raise ValueError(f"{label} không được để trống.")
    check_len(code, 20, label)
    if not CODE_RE.match(code):
        raise ValueError(f"{label} chỉ gồm chữ không dấu, chữ số, dấu gạch ngang hoặc gạch dưới (không có khoảng trắng).")
    return code.upper()


def parse_money(text, label):
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{label} phải là một số hợp lệ.")
    if not value.is_finite() or value < 0:
        raise ValueError(f"{label} phải là số không âm.")
    if value > MONEY_MAX:
        raise ValueError(f"{label} quá lớn (tối đa {MONEY_MAX:,}).")
    return value.quantize(Decimal("0.01"))


def parse_positive_int(text, label):
    try:
        number = int(text)
    except (TypeError, ValueError):
        raise ValueError(f"{label} phải là số nguyên.")
    if number <= 0:
        raise ValueError(f"{label} phải lớn hơn 0.")
    if number > INT_MAX:
        raise ValueError(f"{label} quá lớn.")
    return number


def parse_date(text, label, required=False):
    if not text:
        if required:
            raise ValueError(f"{label} không được để trống.")
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{label} không phải ngày hợp lệ.")


def validate_category(ma, ten):
    ma = validate_code(ma, "Mã danh mục")
    if not ten:
        raise ValueError("Tên danh mục không được để trống.")
    check_len(ten, 255, "Tên danh mục")
    return ma, ten


def validate_supplier(ma, ten, diachi, sdt, email):
    ma = validate_code(ma, "Mã nhà cung cấp")
    if not ten:
        raise ValueError("Tên nhà cung cấp không được để trống.")
    check_len(ten, 255, "Tên nhà cung cấp")
    check_len(diachi, 255, "Địa chỉ")
    if sdt and not PHONE_RE.match(sdt):
        raise ValueError("Số điện thoại không hợp lệ (chỉ gồm số, có thể có dấu +, khoảng trắng, dấu chấm hoặc gạch ngang; 8-20 ký tự).")
    if email:
        check_len(email, 100, "Email")
        if not EMAIL_RE.match(email):
            raise ValueError("Email không hợp lệ (ví dụ: ten@congty.vn).")
    return ma, ten, (diachi or None), (sdt or None), (email or None)


# Tên bảng/cột dùng để kiểm tra trùng TÊN (chỉ là hằng số trong code, không lấy từ người dùng)
NAME_CHECKS = {
    "DANH_MUC": ("MaDanhMuc", "TenDanhMuc", "danh mục"),
    "NHA_CUNG_CAP": ("MaNCC", "TenNCC", "nhà cung cấp"),
}


def ensure_name_not_used(table, name, exclude_code=None):
    """Không cho hai mã khác nhau cùng mang một tên (tránh dữ liệu trùng lặp ngầm)."""
    key_col, name_col, vn_name = NAME_CHECKS[table]
    sql = f"SELECT {key_col} AS Ma, {name_col} AS Ten FROM {table} WHERE {name_col} = %s"
    params = [name]
    if exclude_code:
        sql += f" AND {key_col} <> %s"
        params.append(exclude_code)
    rows = query_db(sql + " LIMIT 1", tuple(params))
    if rows:
        raise ValueError(
            f'Tên {vn_name} "{rows[0]["Ten"]}" đã được dùng bởi mã {rows[0]["Ma"]}. '
            f"Hãy chọn {vn_name} có sẵn trong danh sách thay vì tạo trùng."
        )


# ===========================================================================
# GIẢI THÍCH LỖI CƠ SỞ DỮ LIỆU CHO NGƯỜI DÙNG
# ===========================================================================

def explain_duplicate(label, ctx):
    """Lỗi 1062 (trùng khóa chính): nói rõ bản ghi cũ đang là gì và KHÔNG ghi đè."""
    if label == "DANH_MUC":
        rows = query_db("SELECT MaDanhMuc, TenDanhMuc FROM DANH_MUC WHERE MaDanhMuc = %s", (ctx.get("ma_dm"),))
        if rows:
            return (f'Mã danh mục "{rows[0]["MaDanhMuc"]}" đã tồn tại với tên "{rows[0]["TenDanhMuc"]}" '
                    f'(bạn vừa nhập tên "{ctx.get("ten_dm")}"). Hệ thống KHÔNG ghi đè dữ liệu cũ. '
                    f'Hãy dùng mã khác, chọn danh mục có sẵn, hoặc bấm "Sửa" ở bảng Danh mục nếu muốn đổi tên.')
    if label == "NHA_CUNG_CAP":
        rows = query_db("SELECT MaNCC, TenNCC FROM NHA_CUNG_CAP WHERE MaNCC = %s", (ctx.get("ma_ncc"),))
        if rows:
            return (f'Mã nhà cung cấp "{rows[0]["MaNCC"]}" đã tồn tại với tên "{rows[0]["TenNCC"]}" '
                    f'(bạn vừa nhập tên "{ctx.get("ten_ncc")}"). Hệ thống KHÔNG ghi đè dữ liệu cũ. '
                    f'Hãy dùng mã khác, chọn nhà cung cấp có sẵn, hoặc bấm "Sửa" ở bảng Nhà cung cấp.')
    if label == "THUOC":
        rows = query_db("SELECT MaThuoc, TenThuoc FROM THUOC WHERE MaThuoc = %s", (ctx.get("ma_thuoc"),))
        if rows:
            return (f'Mã thuốc "{rows[0]["MaThuoc"]}" đã tồn tại ("{rows[0]["TenThuoc"]}"). '
                    f'Hãy dùng mã khác hoặc bấm "Sửa" ở bảng thuốc.')
    if label == "LO_THUOC":
        return (f'Lô "{ctx.get("so_lo")}" của thuốc {ctx.get("ma_thuoc")} đã tồn tại. '
                f"Mỗi thuốc không được có hai lô cùng số lô; hãy dùng số lô khác.")
    return "Dữ liệu bị trùng khóa chính với bản ghi đã có."


def explain_db_error(exc, label, ctx):
    errno = getattr(exc, "errno", None)
    if errno == 1062:
        try:
            return explain_duplicate(label, ctx)
        except Exception:
            return "Dữ liệu bị trùng khóa chính với bản ghi đã có."
    if errno == 1452:
        return ("Một giá trị tham chiếu (thuốc, danh mục, nhà cung cấp hoặc nhân viên) không còn tồn tại "
                "trong hệ thống. Hãy tải lại trang và chọn lại.")
    if errno == 1451:
        if label == "THUOC":
            return "Không thể xóa: thuốc này đã xuất hiện trong hóa đơn bán hàng."
        return "Không thể xóa: dữ liệu này đang được bảng khác sử dụng."
    if errno == 1406:
        return "Dữ liệu nhập quá dài so với độ dài cột trong cơ sở dữ liệu."
    if errno == 1048:
        return "Thiếu dữ liệu bắt buộc."
    if errno in (1264, 1292, 1366):
        return "Giá trị số hoặc ngày nằm ngoài phạm vi cho phép của cơ sở dữ liệu."
    return f"Lỗi cơ sở dữ liệu (mã {errno}): {exc}"


def commit_or_flash(statements, ctx, success_message):
    ok, exc, label = run_transaction(statements)
    if ok:
        flash(success_message, "success")
        return True
    flash(explain_db_error(exc, label, ctx), "danger")
    return False


# ===========================================================================
# XỬ LÝ CÁC FORM TRÊN TRANG /medicines
# Mỗi hàm trả True nếu thành công (trang sẽ chuyển hướng), False nếu lỗi (giữ lại dữ liệu đã nhập)
# ===========================================================================

def resolve_category(form):
    """Chọn danh mục có sẵn HOẶC tạo danh mục mới (kèm bước INSERT nằm cùng transaction)."""
    new_ma = clean(form.get("ma_danh_muc_new"))
    new_ten = clean(form.get("ten_danh_muc_new"))
    if new_ma or new_ten:
        ma, ten = validate_category(new_ma, new_ten)
        ensure_name_not_used("DANH_MUC", ten)
        step = ("DANH_MUC", "INSERT INTO DANH_MUC (MaDanhMuc, TenDanhMuc) VALUES (%s, %s)", (ma, ten))
        return ma, ten, [step]
    ma = clean(form.get("ma_danh_muc"))
    if not ma:
        raise ValueError("Vui lòng chọn danh mục hoặc tạo danh mục mới.")
    return ma, None, []


def resolve_supplier(form):
    """Chọn nhà cung cấp có sẵn HOẶC tạo mới với đầy đủ thông tin (mã, tên, địa chỉ, SĐT, email)."""
    fields = [clean(form.get(k)) for k in
              ("ma_ncc_new", "ten_ncc_new", "diachi_ncc_new", "sdt_ncc_new", "email_ncc_new")]
    if any(fields):
        ma, ten, diachi, sdt, email = validate_supplier(*fields)
        ensure_name_not_used("NHA_CUNG_CAP", ten)
        step = ("NHA_CUNG_CAP",
                "INSERT INTO NHA_CUNG_CAP (MaNCC, TenNCC, Diachi, SDT, Email) VALUES (%s, %s, %s, %s, %s)",
                (ma, ten, diachi, sdt, email))
        return ma, ten, [step]
    ma = clean(form.get("ma_ncc"))
    if not ma:
        raise ValueError("Vui lòng chọn nhà cung cấp hoặc tạo nhà cung cấp mới.")
    return ma, None, []


def read_medicine_fields(form):
    ten = clean(form.get("ten_thuoc"))
    if not ten:
        raise ValueError("Tên thuốc không được để trống.")
    check_len(ten, 255, "Tên thuốc")
    thanh_phan = clean(form.get("thanh_phan"))
    chi_dinh = clean(form.get("chi_dinh"))
    check_len(thanh_phan, 255, "Thành phần")
    check_len(chi_dinh, 255, "Chỉ định")
    gia = parse_money(clean(form.get("don_gia_ban")), "Đơn giá bán")
    return ten, thanh_phan, chi_dinh, gia


def handle_add_medicine(form):
    ma_thuoc = validate_code(clean(form.get("ma_thuoc")), "Mã thuốc")
    ten, thanh_phan, chi_dinh, gia = read_medicine_fields(form)
    ma_dm, ten_dm, steps = resolve_category(form)

    # Tồn kho luôn khởi tạo = 0; số lượng chỉ tăng khi NHẬP LÔ (để tồn kho luôn khớp với các lô)
    steps.append(("THUOC", """
        INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc)
        VALUES (%s, %s, %s, %s, %s, 0, %s)
    """, (ma_thuoc, ten, thanh_phan or None, chi_dinh or None, gia, ma_dm)))

    extra = f' và danh mục mới "{ten_dm}"' if ten_dm else ""
    return commit_or_flash(steps, {"ma_thuoc": ma_thuoc, "ma_dm": ma_dm, "ten_dm": ten_dm},
                           f"Đã thêm thuốc [{ma_thuoc}]{extra}. Hãy nhập lô để có tồn kho.")


def handle_update_medicine(form):
    ma_thuoc = clean(form.get("ma_thuoc"))
    if not query_db("SELECT 1 AS ok FROM THUOC WHERE MaThuoc = %s", (ma_thuoc,)):
        raise ValueError(f'Thuốc "{ma_thuoc}" không tồn tại (có thể đã bị xóa). Hãy tải lại trang.')
    ten, thanh_phan, chi_dinh, gia = read_medicine_fields(form)
    ma_dm, ten_dm, steps = resolve_category(form)

    # KHÔNG cập nhật SoLuongTon ở đây: tồn kho chỉ thay đổi qua nhập lô / xóa lô / bán hàng
    steps.append(("THUOC", """
        UPDATE THUOC
        SET TenThuoc = %s, ThanhPhan = %s, ChiDinh = %s, DonGiaBan = %s, MaDanhMuc = %s
        WHERE MaThuoc = %s
    """, (ten, thanh_phan or None, chi_dinh or None, gia, ma_dm, ma_thuoc)))

    return commit_or_flash(steps, {"ma_thuoc": ma_thuoc, "ma_dm": ma_dm, "ten_dm": ten_dm},
                           f"Đã cập nhật thuốc [{ma_thuoc}].")


def handle_add_batch(form):
    ma_thuoc = clean(form.get("batch_ma_thuoc"))
    if not ma_thuoc:
        raise ValueError("Vui lòng chọn thuốc cần nhập lô.")
    if not query_db("SELECT 1 AS ok FROM THUOC WHERE MaThuoc = %s", (ma_thuoc,)):
        raise ValueError(f'Thuốc "{ma_thuoc}" không tồn tại. Hãy tải lại trang.')

    so_lo = clean(form.get("so_lo"))
    if not so_lo:
        raise ValueError("Số lô không được để trống.")
    check_len(so_lo, 100, "Số lô")

    so_luong = parse_positive_int(clean(form.get("so_luong_nhap")), "Số lượng nhập")
    don_gia_nhap = parse_money(clean(form.get("don_gia_nhap")), "Đơn giá nhập")
    nsx = parse_date(clean(form.get("nsx")), "Ngày sản xuất")
    hsd = parse_date(clean(form.get("hsd")), "Hạn sử dụng", required=True)
    ngay_nhap = parse_date(clean(form.get("ngay_nhap")), "Ngày nhập kho") or date.today()

    if nsx and hsd <= nsx:
        raise ValueError("Hạn sử dụng phải sau ngày sản xuất.")
    if nsx and nsx > ngay_nhap:
        raise ValueError("Ngày sản xuất không được sau ngày nhập kho.")
    if hsd < ngay_nhap:
        raise ValueError("Không thể nhập lô đã hết hạn (hạn sử dụng trước ngày nhập kho).")

    ma_nv = clean(form.get("ma_nv")) or None
    ma_ncc, ten_ncc, steps = resolve_supplier(form)

    # Cả 3 bước (tạo NCC mới nếu có, thêm lô, cộng tồn kho) cùng thành công hoặc cùng hủy
    steps.append(("LO_THUOC", """
        INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (ma_thuoc, so_lo, so_luong, nsx, hsd, don_gia_nhap, ngay_nhap, ma_ncc, ma_nv)))
    steps.append(("THUOC", """
        UPDATE THUOC SET SoLuongTon = COALESCE(SoLuongTon, 0) + %s WHERE MaThuoc = %s
    """, (so_luong, ma_thuoc)))

    extra = f' (đã tạo nhà cung cấp mới "{ten_ncc}")' if ten_ncc else ""
    return commit_or_flash(steps, {"ma_thuoc": ma_thuoc, "so_lo": so_lo, "ma_ncc": ma_ncc, "ten_ncc": ten_ncc},
                           f"Nhập lô thành công cho thuốc {ma_thuoc} (số lô {so_lo}, +{so_luong}){extra}.")


def handle_add_category(form):
    ma, ten = validate_category(clean(form.get("dm_ma")), clean(form.get("dm_ten")))
    ensure_name_not_used("DANH_MUC", ten)
    steps = [("DANH_MUC", "INSERT INTO DANH_MUC (MaDanhMuc, TenDanhMuc) VALUES (%s, %s)", (ma, ten))]
    return commit_or_flash(steps, {"ma_dm": ma, "ten_dm": ten}, f'Đã thêm danh mục [{ma}] "{ten}".')


def handle_update_category(form):
    ma, ten = validate_category(clean(form.get("dm_ma")), clean(form.get("dm_ten")))
    if not query_db("SELECT 1 AS ok FROM DANH_MUC WHERE MaDanhMuc = %s", (ma,)):
        raise ValueError(f'Danh mục "{ma}" không tồn tại.')
    ensure_name_not_used("DANH_MUC", ten, exclude_code=ma)
    steps = [("DANH_MUC", "UPDATE DANH_MUC SET TenDanhMuc = %s WHERE MaDanhMuc = %s", (ten, ma))]
    return commit_or_flash(steps, {"ma_dm": ma, "ten_dm": ten}, f'Đã cập nhật danh mục [{ma}].')


def read_supplier_form(form):
    return validate_supplier(clean(form.get("ncc_ma")), clean(form.get("ncc_ten")),
                             clean(form.get("ncc_diachi")), clean(form.get("ncc_sdt")),
                             clean(form.get("ncc_email")))


def handle_add_supplier(form):
    ma, ten, diachi, sdt, email = read_supplier_form(form)
    ensure_name_not_used("NHA_CUNG_CAP", ten)
    steps = [("NHA_CUNG_CAP",
              "INSERT INTO NHA_CUNG_CAP (MaNCC, TenNCC, Diachi, SDT, Email) VALUES (%s, %s, %s, %s, %s)",
              (ma, ten, diachi, sdt, email))]
    return commit_or_flash(steps, {"ma_ncc": ma, "ten_ncc": ten}, f'Đã thêm nhà cung cấp [{ma}] "{ten}".')


def handle_update_supplier(form):
    ma, ten, diachi, sdt, email = read_supplier_form(form)
    if not query_db("SELECT 1 AS ok FROM NHA_CUNG_CAP WHERE MaNCC = %s", (ma,)):
        raise ValueError(f'Nhà cung cấp "{ma}" không tồn tại.')
    ensure_name_not_used("NHA_CUNG_CAP", ten, exclude_code=ma)
    steps = [("NHA_CUNG_CAP",
              "UPDATE NHA_CUNG_CAP SET TenNCC = %s, Diachi = %s, SDT = %s, Email = %s WHERE MaNCC = %s",
              (ten, diachi, sdt, email, ma))]
    return commit_or_flash(steps, {"ma_ncc": ma, "ten_ncc": ten}, f"Đã cập nhật nhà cung cấp [{ma}].")


ACTIONS = {
    "add_medicine": handle_add_medicine,
    "update_medicine": handle_update_medicine,
    "add_batch": handle_add_batch,
    "add_category": handle_add_category,
    "update_category": handle_update_category,
    "add_supplier": handle_add_supplier,
    "update_supplier": handle_update_supplier,
}


@app.route("/medicines", methods=["GET", "POST"])
def manage_medicines():
    form = {}

    if request.method == "POST":
        form = request.form
        handler = ACTIONS.get(clean(form.get("action")))
        if handler is None:
            flash("Thao tác không hợp lệ.", "danger")
        else:
            try:
                if handler(form):
                    return redirect(url_for("manage_medicines"))  # tránh gửi lại form khi F5
            except ValueError as err:
                flash(str(err), "danger")
            except Exception as err:  # lỗi bất ngờ (mất kết nối CSDL...)
                app.logger.exception("Lỗi khi xử lý /medicines")
                flash(f"Lỗi hệ thống: {err}", "danger")

    categories = query_db("""
        SELECT dm.MaDanhMuc, dm.TenDanhMuc, COUNT(t.MaThuoc) AS SoThuoc
        FROM DANH_MUC dm
        LEFT JOIN THUOC t ON t.MaDanhMuc = dm.MaDanhMuc
        GROUP BY dm.MaDanhMuc, dm.TenDanhMuc
        ORDER BY dm.MaDanhMuc
    """)
    suppliers = query_db("""
        SELECT ncc.MaNCC, ncc.TenNCC, ncc.Diachi, ncc.SDT, ncc.Email, COUNT(lt.SoLo) AS SoLo
        FROM NHA_CUNG_CAP ncc
        LEFT JOIN LO_THUOC lt ON lt.MaNCC = ncc.MaNCC
        GROUP BY ncc.MaNCC, ncc.TenNCC, ncc.Diachi, ncc.SDT, ncc.Email
        ORDER BY ncc.MaNCC
    """)
    employees = query_db("SELECT MaNV, TenNV FROM NHAN_VIEN ORDER BY TenNV")
    medicines = query_db("""
        SELECT t.*, dm.TenDanhMuc
        FROM THUOC t
        LEFT JOIN DANH_MUC dm ON t.MaDanhMuc = dm.MaDanhMuc
        ORDER BY t.MaThuoc DESC
    """)
    batches = query_db("""
        SELECT lt.MaThuoc, t.TenThuoc, lt.SoLo, lt.SoLuongThuocNhap, lt.NSX, lt.HSD,
               lt.DonGiaNhap, lt.NgayNhap, ncc.TenNCC, nv.TenNV,
               DATEDIFF(lt.HSD, CURDATE()) AS SoNgayConLai
        FROM LO_THUOC lt
        JOIN THUOC t ON lt.MaThuoc = t.MaThuoc
        LEFT JOIN NHA_CUNG_CAP ncc ON lt.MaNCC = ncc.MaNCC
        LEFT JOIN NHAN_VIEN nv ON lt.MaNV = nv.MaNV
        ORDER BY lt.NgayNhap DESC, lt.HSD
        LIMIT 200
    """)

    return render_template(
        "medicines.html",
        categories=categories, suppliers=suppliers, employees=employees,
        medicines=medicines, batches=batches,
        form=form, today=date.today().isoformat()
    )


# ===========================================================================
# CÁC THAO TÁC XÓA
# ===========================================================================

@app.route("/medicines/delete/<string:ma_thuoc>", methods=["POST"])
def delete_medicine(ma_thuoc):
    # Các lô của thuốc bị xóa theo (ON DELETE CASCADE); thuốc đã có trong hóa đơn thì bị chặn (RESTRICT)
    steps = [("THUOC", "DELETE FROM THUOC WHERE MaThuoc = %s", (ma_thuoc,))]
    commit_or_flash(steps, {"ma_thuoc": ma_thuoc}, f"Đã xóa thuốc mã {ma_thuoc} cùng các lô của thuốc.")
    return redirect(url_for("manage_medicines"))


@app.route("/categories/delete/<string:ma_dm>", methods=["POST"])
def delete_category(ma_dm):
    used = query_db("SELECT COUNT(*) AS n FROM THUOC WHERE MaDanhMuc = %s", (ma_dm,))[0]["n"]
    if used:
        flash(f"Không thể xóa danh mục {ma_dm}: đang có {used} thuốc thuộc danh mục này. "
              f"Hãy chuyển các thuốc sang danh mục khác trước.", "danger")
    else:
        steps = [("DANH_MUC", "DELETE FROM DANH_MUC WHERE MaDanhMuc = %s", (ma_dm,))]
        commit_or_flash(steps, {"ma_dm": ma_dm}, f"Đã xóa danh mục {ma_dm}.")
    return redirect(url_for("manage_medicines"))


@app.route("/suppliers/delete/<string:ma_ncc>", methods=["POST"])
def delete_supplier(ma_ncc):
    used = query_db("SELECT COUNT(*) AS n FROM LO_THUOC WHERE MaNCC = %s", (ma_ncc,))[0]["n"]
    if used:
        flash(f"Không thể xóa nhà cung cấp {ma_ncc}: đã có {used} lô thuốc nhập từ nhà cung cấp này.", "danger")
    else:
        steps = [("NHA_CUNG_CAP", "DELETE FROM NHA_CUNG_CAP WHERE MaNCC = %s", (ma_ncc,))]
        commit_or_flash(steps, {"ma_ncc": ma_ncc}, f"Đã xóa nhà cung cấp {ma_ncc}.")
    return redirect(url_for("manage_medicines"))


@app.route("/batches/delete", methods=["POST"])
def delete_batch():
    """Xóa lô: trừ tồn kho tương ứng rồi mới xóa lô, trong cùng một transaction."""
    ma_thuoc = clean(request.form.get("ma_thuoc"))
    so_lo = clean(request.form.get("so_lo"))
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        cursor.execute("SELECT SoLuongThuocNhap FROM LO_THUOC WHERE MaThuoc = %s AND SoLo = %s FOR UPDATE",
                       (ma_thuoc, so_lo))
        lot = cursor.fetchone()
        if lot is None:
            connection.rollback()
            flash(f'Lô "{so_lo}" của thuốc {ma_thuoc} không tồn tại.', "danger")
            return redirect(url_for("manage_medicines"))

        cursor.execute("SELECT SoLuongTon FROM THUOC WHERE MaThuoc = %s FOR UPDATE", (ma_thuoc,))
        ton = (cursor.fetchone() or {}).get("SoLuongTon") or 0
        if ton < lot["SoLuongThuocNhap"]:
            connection.rollback()
            flash(f"Không thể xóa lô {so_lo}: tồn kho hiện tại ({ton}) ít hơn số lượng của lô "
                  f"({lot['SoLuongThuocNhap']}), nghĩa là một phần hàng đã được bán. "
                  f"Xóa lô sẽ làm tồn kho bị âm.", "danger")
            return redirect(url_for("manage_medicines"))

        cursor.execute("UPDATE THUOC SET SoLuongTon = SoLuongTon - %s WHERE MaThuoc = %s",
                       (lot["SoLuongThuocNhap"], ma_thuoc))
        cursor.execute("DELETE FROM LO_THUOC WHERE MaThuoc = %s AND SoLo = %s", (ma_thuoc, so_lo))
        connection.commit()
        flash(f"Đã xóa lô {so_lo} của thuốc {ma_thuoc} và trừ {lot['SoLuongThuocNhap']} khỏi tồn kho.", "success")
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        flash(explain_db_error(exc, "LO_THUOC", {}), "danger")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
    return redirect(url_for("manage_medicines"))


if __name__ == "__main__":
    app.run(debug=True)
