from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from db import get_db_connection

app = Flask(__name__)
app.secret_key = "pharma_secret_key_qlnt"  # Khóa bảo mật để dùng tính năng thông báo


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

@app.route("/inventory/export-excel")
def export_inventory_excel():
    """Xuất Báo cáo Tồn kho & Định giá ra file Excel (.xlsx) chuẩn biểu mẫu thực tế."""
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

    wb = Workbook()
    ws = wb.active
    ws.title = "BaoCaoTonKho"

    # Khai báo các kiểu định dạng (Font, Border, Fill, Alignment)
    font_unit = Font(name="Times New Roman", size=11, bold=True)
    font_sub = Font(name="Times New Roman", size=10, italic=True)
    font_title = Font(name="Times New Roman", size=15, bold=True)
    font_header = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Times New Roman", size=11)
    font_bold = Font(name="Times New Roman", size=11, bold=True)
    fill_header = PatternFill(start_color="1E6B52", end_color="1E6B52", fill_type="solid")
    fill_total = PatternFill(start_color="EEF6F3", end_color="EEF6F3", fill_type="solid")
    thin = Side(border_style="thin", color="888888")
    border_cell = Border(left=thin, right=thin, top=thin, bottom=thin)

    # 1. Tiêu đề đơn vị & Biểu mẫu chứng từ
    ws.merge_cells("A1:D1")
    ws["A1"] = "NHÀ THUỐC ĐẠT CHUẨN GPP"
    ws["A1"].font = font_unit

    ws.merge_cells("E1:G1")
    ws["E1"] = "Mẫu số: BC-TK01"
    ws["E1"].font = font_sub
    ws["E1"].alignment = Alignment(horizontal="right")

    ws.merge_cells("A2:G2")
    ws["A2"] = "Địa chỉ: Quận Hai Bà Trưng, Hà Nội | Điện thoại: 024.3869.xxxx"
    ws["A2"].font = font_sub

    ws.merge_cells("A4:G4")
    ws["A4"] = "BÁO CÁO TỒN KHO VÀ ĐỊNH GIÁ DƯỢC PHẨM"
    ws["A4"].font = font_title
    ws["A4"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A5:G5")
    ws["A5"] = f"Ngày lập báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Người lập: Lê Hoàng Nam (Quản lý kho) | Nơi nhận: Chủ nhà thuốc & Kế toán"
    ws["A5"].font = font_sub
    ws["A5"].alignment = Alignment(horizontal="center")

    # 2. Tiêu đề cột bảng số liệu (Dòng 7)
    headers = ["STT", "Mã thuốc", "Tên thuốc", "Danh mục", "Đơn giá bán (VNĐ)", "Số lượng tồn", "Giá trị tồn kho (VNĐ)"]
    ws.append([])
    ws.append(headers)
    for col_idx in range(1, 8):
        cell = ws.cell(row=7, column=col_idx)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_cell
    ws.row_dimensions[7].height = 26

    # 3. Đổ dữ liệu chi tiết
    tong_so_luong = 0
    tong_gia_tri = Decimal("0")
    for idx, item in enumerate(inventory, start=1):
        sl = int(item.get("SoLuongTon") or 0)
        don_gia = Decimal(str(item.get("DonGiaBan") or 0))
        gia_tri = Decimal(str(item.get("GiaTriTonKho") or 0))
        tong_so_luong += sl
        tong_gia_tri += gia_tri

        row_idx = 7 + idx
        ws.append([
            idx,
            item["MaThuoc"],
            item["TenThuoc"],
            item.get("TenDanhMuc") or "-",
            float(don_gia),
            sl,
            float(gia_tri)
        ])
        for col_idx in range(1, 8):
            c = ws.cell(row=row_idx, column=col_idx)
            c.font = font_data
            c.border = border_cell
            if col_idx in (1, 2):
                c.alignment = Alignment(horizontal="center")
            elif col_idx in (5, 6, 7):
                c.alignment = Alignment(horizontal="right")
                c.number_format = "#,##0"

    # 4. Dòng Tổng cộng
    total_row = 8 + len(inventory)
    ws.append(["", "", "TỔNG CỘNG TOÀN KHO", "", "", tong_so_luong, float(tong_gia_tri)])
    for col_idx in range(1, 8):
        c = ws.cell(row=total_row, column=col_idx)
        c.font = font_bold
        c.fill = fill_total
        c.border = border_cell
        if col_idx in (6, 7):
            c.alignment = Alignment(horizontal="right")
            c.number_format = "#,##0"

    # 5. Khu vực ký xác nhận cuối trang
    sign_row = total_row + 2
    ws.merge_cells(start_row=sign_row, start_column=1, end_row=sign_row, end_column=3)
    ws.cell(row=sign_row, column=1, value="NGƯỜI LẬP BÁO CÁO").font = font_bold
    ws.cell(row=sign_row, column=1).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row, start_column=5, end_row=sign_row, end_column=7)
    ws.cell(row=sign_row, column=5, value="CHỦ NHÀ THUỐC / KẾ TOÁN DUYỆT").font = font_bold
    ws.cell(row=sign_row, column=5).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row + 1, start_column=1, end_row=sign_row + 1, end_column=3)
    ws.cell(row=sign_row + 1, column=1, value="(Ký, ghi rõ họ tên)").font = font_sub
    ws.cell(row=sign_row + 1, column=1).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row + 1, start_column=5, end_row=sign_row + 1, end_column=7)
    ws.cell(row=sign_row + 1, column=5, value="(Ký, đóng dấu xác nhận)").font = font_sub
    ws.cell(row=sign_row + 1, column=5).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row + 4, start_column=1, end_row=sign_row + 4, end_column=3)
    ws.cell(row=sign_row + 4, column=1, value="Lê Hoàng Nam").font = font_bold
    ws.cell(row=sign_row + 4, column=1).alignment = Alignment(horizontal="center")

    # Căn độ rộng các cột
    col_widths = {"A": 7, "B": 14, "C": 30, "D": 28, "E": 20, "F": 16, "G": 22}
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"BaoCao_TonKho_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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

@app.route("/expiry/export-excel")
def export_expiry_excel():
    """Xuất Báo cáo Cảnh báo Hạn sử dụng ra file Excel (.xlsx) chuẩn biểu mẫu thực tế."""
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

    wb = Workbook()
    ws = wb.active
    ws.title = "CanhBaoHanSuDung"

    font_unit = Font(name="Times New Roman", size=11, bold=True)
    font_sub = Font(name="Times New Roman", size=10, italic=True)
    font_title = Font(name="Times New Roman", size=15, bold=True)
    font_header = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Times New Roman", size=11)
    font_bold = Font(name="Times New Roman", size=11, bold=True)
    font_red = Font(name="Times New Roman", size=11, bold=True, color="B91C1C")
    font_amber = Font(name="Times New Roman", size=11, bold=True, color="B45309")
    fill_header = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
    fill_expired = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    fill_warning = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    thin = Side(border_style="thin", color="888888")
    border_cell = Border(left=thin, right=thin, top=thin, bottom=thin)

    # 1. Tiêu đề đơn vị & Biểu mẫu chứng từ
    ws.merge_cells("A1:E1")
    ws["A1"] = "NHÀ THUỐC ĐẠT CHUẨN GPP"
    ws["A1"].font = font_unit

    ws.merge_cells("F1:J1")
    ws["F1"] = "Mẫu số: BC-HSD02"
    ws["F1"].font = font_sub
    ws["F1"].alignment = Alignment(horizontal="right")

    ws.merge_cells("A2:J2")
    ws["A2"] = "Địa chỉ: Quận Hai Bà Trưng, Hà Nội | Điện thoại: 024.3869.xxxx"
    ws["A2"].font = font_sub

    ws.merge_cells("A4:J4")
    ws["A4"] = "BÁO CÁO KIỂM SOÁT & CẢNH BÁO THUỐC HẾT HẠN / SẮP HẾT HẠN (30 NGÀY)"
    ws["A4"].font = font_title
    ws["A4"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A5:J5")
    ws["A5"] = f"Ngày kiểm tra: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Người lập: Nguyễn Văn An (Dược sĩ) | Nơi nhận: Dược sĩ quầy & Chủ nhà thuốc"
    ws["A5"].font = font_sub
    ws["A5"].alignment = Alignment(horizontal="center")

    # 2. Tiêu đề cột bảng số liệu (Dòng 7)
    headers = [
        "STT", "Mã thuốc", "Tên thuốc", "Danh mục", "Số lô",
        "Ngày SX", "Hạn sử dụng", "SL nhập lô", "Nhà cung cấp", "Tình trạng"
    ]
    ws.append([])
    ws.append(headers)
    for col_idx in range(1, 11):
        cell = ws.cell(row=7, column=col_idx)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_cell
    ws.row_dimensions[7].height = 26

    # 3. Đổ dữ liệu các lô thuốc cảnh báo
    for idx, item in enumerate(expiry_list, start=1):
        so_ngay = item.get("SoNgayConLai") or 0
        is_expired = so_ngay < 0
        status_text = f"Đã hết hạn (Quá {-so_ngay} ngày)" if is_expired else f"Sắp hết hạn (Còn {so_ngay} ngày)"

        row_idx = 7 + idx
        ws.append([
            idx,
            item["MaThuoc"],
            item["TenThuoc"],
            item.get("TenDanhMuc") or "-",
            item["SoLo"],
            item["NSX"].strftime("%d/%m/%Y") if item.get("NSX") else "-",
            item["HSD"].strftime("%d/%m/%Y") if item.get("HSD") else "-",
            int(item.get("SoLuongThuocNhap") or 0),
            item.get("TenNCC") or "-",
            status_text
        ])
        for col_idx in range(1, 11):
            c = ws.cell(row=row_idx, column=col_idx)
            c.font = font_data
            c.border = border_cell
            if col_idx in (1, 2, 5, 6, 7):
                c.alignment = Alignment(horizontal="center")
            elif col_idx == 8:
                c.alignment = Alignment(horizontal="right")
                c.number_format = "#,##0"
            elif col_idx == 10:
                c.font = font_red if is_expired else font_amber
                c.fill = fill_expired if is_expired else fill_warning
                c.alignment = Alignment(horizontal="center")

    # 4. Khu vực ký xác nhận cuối trang
    sign_row = 9 + len(expiry_list)
    ws.merge_cells(start_row=sign_row, start_column=1, end_row=sign_row, end_column=4)
    ws.cell(row=sign_row, column=1, value="DƯỢC SĨ LẬP BÁO CÁO").font = font_bold
    ws.cell(row=sign_row, column=1).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row, start_column=7, end_row=sign_row, end_column=10)
    ws.cell(row=sign_row, column=7, value="CHỦ NHÀ THUỐC PHÊ DUYỆT XỬ LÝ").font = font_bold
    ws.cell(row=sign_row, column=7).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row + 1, start_column=1, end_row=sign_row + 1, end_column=4)
    ws.cell(row=sign_row + 1, column=1, value="(Ký, ghi rõ họ tên)").font = font_sub
    ws.cell(row=sign_row + 1, column=1).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row + 1, start_column=7, end_row=sign_row + 1, end_column=10)
    ws.cell(row=sign_row + 1, column=7, value="(Ký, đóng dấu xác nhận)").font = font_sub
    ws.cell(row=sign_row + 1, column=7).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=sign_row + 4, start_column=1, end_row=sign_row + 4, end_column=4)
    ws.cell(row=sign_row + 4, column=1, value="Nguyễn Văn An").font = font_bold
    ws.cell(row=sign_row + 4, column=1).alignment = Alignment(horizontal="center")

    col_widths = {"A": 6, "B": 12, "C": 26, "D": 24, "E": 15, "F": 14, "G": 14, "H": 14, "I": 28, "J": 26}
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"BaoCao_CanhBaoHSD_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
# ===========================================================================
# KIỂM TRA DỮ LIỆU ĐẦU VÀO & QUẢN LÝ 4 MỤC CON TRÊN /medicines
# ===========================================================================

INT_MAX = 2_147_483_647                    # giới hạn kiểu INT của MySQL
MONEY_MAX = Decimal("9999999999999.99")    # giới hạn DECIMAL(15,2)
CODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s.\-]{7,19}$")

VALID_TABS = ("thuoc", "lo-thuoc", "danh-muc", "nha-cung-cap")
ACTION_TAB_MAP = {
    "add_medicine": "thuoc",
    "update_medicine": "thuoc",
    "add_batch": "lo-thuoc",
    "update_batch": "lo-thuoc",
    "add_category": "danh-muc",
    "update_category": "danh-muc",
    "add_supplier": "nha-cung-cap",
    "update_supplier": "nha-cung-cap",
}


def set_tab_notice(tab, message, category="danger"):
    """Lưu thông báo gắn với đúng mục con (1, 2, 3 hoặc 4) để hiển thị ngay tại mục đó."""
    session["med_notice"] = {
        "tab": tab if tab in VALID_TABS else "thuoc",
        "message": message,
        "category": category,
    }


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


NAME_CHECKS = {
    "DANH_MUC": ("MaDanhMuc", "TenDanhMuc", "danh mục"),
    "NHA_CUNG_CAP": ("MaNCC", "TenNCC", "nhà cung cấp"),
}


def ensure_name_not_used(table, name, exclude_code=None):
    """Không cho hai mã KHÁC NHAU cùng mang một tên."""
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
            return (f'Lỗi trùng khóa chính: Mã danh mục "{rows[0]["MaDanhMuc"]}" đã tồn tại với tên "{rows[0]["TenDanhMuc"]}" '
                    f'(bạn vừa nhập tên "{ctx.get("ten_dm")}"). Hệ thống KHÔNG ghi đè dữ liệu cũ. '
                    f'Hãy dùng mã khác, chọn danh mục có sẵn, hoặc bấm "Sửa" ở bảng Danh mục bên dưới nếu muốn đổi tên.')
    if label == "NHA_CUNG_CAP":
        rows = query_db("SELECT MaNCC, TenNCC FROM NHA_CUNG_CAP WHERE MaNCC = %s", (ctx.get("ma_ncc"),))
        if rows:
            return (f'Lỗi trùng khóa chính: Mã nhà cung cấp "{rows[0]["MaNCC"]}" đã tồn tại với tên "{rows[0]["TenNCC"]}" '
                    f'(bạn vừa nhập tên "{ctx.get("ten_ncc")}"). Hệ thống KHÔNG ghi đè dữ liệu cũ. '
                    f'Hãy dùng mã khác, chọn nhà cung cấp có sẵn, hoặc bấm "Sửa" ở bảng Nhà cung cấp bên dưới.')
    if label == "THUOC":
        rows = query_db("SELECT MaThuoc, TenThuoc FROM THUOC WHERE MaThuoc = %s", (ctx.get("ma_thuoc"),))
        if rows:
            return (f'Lỗi trùng khóa chính: Mã thuốc "{rows[0]["MaThuoc"]}" đã tồn tại ("{rows[0]["TenThuoc"]}"). '
                    f'Hệ thống KHÔNG ghi đè dữ liệu cũ. Hãy dùng mã khác hoặc bấm "Sửa" ở bảng thuốc bên dưới.')
    if label == "LO_THUOC":
        return (f'Lỗi trùng khóa chính: Lô "{ctx.get("so_lo")}" của thuốc {ctx.get("ma_thuoc")} đã tồn tại. '
                f'Mỗi thuốc không được có hai lô cùng số lô; hãy dùng số lô khác hoặc bấm "Sửa" ở bảng lô thuốc.')
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
            return "Không thể xóa: thuốc này đã xuất hiện trong hóa đơn bán hàng hoặc còn dữ liệu liên quan."
        return "Không thể xóa: dữ liệu này đang được bảng khác sử dụng."
    if errno == 1406:
        return "Dữ liệu nhập quá dài so với độ dài cột trong cơ sở dữ liệu."
    if errno == 1048:
        return "Thiếu dữ liệu bắt buộc."
    if errno in (1264, 1292, 1366):
        return "Giá trị số hoặc ngày nằm ngoài phạm vi cho phép của cơ sở dữ liệu."
    return f"Lỗi cơ sở dữ liệu (mã {errno}): {exc}"


def commit_or_flash(statements, ctx, success_message, tab="thuoc"):
    ok, exc, label = run_transaction(statements)
    if ok:
        set_tab_notice(tab, success_message, "success")
        return True
    set_tab_notice(tab, explain_db_error(exc, label, ctx), "danger")
    return False


# ===========================================================================
# XỬ LÝ CÁC FORM TRÊN TRANG /medicines
# ===========================================================================

def resolve_category(form):
    """Chọn danh mục có sẵn HOẶC tạo danh mục mới (kèm bước INSERT nằm cùng transaction)."""
    new_ma = clean(form.get("ma_danh_muc_new"))
    new_ten = clean(form.get("ten_danh_muc_new"))
    if new_ma or new_ten:
        ma, ten = validate_category(new_ma, new_ten)
        ensure_name_not_used("DANH_MUC", ten, exclude_code=ma)
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
        ensure_name_not_used("NHA_CUNG_CAP", ten, exclude_code=ma)
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

    steps.append(("THUOC", """
        INSERT INTO THUOC (MaThuoc, TenThuoc, ThanhPhan, ChiDinh, DonGiaBan, SoLuongTon, MaDanhMuc)
        VALUES (%s, %s, %s, %s, %s, 0, %s)
    """, (ma_thuoc, ten, thanh_phan or None, chi_dinh or None, gia, ma_dm)))

    extra = f' và danh mục mới "{ten_dm}"' if ten_dm else ""
    return commit_or_flash(
        steps,
        {"ma_thuoc": ma_thuoc, "ma_dm": ma_dm, "ten_dm": ten_dm},
        f"Đã thêm thuốc [{ma_thuoc}]{extra}. Hãy sang mục '2. Quản lý Lô thuốc' để nhập lô hàng đầu tiên.",
        tab="thuoc"
    )


def handle_update_medicine(form):
    ma_thuoc = clean(form.get("ma_thuoc"))
    if not query_db("SELECT 1 AS ok FROM THUOC WHERE MaThuoc = %s", (ma_thuoc,)):
        raise ValueError(f'Thuốc "{ma_thuoc}" không tồn tại (có thể đã bị xóa). Hãy tải lại trang.')
    ten, thanh_phan, chi_dinh, gia = read_medicine_fields(form)
    ma_dm, ten_dm, steps = resolve_category(form)

    steps.append(("THUOC", """
        UPDATE THUOC
        SET TenThuoc = %s, ThanhPhan = %s, ChiDinh = %s, DonGiaBan = %s, MaDanhMuc = %s
        WHERE MaThuoc = %s
    """, (ten, thanh_phan or None, chi_dinh or None, gia, ma_dm, ma_thuoc)))

    return commit_or_flash(
        steps,
        {"ma_thuoc": ma_thuoc, "ma_dm": ma_dm, "ten_dm": ten_dm},
        f"Đã cập nhật thông tin thuốc [{ma_thuoc}].",
        tab="thuoc"
    )


def parse_batch_common_fields(form):
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
    return ma_thuoc, so_lo, so_luong, don_gia_nhap, nsx, hsd, ngay_nhap, ma_nv, ma_ncc, ten_ncc, steps


def handle_add_batch(form):
    (ma_thuoc, so_lo, so_luong, don_gia_nhap,
     nsx, hsd, ngay_nhap, ma_nv, ma_ncc, ten_ncc, steps) = parse_batch_common_fields(form)

    steps.append(("LO_THUOC", """
        INSERT INTO LO_THUOC (MaThuoc, SoLo, SoLuongThuocNhap, NSX, HSD, DonGiaNhap, NgayNhap, MaNCC, MaNV)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (ma_thuoc, so_lo, so_luong, nsx, hsd, don_gia_nhap, ngay_nhap, ma_ncc, ma_nv)))
    steps.append(("THUOC", """
        UPDATE THUOC SET SoLuongTon = COALESCE(SoLuongTon, 0) + %s WHERE MaThuoc = %s
    """, (so_luong, ma_thuoc)))

    extra = f' (đã tạo nhà cung cấp mới "{ten_ncc}")' if ten_ncc else ""
    return commit_or_flash(
        steps,
        {"ma_thuoc": ma_thuoc, "so_lo": so_lo, "ma_ncc": ma_ncc, "ten_ncc": ten_ncc},
        f"Nhập lô thành công cho thuốc {ma_thuoc} (số lô {so_lo}, +{so_luong} vào tồn kho){extra}.",
        tab="lo-thuoc"
    )


def handle_update_batch(form):
    """Cập nhật thông tin lô thuốc và tự động điều chỉnh chênh lệch tồn kho trong cùng 1 Transaction."""
    (ma_thuoc, so_lo, so_luong_moi, don_gia_nhap,
     nsx, hsd, ngay_nhap, ma_nv, ma_ncc, ten_ncc, supplier_steps) = parse_batch_common_fields(form)

    old_rows = query_db("SELECT SoLuongThuocNhap FROM LO_THUOC WHERE MaThuoc = %s AND SoLo = %s", (ma_thuoc, so_lo))
    if not old_rows:
        raise ValueError(f'Lô "{so_lo}" của thuốc {ma_thuoc} không tồn tại.')
    so_luong_cu = old_rows[0]["SoLuongThuocNhap"] or 0
    delta = so_luong_moi - so_luong_cu

    if delta < 0:
        ton_rows = query_db("SELECT COALESCE(SoLuongTon, 0) AS Ton FROM THUOC WHERE MaThuoc = %s", (ma_thuoc,))
        ton_hien_tai = ton_rows[0]["Ton"] if ton_rows else 0
        if ton_hien_tai + delta < 0:
            raise ValueError(
                f"Không thể giảm số lượng nhập từ {so_luong_cu} xuống {so_luong_moi}: "
                f"tồn kho hiện tại ({ton_hien_tai}) không đủ để trừ {abs(delta)} đơn vị."
            )

    steps = list(supplier_steps)
    steps.append(("LO_THUOC", """
        UPDATE LO_THUOC
        SET SoLuongThuocNhap = %s, NSX = %s, HSD = %s, DonGiaNhap = %s, NgayNhap = %s, MaNCC = %s, MaNV = %s
        WHERE MaThuoc = %s AND SoLo = %s
    """, (so_luong_moi, nsx, hsd, don_gia_nhap, ngay_nhap, ma_ncc, ma_nv, ma_thuoc, so_lo)))

    if delta != 0:
        steps.append(("THUOC", """
            UPDATE THUOC SET SoLuongTon = COALESCE(SoLuongTon, 0) + %s WHERE MaThuoc = %s
        """, (delta, ma_thuoc)))

    delta_txt = f" (điều chỉnh tồn kho {'+' if delta > 0 else ''}{delta})" if delta != 0 else ""
    return commit_or_flash(
        steps,
        {"ma_thuoc": ma_thuoc, "so_lo": so_lo, "ma_ncc": ma_ncc, "ten_ncc": ten_ncc},
        f"Đã cập nhật lô [{so_lo}] của thuốc [{ma_thuoc}]{delta_txt}.",
        tab="lo-thuoc"
    )


def handle_add_category(form):
    ma, ten = validate_category(clean(form.get("dm_ma")), clean(form.get("dm_ten")))
    ensure_name_not_used("DANH_MUC", ten, exclude_code=ma)
    steps = [("DANH_MUC", "INSERT INTO DANH_MUC (MaDanhMuc, TenDanhMuc) VALUES (%s, %s)", (ma, ten))]
    return commit_or_flash(steps, {"ma_dm": ma, "ten_dm": ten}, f'Đã thêm danh mục [{ma}] "{ten}".', tab="danh-muc")


def handle_update_category(form):
    ma, ten = validate_category(clean(form.get("dm_ma")), clean(form.get("dm_ten")))
    if not query_db("SELECT 1 AS ok FROM DANH_MUC WHERE MaDanhMuc = %s", (ma,)):
        raise ValueError(f'Danh mục "{ma}" không tồn tại.')
    ensure_name_not_used("DANH_MUC", ten, exclude_code=ma)
    steps = [("DANH_MUC", "UPDATE DANH_MUC SET TenDanhMuc = %s WHERE MaDanhMuc = %s", (ten, ma))]
    return commit_or_flash(steps, {"ma_dm": ma, "ten_dm": ten}, f'Đã cập nhật danh mục [{ma}] thành "{ten}".', tab="danh-muc")


def read_supplier_form(form):
    return validate_supplier(clean(form.get("ncc_ma")), clean(form.get("ncc_ten")),
                             clean(form.get("ncc_diachi")), clean(form.get("ncc_sdt")),
                             clean(form.get("ncc_email")))


def handle_add_supplier(form):
    ma, ten, diachi, sdt, email = read_supplier_form(form)
    ensure_name_not_used("NHA_CUNG_CAP", ten, exclude_code=ma)
    steps = [("NHA_CUNG_CAP",
              "INSERT INTO NHA_CUNG_CAP (MaNCC, TenNCC, Diachi, SDT, Email) VALUES (%s, %s, %s, %s, %s)",
              (ma, ten, diachi, sdt, email))]
    return commit_or_flash(steps, {"ma_ncc": ma, "ten_ncc": ten}, f'Đã thêm nhà cung cấp [{ma}] "{ten}".', tab="nha-cung-cap")


def handle_update_supplier(form):
    ma, ten, diachi, sdt, email = read_supplier_form(form)
    if not query_db("SELECT 1 AS ok FROM NHA_CUNG_CAP WHERE MaNCC = %s", (ma,)):
        raise ValueError(f'Nhà cung cấp "{ma}" không tồn tại.')
    ensure_name_not_used("NHA_CUNG_CAP", ten, exclude_code=ma)
    steps = [("NHA_CUNG_CAP",
              "UPDATE NHA_CUNG_CAP SET TenNCC = %s, Diachi = %s, SDT = %s, Email = %s WHERE MaNCC = %s",
              (ten, diachi, sdt, email, ma))]
    return commit_or_flash(steps, {"ma_ncc": ma, "ten_ncc": ten}, f'Đã cập nhật nhà cung cấp [{ma}] "{ten}".', tab="nha-cung-cap")


ACTIONS = {
    "add_medicine": handle_add_medicine,
    "update_medicine": handle_update_medicine,
    "add_batch": handle_add_batch,
    "update_batch": handle_update_batch,
    "add_category": handle_add_category,
    "update_category": handle_update_category,
    "add_supplier": handle_add_supplier,
    "update_supplier": handle_update_supplier,
}


@app.route("/medicines", methods=["GET", "POST"])
def manage_medicines():
    form = {}
    active_tab = clean(request.args.get("tab"))
    if active_tab not in VALID_TABS:
        active_tab = "thuoc"

    if request.method == "POST":
        form = request.form
        action = clean(form.get("action"))
        active_tab = ACTION_TAB_MAP.get(action, active_tab)
        handler = ACTIONS.get(action)
        if handler is None:
            set_tab_notice(active_tab, "Thao tác không hợp lệ.", "danger")
        else:
            try:
                if handler(form):
                    return redirect(url_for("manage_medicines", tab=active_tab))
            except ValueError as err:
                set_tab_notice(active_tab, str(err), "danger")
            except Exception as err:
                app.logger.exception("Lỗi khi xử lý /medicines")
                set_tab_notice(active_tab, f"Lỗi hệ thống: {err}", "danger")

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
    employees = query_db("SELECT MaNV, TenNV FROM NHAN_VIEN ORDER BY MaNV")
    medicines = query_db("""
        SELECT t.*, dm.TenDanhMuc
        FROM THUOC t
        LEFT JOIN DANH_MUC dm ON t.MaDanhMuc = dm.MaDanhMuc
        ORDER BY t.MaThuoc DESC
    """)
    batches = query_db("""
        SELECT lt.MaThuoc, t.TenThuoc, lt.SoLo, lt.SoLuongThuocNhap, lt.NSX, lt.HSD,
               lt.DonGiaNhap, lt.NgayNhap, lt.MaNCC, lt.MaNV, ncc.TenNCC, nv.TenNV,
               DATEDIFF(lt.HSD, CURDATE()) AS SoNgayConLai
        FROM LO_THUOC lt
        JOIN THUOC t ON lt.MaThuoc = t.MaThuoc
        LEFT JOIN NHA_CUNG_CAP ncc ON lt.MaNCC = ncc.MaNCC
        LEFT JOIN NHAN_VIEN nv ON lt.MaNV = nv.MaNV
        ORDER BY lt.NgayNhap DESC, lt.HSD
        LIMIT 200
    """)

    notice = session.pop("med_notice", None)

    return render_template(
        "medicines.html",
        categories=categories, suppliers=suppliers, employees=employees,
        medicines=medicines, batches=batches,
        form=form, today=date.today().isoformat(),
        active_tab=active_tab, notice=notice
    )


# ===========================================================================
# CÁC THAO TÁC XÓA (giữ nguyên đúng mục đang mở)
# ===========================================================================

@app.route("/medicines/delete/<string:ma_thuoc>", methods=["POST"])
def delete_medicine(ma_thuoc):
    steps = [
        ("LO_THUOC", "DELETE FROM LO_THUOC WHERE MaThuoc = %s", (ma_thuoc,)),
        ("THUOC", "DELETE FROM THUOC WHERE MaThuoc = %s", (ma_thuoc,)),
    ]
    commit_or_flash(steps, {"ma_thuoc": ma_thuoc}, f"Đã xóa thuốc mã {ma_thuoc} cùng các lô của thuốc.", tab="thuoc")
    return redirect(url_for("manage_medicines", tab="thuoc"))


@app.route("/categories/delete/<string:ma_dm>", methods=["POST"])
def delete_category(ma_dm):
    used = query_db("SELECT COUNT(*) AS n FROM THUOC WHERE MaDanhMuc = %s", (ma_dm,))[0]["n"]
    if used:
        set_tab_notice(
            "danh-muc",
            f"Không thể xóa danh mục {ma_dm}: đang có {used} thuốc thuộc danh mục này. "
            f"Hãy chuyển các thuốc sang danh mục khác trước.",
            "danger"
        )
    else:
        steps = [("DANH_MUC", "DELETE FROM DANH_MUC WHERE MaDanhMuc = %s", (ma_dm,))]
        commit_or_flash(steps, {"ma_dm": ma_dm}, f"Đã xóa danh mục {ma_dm}.", tab="danh-muc")
    return redirect(url_for("manage_medicines", tab="danh-muc"))


@app.route("/suppliers/delete/<string:ma_ncc>", methods=["POST"])
def delete_supplier(ma_ncc):
    used = query_db("SELECT COUNT(*) AS n FROM LO_THUOC WHERE MaNCC = %s", (ma_ncc,))[0]["n"]
    if used:
        set_tab_notice(
            "nha-cung-cap",
            f"Không thể xóa nhà cung cấp {ma_ncc}: đã có {used} lô thuốc nhập từ nhà cung cấp này.",
            "danger"
        )
    else:
        steps = [("NHA_CUNG_CAP", "DELETE FROM NHA_CUNG_CAP WHERE MaNCC = %s", (ma_ncc,))]
        commit_or_flash(steps, {"ma_ncc": ma_ncc}, f"Đã xóa nhà cung cấp {ma_ncc}.", tab="nha-cung-cap")
    return redirect(url_for("manage_medicines", tab="nha-cung-cap"))


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
            set_tab_notice("lo-thuoc", f'Lô "{so_lo}" của thuốc {ma_thuoc} không tồn tại.', "danger")
            return redirect(url_for("manage_medicines", tab="lo-thuoc"))

        cursor.execute("SELECT SoLuongTon FROM THUOC WHERE MaThuoc = %s FOR UPDATE", (ma_thuoc,))
        ton = (cursor.fetchone() or {}).get("SoLuongTon") or 0
        if ton < lot["SoLuongThuocNhap"]:
            connection.rollback()
            set_tab_notice(
                "lo-thuoc",
                f"Không thể xóa lô {so_lo}: tồn kho hiện tại ({ton}) ít hơn số lượng của lô "
                f"({lot['SoLuongThuocNhap']}), nghĩa là một phần hàng đã được bán. "
                f"Xóa lô sẽ làm tồn kho bị âm.",
                "danger"
            )
            return redirect(url_for("manage_medicines", tab="lo-thuoc"))

        cursor.execute("UPDATE THUOC SET SoLuongTon = SoLuongTon - %s WHERE MaThuoc = %s",
                       (lot["SoLuongThuocNhap"], ma_thuoc))
        cursor.execute("DELETE FROM LO_THUOC WHERE MaThuoc = %s AND SoLo = %s", (ma_thuoc, so_lo))
        connection.commit()
        set_tab_notice("lo-thuoc", f"Đã xóa lô {so_lo} của thuốc {ma_thuoc} và trừ {lot['SoLuongThuocNhap']} khỏi tồn kho.", "success")
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        set_tab_notice("lo-thuoc", explain_db_error(exc, "LO_THUOC", {}), "danger")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
    return redirect(url_for("manage_medicines", tab="lo-thuoc"))

@app.route("/invoice", methods=["GET", "POST"])
def create_invoice():
    import json
    from datetime import datetime

    # 1. KHI NGƯỜI DÙNG MỞ TRANG (GET): Tải dữ liệu thuốc, nhân viên, khách hàng lên form
    if request.method == "GET":
        # Lấy danh sách các thuốc còn hàng trong kho để bán
        medicines = query_db("""
            SELECT MaThuoc, TenThuoc, DonGiaBan, SoLuongTon 
            FROM THUOC 
            WHERE SoLuongTon > 0 
            ORDER BY TenThuoc ASC
        """)
        
        # Lấy danh sách nhân viên để chọn người bán
        employees = query_db("SELECT MaNV, TenNV, VaiTro FROM NHAN_VIEN ORDER BY TenNV ASC")
        
        # Lấy danh sách khách hàng
        customers = query_db("SELECT MaKH, TenKH, SDT FROM KHACH_HANG ORDER BY TenKH ASC")
        
        # Tự động sinh mã hóa đơn mới (VD: HD001, HD002...)
        last_hd = query_db("SELECT MaHD FROM HOA_DON ORDER BY MaHD DESC LIMIT 1")
        if last_hd and last_hd[0]["MaHD"].startswith("HD"):
            try:
                curr_num = int(last_hd[0]["MaHD"][2:])
                ma_hd_moi = f"HD{curr_num + 1:03d}"
            except ValueError:
                ma_hd_moi = f"HD{int(datetime.now().timestamp()) % 10000:04d}"
        else:
            ma_hd_moi = "HD001"

        return render_template(
            "invoice.html",
            medicines=medicines,
            employees=employees,
            customers=customers,
            ma_hd_moi=ma_hd_moi
        )

    # 2. KHI BẤM NÚT "LƯU & XUẤT HÓA ĐƠN" (POST): Thực hiện TRANSACTION trong CSDL
    elif request.method == "POST":
        ma_hd = request.form.get("ma_hd")
        ten_nv_input = request.form.get("ten_nv", "").strip()
        ma_kh_input = request.form.get("ma_kh", "").strip()
        ten_kh_input = request.form.get("ten_kh", "Khách vãng lai").strip()
        sdt_kh_input = request.form.get("sdt_kh", "").strip()
        cart_raw = request.form.get("cart_data", "[]")

        try:
            cart = json.loads(cart_raw)
        except Exception:
            cart = []

        if not cart:
            flash("Đơn hàng chưa có sản phẩm nào để xuất bán!", "danger")
            return redirect(url_for("create_invoice"))

        # Tính tổng tiền hóa đơn = tổng (số lượng * đơn giá)
        tong_tien = sum(item["soLuong"] * item["donGia"] for item in cart)

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # BẮT ĐẦU TRANSACTION: Đảm bảo tính toàn vẹn (ACID)
            conn.start_transaction()

            # XỬ LÝ 1: Tìm mã nhân viên từ tên người dùng nhập vào
            cursor.execute("SELECT MaNV FROM NHAN_VIEN WHERE TenNV LIKE %s OR MaNV = %s LIMIT 1", (f"%{ten_nv_input}%", ten_nv_input))
            nv_row = cursor.fetchone()
            ma_nv = nv_row["MaNV"] if nv_row else "NV01"

            # XỬ LÝ 2: Định danh khách hàng
            ma_kh = None
            clean_sdt = re.sub(r'[\s.\-]', '', sdt_kh_input) if sdt_kh_input else ""

            # 2.1. Chọn khách hàng đã có trong hệ thống (kể cả Khách vãng lai nếu chọn trong danh mục)
            if ma_kh_input and ma_kh_input != "NEW":
                cursor.execute("SELECT MaKH, TenKH FROM KHACH_HANG WHERE MaKH = %s LIMIT 1", (ma_kh_input,))
                kh_exist = cursor.fetchone()
                if not kh_exist:
                    raise Exception("Khách hàng đã chọn không tồn tại trong hệ thống. Vui lòng tải lại trang!")
                ma_kh = kh_exist["MaKH"]

            # 2.2. Thêm khách hàng mới (chọn "+ Thêm khách hàng mới")
            elif ma_kh_input == "NEW":
                if not ten_kh_input:
                    raise Exception("Vui lòng nhập họ tên khách hàng mới!")

                # SĐT là bắt buộc đối với khách mới
                if not clean_sdt:
                    raise Exception("Số điện thoại là thông tin bắt buộc khi thêm khách hàng mới (để phân biệt khách hàng khi trùng tên)!")

                if not clean_sdt.isdigit() or len(clean_sdt) < 8 or len(clean_sdt) > 15:
                    raise Exception(f'Số điện thoại "{sdt_kh_input}" không hợp lệ. Vui lòng nhập từ 8 đến 15 chữ số!')

                # Kiểm tra SĐT DUY NHẤT: Tên có thể trùng, nhưng mỗi khách chỉ sử dụng 1 SĐT
                cursor.execute("SELECT MaKH, TenKH FROM KHACH_HANG WHERE SDT = %s LIMIT 1", (clean_sdt,))
                phone_match = cursor.fetchone()
                if phone_match:
                    raise Exception(
                        f'Số điện thoại "{clean_sdt}" đã được đăng ký bởi khách hàng "{phone_match["TenKH"]}" '
                        f'(mã {phone_match["MaKH"]}). Mỗi khách hàng chỉ được dùng 1 số điện thoại duy nhất. '
                        f'Vui lòng chọn khách hàng này từ danh sách hoặc kiểm tra lại SĐT!'
                    )

                # Sinh mã khách hàng mới tăng dần an toàn (bằng số nguyên lớn nhất)
                cursor.execute("SELECT MaKH FROM KHACH_HANG WHERE MaKH LIKE 'KH%'")
                all_kh = cursor.fetchall()
                max_num = 0
                for row in all_kh:
                    raw_id = row.get("MaKH", "")
                    digits = re.findall(r'\d+', raw_id)
                    if digits:
                        try:
                            num = int(digits[-1])
                            if num > max_num:
                                max_num = num
                        except ValueError:
                            pass
                ma_kh = f"KH{max_num + 1:02d}"

                # Thêm khách hàng mới vào CSDL (cho phép trùng tên, nhưng SĐT là duy nhất)
                cursor.execute("""
                    INSERT INTO KHACH_HANG (MaKH, TenKH, SDT) 
                    VALUES (%s, %s, %s)
                """, (ma_kh, ten_kh_input, clean_sdt))

            else:
                raise Exception("Vui lòng chọn khách hàng từ danh sách hoặc chọn '+ Thêm khách hàng mới'!")
            # BƯỚC 1: Kiểm tra lại tồn kho tức thời trong DB trước khi bán
            for item in cart:
                cursor.execute("SELECT SoLuongTon, TenThuoc FROM THUOC WHERE MaThuoc = %s", (item["maThuoc"],))
                row = cursor.fetchone()
                if not row or row["SoLuongTon"] < item["soLuong"]:
                    raise Exception(f"Thuốc '{row['TenThuoc'] if row else item['maThuoc']}' trong kho không đủ để xuất bán!")

            # BƯỚC 2: Thêm mới hóa đơn vào bảng HOA_DON
            cursor.execute("""
                INSERT INTO HOA_DON (MaHD, NgayBan, TongTien, MaNV, MaKH)
                VALUES (%s, NOW(), %s, %s, %s)
            """, (ma_hd, tong_tien, ma_nv, ma_kh))

            # BƯỚC 3: Thêm từng món vào CHI_TIET_HOA_DON và TRỪ TỒN KHO ở THUOC
            for item in cart:
                # Ghi chi tiết hóa đơn
                cursor.execute("""
                    INSERT INTO CHI_TIET_HOA_DON (MaHD, MaThuoc, SoLuongBan)
                    VALUES (%s, %s, %s)
                """, (ma_hd, item["maThuoc"], item["soLuong"]))

                # Cập nhật giảm số lượng tồn kho
                cursor.execute("""
                    UPDATE THUOC 
                    SET SoLuongTon = SoLuongTon - %s 
                    WHERE MaThuoc = %s
                """, (item["soLuong"], item["maThuoc"]))

            # BƯỚC 4: Nếu mọi thao tác đều thành công -> COMMIT xác nhận lưu vĩnh viễn
            conn.commit()
            flash(f"Lập hóa đơn [{ma_hd}] thành công! Tổng tiền: {tong_tien:,.0f} VNĐ (Đã trừ tồn kho)", "success")

        except Exception as e:
            # NẾU CÓ BẤT KỲ LỖI NÀO -> ROLLBACK HỦY TOÀN BỘ, KHÔNG ĐỂ KHO BỊ LỆCH
            if conn:
                conn.rollback()
            flash(f"Lỗi khi lập hóa đơn: {str(e)}", "danger")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

        return redirect(url_for("create_invoice"))
    
if __name__ == "__main__":
    app.run(debug=True)