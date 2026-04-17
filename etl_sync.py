"""
etl_sync.py — Unified ETL: GSheets → Supabase
Hợp nhất pipeline: Đội GSheets (Farm 126) + Master GSheets (157/195) → DB

Usage:
  python etl_sync.py                    # Incremental (chỉ thêm mới)
  python etl_sync.py --full-reload      # Xoá tất cả + INSERT lại
  python etl_sync.py --farm 126         # Chỉ chạy cho 1 farm
  python etl_sync.py --farm 126 --full-reload
"""

import argparse, json, time, sys, os, re
from datetime import datetime

import pandas as pd
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────
# CONFIG: Data Sources — Master GSheets + Team GSheets
# ──────────────────────────────────────────────────────────────
ETL_SOURCES = {
    # ── Farm 126: Đọc Master (data cũ từ 08/2025) + Teams (data mới T3-T4/2026) ──
    # Master: "BÁO CÁO TỔNG HỢP" có ~6500 rows từ 08/2025 → 03/2026
    # Teams: 6 đội có data mới nhất tới 04/2026, bổ sung phần Master chưa cập nhật
    "Farm 126": {
        "farm_code": "Farm 126",
        "type": "both",  # Đọc cả Master lẫn Teams, dedup qua ON CONFLICT
        "master": "1FJFVAUnDLp4C2w6n4le4iVNPUVdhYandy8NQaf2bcB0",
        "fact_cong_sheet": "Công (fact)",
        "fact_vt_sheet": "Vật Tư (fact)",
        "teams": [
            {
                "id": "1K7IxcAeZ_Qe82mLSDo2nM8PaZxdqe52TNPsgCpCY8aQ",
                "name": "Đội 1",
                "sheets": [
                    {"name": "Công (fact)", "type": "nk"},
                    {"name": "Vật Tư (fact)", "type": "vt"},
                ]
            },
            {
                "id": "1tMl4yhmStVjGsVhem3ICgfw9W10JVly9Y49uPPSFytA",
                "name": "Đội 2",
                "sheets": [
                    {"name": "Công (fact)", "type": "nk"},
                    {"name": "Vật Tư (fact)", "type": "vt"},
                ]
            },
            {
                "id": "17rQY5n--JLht6KuU3Vmg7lhqgzxpommcYeCc7jQJVf4",
                "name": "Đội BVTV",
                "sheets": [
                    {"name": "Công (fact)", "type": "nk"},
                    {"name": "Vật Tư (fact)", "type": "vt"},
                ]
            },
            {
                "id": "1by_0MyQb1pRPjTsxxE7z0BjIRzkfCOrApbVwP5_d8UE",
                "name": "Đội Điện Nước",
                "sheets": [
                    {"name": "Công (fact)", "type": "nk"},
                    {"name": "Vật Tư (fact)", "type": "vt"},
                ]
            },
            {
                "id": "1WSD8mYp0jbhqTh-c3bZo638ihDnpcVugapdC1HdHViM",
                "name": "Đội Cơ Giới",
                "sheets": [
                    {"name": "Công (fact)", "type": "nk"},
                    {"name": "Vật Tư (fact)", "type": "vt"},
                ]
            },
            {
                "id": "1TYcbDTZLJjPdBSvf_Qo_rNe14myq3gUoWvXR6_U2W0s",
                "name": "Đội Thu Hoạch",
                "sheets": [
                    {"name": "Công (fact)", "type": "nk"},
                    {"name": "Vật Tư (fact)", "type": "vt"},
                ]
            },
        ]
    },

    # ── Farm 157: Master (data 03/2025→03/2026) + Teams (data mới T4/2026) ──
    "Farm 157": {
        "farm_code": "Farm 157",
        "type": "both",
        "master": "1dA8HIOEUDtp_ip6Dg0Yz7sCF9I90KMKiycixF0jus04",
        "fact_cong_sheet": "Công (fact)",
        "fact_vt_sheet": None,  # Tự tìm
        "teams": [
            {
                "id": "1sNjRPcDJkSoiVZNRHIeu_8VinA16KnwdwZCpLBwJ4EA",
                "name": "Đội 1",
                "sheets": [
                    {"name": "Nhập công hàng ngày", "type": "nk"},
                    {"name": "Nhập vật tư hàng ngày", "type": "vt"},
                ]
            },
            {
                "id": "1NQY7K6QVgHnvx0SEay-lCRqgDn7qJaY7XD290HnKI5s",
                "name": "Đội 2",
                "sheets": [
                    {"name": "Nhập công hàng ngày", "type": "nk"},
                    {"name": "Nhập vật tư hàng ngày", "type": "vt"},
                ]
            },
            {
                "id": "12BUt2pyxomDYo71dVmbT6i_mIMv_ERMVnCb6O6r5ddw",
                "name": "Đội BVTV",
                "sheets": [
                    {"name": "Nhập công hàng ngày", "type": "nk"},
                    {"name": "Nhập vật tư hàng ngày", "type": "vt"},
                ]
            },
            {
                "id": "1m8t584ZNV_SfrpmzUoNEllW06nfhnwHBD-sopFZOCX8",
                "name": "Đội Điện Nước",
                "sheets": [
                    {"name": "Nhập công hàng ngày", "type": "nk"},
                    {"name": "Nhập vật tư hàng ngày", "type": "vt"},
                ]
            },
            {
                "id": "17jUY6Ep_JreMPvphXhyzi50CX7nuvnLhIdhWkY4CHWc",
                "name": "Đội Thu Hoạch",
                "sheets": [
                    {"name": "Nhập công hàng ngày", "type": "nk"},
                    {"name": "Nhập vật tư hàng ngày", "type": "vt"},
                ]
            },
            {
                "id": "1m1OFHE2foQ6y-pOxzusnHwokxoL3qT1jpH5r28khaLc",
                "name": "Đội Cơ Giới",
                "sheets": [
                    {"name": "Nhập công hàng ngày", "type": "nk"},
                    {"name": "Nhập vật tư hàng ngày", "type": "vt"},
                ]
            },
        ]
    },

    # ── Farm 195: Đọc từ Master GSheet (Vườn Ươm) ──
    "Farm 195": {
        "farm_code": "Farm 195",
        "type": "master",
        "master": "1V9ThLCFTtLKuFNeNUkBgmRKzW3MpeLnsOPnapDoAn4Y",
        "fact_cong_sheet": "Công (fact)",
        "fact_vt_sheet": "Vật Tư (fact)",
    },
}


# ──────────────────────────────────────────────────────────────
# AUTH: Google OAuth + Supabase Pool
# ──────────────────────────────────────────────────────────────
def get_google_client():
    """Xác thực Google Sheets qua OAuth token.json, tự refresh nếu hết hạn."""
    token_path = os.path.join(os.path.dirname(__file__), "token.json")
    with open(token_path) as f:
        tok = json.load(f)

    creds = Credentials(
        token=tok["token"],
        refresh_token=tok["refresh_token"],
        token_uri=tok["token_uri"],
        client_id=tok["client_id"],
        client_secret=tok["client_secret"],
        scopes=tok["scopes"],
    )

    if creds.expired or not creds.valid:
        print("🔄 Đang refresh Google token...")
        creds.refresh(Request())
        with open(token_path, "w") as f:
            json.dump({
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes),
                "universe_domain": "googleapis.com",
                "account": "",
                "expiry": creds.expiry.isoformat() + "Z" if creds.expiry else "",
            }, f)
        print("✅ Token refreshed")

    return gspread.authorize(creds)


def get_db_pool():
    """Tạo Supabase connection pool từ .streamlit/secrets.toml."""
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    cfg = {}

    if os.path.exists(secrets_path):
        section = None
        with open(secrets_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                elif "=" in line and section == "supabase":
                    key, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                    cfg[key.strip()] = val

    if not cfg:
        load_dotenv(override=True)
        db_url = os.getenv("SUPABASE_URL")
        if not db_url:
            print("❌ Không tìm thấy DB config trong .streamlit/secrets.toml hoặc .env")
            sys.exit(1)
        pool = SimpleConnectionPool(1, 5, dsn=db_url, sslmode="require",
                                    options="-c search_path=public", connect_timeout=10)
        print("✅ Kết nối Supabase (env)")
        return pool

    pool = SimpleConnectionPool(
        1, 5,
        host=cfg["host"], port=cfg.get("port", 6543),
        database=cfg.get("database", "postgres"),
        user=cfg["user"], password=cfg["password"],
        sslmode="require",
        options="-c search_path=public",
        connect_timeout=10,
    )
    print(f"✅ Kết nối Supabase: {cfg['host']}")
    return pool


# ──────────────────────────────────────────────────────────────
# DIM LOADING: Load toàn bộ dim tables 1 lần
# ──────────────────────────────────────────────────────────────
def load_dim_maps(conn):
    """Load tất cả dim tables vào dictionaries."""
    maps = {}
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Farm: farm_code → farm_id
        cur.execute("SELECT farm_id, farm_code FROM dim_farm")
        maps["farm"] = {r["farm_code"].strip(): r["farm_id"] for r in cur.fetchall()}
        print(f"  dim_farm: {len(maps['farm'])} entries")

        # Đội: doi_code → doi_id (tất cả farms)
        cur.execute("SELECT doi_id, doi_code FROM dim_doi")
        maps["doi"] = {r["doi_code"].strip(): r["doi_id"] for r in cur.fetchall()}
        # Thêm alias phổ biến
        doi_alias = {
            "Điện nước": "Đội Điện Nước", "Điện Nước": "Đội Điện Nước",
            "ĐIỆN NƯỚC": "Đội Điện Nước", "ĐIện Nước": "Đội Điện Nước",
            "Đội Điện nước": "Đội Điện Nước", "Đội Điên Nước": "Đội Điện Nước",
            "Đội điện nước": "Đội Điện Nước",
            "Cơ giới": "Đội Cơ Giới", "Cờ Giới 157": "Đội Cơ Giới",
            "Cơ Giới": "Đội Cơ Giới",
            "Thu hoạch": "Đội Thu Hoạch", "Thu Hoạch": "Đội Thu Hoạch",
            "Thu hoạch 157": "Đội Thu Hoạch",
            "BVTV": "Đội BVTV",
            "NT1": "Đội NT1", "Đội 1A": "Đội NT1", "Đội 1B": "Đội NT1",
            "NT2": "Đội NT2", "Đội 2A": "Đội NT2", "Đội 2B": "Đội NT2",
            "NT1+NT2": "Đội NT1",  # Gán mặc định
            "NT3+NT4": "Đội NT1",  # Gán mặc định
            "Vườn Ươm": "Đội Vườn Ươm",
            "XDG": "XĐG",
        }
        for alias, real in doi_alias.items():
            if real in maps["doi"] and alias not in maps["doi"]:
                maps["doi"][alias] = maps["doi"][real]
        print(f"  dim_doi: {len(maps['doi'])} entries (incl. aliases)")

        # Lô: lo_code → lo_id (tất cả farms) + case-insensitive
        cur.execute("SELECT lo_id, lo_code, farm_id FROM dim_lo")
        maps["lo"] = {}
        maps["lo_ci"] = {}  # case-insensitive: lower(lo_code) → lo_id
        maps["lo_by_farm"] = {}  # (farm_id, lo_code) → lo_id
        maps["lo_by_farm_ci"] = {}  # (farm_id, lower(lo_code)) → lo_id
        for r in cur.fetchall():
            code = r["lo_code"].strip()
            maps["lo"][code] = r["lo_id"]
            maps["lo_ci"][code.lower()] = r["lo_id"]
            maps["lo_by_farm"][(r["farm_id"], code)] = r["lo_id"]
            maps["lo_by_farm_ci"][(r["farm_id"], code.lower())] = r["lo_id"]
        print(f"  dim_lo: {len(maps['lo'])} entries")

        # Công Việc: LOWER(ten_cong_viec) → cong_viec_id + ma_cv → cong_viec_id
        cur.execute("SELECT cong_viec_id, ma_cv, ten_cong_viec, cong_doan FROM dim_cong_viec")
        maps["cv"] = {}       # lower(ten_cv) → cong_viec_id
        maps["cv_by_ma"] = {} # ma_cv → cong_viec_id (fallback)
        maps["cv_max_seq"] = {}  # group → max sequence number (for auto-gen)
        for r in cur.fetchall():
            if r["ten_cong_viec"]:
                key = r["ten_cong_viec"].strip().lower()
                if key not in maps["cv"]:  # giữ entry đầu tiên
                    maps["cv"][key] = r["cong_viec_id"]
            if r["ma_cv"]:
                maps["cv_by_ma"][r["ma_cv"].strip()] = r["cong_viec_id"]
                # Track max seq per group cho auto-gen mã
                m = re.match(r"(\d+)-(\d+)", r["ma_cv"].strip())
                if m:
                    grp, seq = int(m.group(1)), int(m.group(2))
                    maps["cv_max_seq"][grp] = max(maps["cv_max_seq"].get(grp, 0), seq)
        print(f"  dim_cong_viec: {len(maps['cv'])} by name, {len(maps['cv_by_ma'])} by ma_cv")

        # Vật Tư: ma_vat_tu → vat_tu_id
        cur.execute("SELECT vat_tu_id, ma_vat_tu, ten_vat_tu FROM dim_vat_tu")
        maps["vt"] = {}
        maps["vt_by_name"] = {}  # lowercase key!
        for r in cur.fetchall():
            if r["ma_vat_tu"]:
                maps["vt"][r["ma_vat_tu"].strip()] = r["vat_tu_id"]
            if r["ten_vat_tu"]:
                maps["vt_by_name"][r["ten_vat_tu"].strip().lower()] = r["vat_tu_id"]
        print(f"  dim_vat_tu: {len(maps['vt'])} entries (code), {len(maps['vt_by_name'])} (name, case-insensitive)")

    return maps


# ──────────────────────────────────────────────────────────────
# TRANSFORM: GSheet row → DB record
# ──────────────────────────────────────────────────────────────
def normalize_text(val):
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()


def parse_number(val):
    """Chuyển chuỗi GSheet ('1,234.56' hoặc '1.234,56') → float."""
    if pd.isna(val) or val is None:
        return 0.0
    s = str(val).strip().replace(" ", "")
    if not s:
        return 0.0
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_date(val):
    """Chuyển chuỗi ngày GSheet → YYYY-MM-DD. Trả None nếu lỗi hoặc ngày bất thường."""
    if pd.isna(val) or val is None:
        return None
    s = normalize_text(val)
    if not s:
        return None
    try:
        if "/" in s or "-" in s:
            dt = pd.to_datetime(s, dayfirst=True)
            # Bỏ qua ngày quá xa tương lai (> 30 ngày from now)
            if dt > pd.Timestamp.now() + pd.Timedelta(days=30):
                return None
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def detect_header_row(data, max_scan=5):
    """Tìm header row bằng cách kiểm tra các từ khóa đặc trưng."""
    keywords = {"mã cv", "ngày", "số công", "vật tư", "lô", "đội", "thành tiền", "klcv", "sl", "đơn giá"}
    for i, row in enumerate(data[:max_scan]):
        row_lower = " ".join(str(c).lower().strip() for c in row)
        matches = sum(1 for kw in keywords if kw in row_lower)
        if matches >= 3:
            return i
    return 0  # Mặc định row 0


def map_columns(header):
    """Map tiêu đề cột GSheet → tên cột chuẩn.
    Hỗ trợ cả header Master GSheet lẫn header Team GSheet.
    """
    mapping = {}
    for i, col in enumerate(header):
        c = str(col).lower().strip()
        # Bỏ newline trong header (một số đội có header nhiều dòng)
        c = c.replace("\n", " ").replace("\r", " ")

        if c in ("stt", "#", ""):
            continue
        elif "mã cv" in c or "mã công việc" in c:
            mapping[i] = "ma_cv"
        elif c == "lô 2" or c == "lô của đội":
            mapping[i] = "lo_code"
        elif "lô" in c and "lô 2" not in c and "lo_raw" not in mapping.values():
            # "lô", "lô làm" → lô thực, nhưng KHÔNG match "lô 2"
            mapping[i] = "lo_raw"
        elif c == "vườn":
            # Farm 157 teams: "Vườn" chứa mã lô thật (3A, 3B, 7A, 8A...)
            if "lo_raw" not in mapping.values():
                mapping[i] = "lo_raw"
        elif "đội thực hiện" in c or "tên đội" in c or "nhóm" in c or c == "đội":
            mapping[i] = "doi_name"
        elif c == "ngày" or ("ngày" in c and "tháng" in c):
            if "ngay" not in mapping.values():
                mapping[i] = "ngay"
        elif "hạng mục" in c or "công đoạn" in c or "giai đoạn" in c:
            mapping[i] = "hang_muc"
        elif "tên công việc" in c or "tên cv" in c:
            # Team sheets: "tên công việc" = tên hạng mục công việc
            if "hang_muc" not in mapping.values():
                mapping[i] = "hang_muc"
        elif "loại công" in c:
            mapping[i] = "loai_cong"
        elif "số công" in c or c == "công" or "ca máy" in c or "số giờ" in c:
            if "so_cong" not in mapping.values():
                mapping[i] = "so_cong"
        elif "klcv" in c or "khối lượng" in c:
            mapping[i] = "klcv"
        elif "thành tiền" in c or "t.tiền" in c or "số tiền" in c:
            if "thanh_tien" not in mapping.values():
                mapping[i] = "thanh_tien"
        elif c == "vật tư" or "tên vật tư" in c:
            mapping[i] = "ten_vt"
        elif "mã vt" in c or "mã vật tư" in c:
            mapping[i] = "ma_vt"
        elif c == "sl" or "số lượng" in c:
            mapping[i] = "so_luong"
        elif "đơn giá" in c:
            mapping[i] = "don_gia"
        elif "đvt" in c or "đơn vị" in c:
            continue
        elif "định mức" in c:
            mapping[i] = "dinh_muc"
        elif "loại vật tư" in c:
            continue
    return mapping


def _map_value(val, lookup, missing_set, fallback_lookup=None):
    """Tìm khớp val trong lookup dict, ghi nhận missing."""
    v = normalize_text(val)
    if not v:
        return None
    result = lookup.get(v)
    if result:
        return result
    if fallback_lookup:
        result = fallback_lookup.get(v)
        if result:
            return result
    missing_set.add(v)
    return None


def _resolve_lo(lo_raw, lo_code_val, farm_id, maps, missing_lo):
    """Resolve lô ID với ưu tiên: lo_raw (lô thật) > lo_code (Lô 2), case-insensitive fallback.
    Trả (lo_id, lo_display) — lo_display dùng cho missing tracking.
    """
    lo_id = None

    # 1) Thử lo_raw (cột Lô) — thường là lô thật (3A, 1B...)
    if lo_raw:
        lo_id = maps["lo"].get(lo_raw)
        if not lo_id:
            lo_id = maps["lo_by_farm"].get((farm_id, lo_raw))
        if not lo_id:  # case-insensitive fallback
            lo_id = maps["lo_ci"].get(lo_raw.lower())
        if not lo_id:
            lo_id = maps["lo_by_farm_ci"].get((farm_id, lo_raw.lower()))

    # 2) Fallback: lo_code (cột Lô 2) — thường là nhóm đội (NT1+NT2)
    if not lo_id and lo_code_val:
        lo_id = maps["lo"].get(lo_code_val)
        if not lo_id:
            lo_id = maps["lo_by_farm"].get((farm_id, lo_code_val))
        if not lo_id:
            lo_id = maps["lo_ci"].get(lo_code_val.lower())
        if not lo_id:
            lo_id = maps["lo_by_farm_ci"].get((farm_id, lo_code_val.lower()))

    # 3) Ghi missing
    if not lo_id:
        lo_display = lo_raw or lo_code_val
        if lo_display:
            missing_lo.add(lo_display)

    return lo_id


def _resolve_cv(ma_cv, hang_muc, loai_cong, maps, conn, missing_cv):
    """Resolve công việc ID. Thử mã CV trước, rồi tên (case-insensitive), auto-insert nếu mới.
    
    Returns: cong_viec_id hoặc None
    """
    cv_id = None

    # 1) Thử mã CV (team sheets thường dùng mã)
    if ma_cv:
        cv_id = maps["cv_by_ma"].get(ma_cv)
        if cv_id:
            return cv_id

    # 2) Thử tên hạng mục (master sheets thường dùng tên)
    name = normalize_text(hang_muc)
    if not name:
        # Nếu không có cả ma_cv lẫn hang_muc → missing
        if ma_cv:
            missing_cv.add(ma_cv)
        return None

    key = name.lower()
    cv_id = maps["cv"].get(key)
    if cv_id:
        return cv_id

    # 3) Auto-insert vào dim_cong_viec nếu tên mới
    loai = normalize_text(loai_cong).lower()
    suffix = "k" if "kho" in loai else "n"
    grp = 99
    seq = maps["cv_max_seq"].get(grp, 0) + 1
    maps["cv_max_seq"][grp] = seq
    new_ma_cv = f"{grp}-{seq:02d}{suffix}"

    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO dim_cong_viec (ma_cv, ten_cong_viec, loai_cong)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (ma_cv) DO NOTHING
                   RETURNING cong_viec_id""",
                (new_ma_cv, name, loai_cong)
            )
            row = cur.fetchone()
            record = {
                "ngay": nk_date_str,
                "nguoi_thuc_hien": nguoi_thuc_hien,
                "cong_viec_raw": cv_raw,
                "lo_raw": lo_raw,
                "so_cong": so_cong,
                "klcv": klcv,
                "dinh_muc": dinh_muc,
                "ti_le_display": ti_le_display,
                "don_gia": don_gia,
                "thanh_tien": thanh_tien,
                "is_ho_tro": is_ho_tro,
                "loai_cong": "Ngày"
            }
            if row:
                cv_id = row[0]
                maps["cv"][key] = cv_id
                maps["cv_by_ma"][new_ma_cv] = cv_id
                conn.commit()
                return cv_id
            else:
                conn.rollback()
                missing_cv.add(name)
                return None
    except Exception:
        conn.rollback()
        missing_cv.add(name)
        return None


# ──────────────────────────────────────────────────────────────
# PROCESSOR
# ──────────────────────────────────────────────────────────────
class ETLProcessor:
    def __init__(self, conn, dim_maps):
        self.conn = conn
        self.maps = dim_maps
        self.nk_buffer = []
        self.vt_buffer = []
        self.missing = {"lo": set(), "doi": set(), "cv": set(), "vt": set()}
        self.stats = {
            "nk_total": 0, "nk_skipped": 0,
            "vt_total": 0, "vt_skipped": 0,
        }

    # ── Xử lý Sheet Nhật Ký (NK) — Master hoặc Team ──
    def process_cong_sheet(self, data, farm_id, source_name, override_doi=None):
        """Xử lý sheet Công/NK (cả Master lẫn Team).
        Hỗ trợ cả 2 kiểu mapping: mã CV (code) lẫn hạng mục (tên).
        override_doi: Nếu set, dùng tên này thay cho cột 'Đội Thực Hiện' trong GSheet.
        """
        header_idx = detect_header_row(data)
        header = data[header_idx]
        col_map = map_columns(header)

        mapped_names = set(col_map.values())

        # Cần ít nhất 1 cột CV identifier + 1 cột số liệu
        has_cv_col = "ma_cv" in mapped_names or "hang_muc" in mapped_names
        has_num_col = "so_cong" in mapped_names or "thanh_tien" in mapped_names
        if not has_cv_col or not has_num_col:
            print(f"  ⚠️ {source_name}: Thiếu cột cần thiết (mapped: {mapped_names})")
            return

        # Pre-resolve override_doi nếu có
        override_doi_id = None
        if override_doi:
            override_doi_id = _map_value(override_doi, self.maps["doi"], self.missing["doi"])
            if override_doi_id:
                print(f"  🔄 Override đội: tất cả rows → '{override_doi}'")

        rows = data[header_idx + 1:]
        print(f"  📥 {source_name}: {len(rows)} dòng (header row {header_idx})")

        for row in rows:
            self.stats["nk_total"] += 1

            # Đọc giá trị theo col_map
            vals = {}
            for idx, target in col_map.items():
                if idx < len(row):
                    vals[target] = row[idx]

            # Ngày
            ngay = parse_date(vals.get("ngay"))
            if not ngay:
                self.stats["nk_skipped"] += 1
                continue

            # FK mapping — Lô (ưu tiên lo_raw > lo_code, CI fallback)
            lo_raw = normalize_text(vals.get("lo_raw", ""))
            lo_code_val = normalize_text(vals.get("lo_code", ""))
            lo_id = _resolve_lo(lo_raw, lo_code_val, farm_id, self.maps, self.missing["lo"])

            # FK mapping — Đội (override nếu đọc từ team sheet)
            if override_doi_id:
                doi_id = override_doi_id
            else:
                doi_name = normalize_text(vals.get("doi_name", ""))
                doi_id = _map_value(doi_name, self.maps["doi"], self.missing["doi"])

            # FK mapping — Công việc (mã CV hoặc tên hạng mục)
            ma_cv = normalize_text(vals.get("ma_cv", ""))
            hang_muc = normalize_text(vals.get("hang_muc", ""))
            loai_cong_val = normalize_text(vals.get("loai_cong", ""))
            cv_id = _resolve_cv(ma_cv, hang_muc, loai_cong_val,
                                self.maps, self.conn, self.missing["cv"])

            # Số liệu
            so_cong = parse_number(vals.get("so_cong"))
            klcv = parse_number(vals.get("klcv"))
            thanh_tien = parse_number(vals.get("thanh_tien"))
            don_gia = parse_number(vals.get("don_gia", 0))
            dinh_muc = parse_number(vals.get("dinh_muc", 0))

            # Tự tính thanh_tien nếu = 0 nhưng có don_gia và so_cong
            if thanh_tien == 0 and don_gia > 0 and so_cong > 0:
                thanh_tien = so_cong * don_gia

            # Tính ti_le_display
            ti_le_display = None
            if so_cong > 0 and dinh_muc > 0:
                ns_thuc = klcv / so_cong
                ti_le_display = (ns_thuc / dinh_muc) * 100

            # Bỏ qua dòng rỗng
            if so_cong == 0 and klcv == 0 and thanh_tien == 0:
                self.stats["nk_skipped"] += 1
                continue

            # RULE: NK phải có hạng mục (cv_id), nếu không → skip
            if not cv_id:
                self.stats["nk_skipped"] += 1
                continue

            # RULE: Bỏ lô lỗi nhập (12, 12.00)
            lo_check = lo_raw or lo_code_val
            if lo_check in ("12", "12.00"):
                self.stats["nk_skipped"] += 1
                continue

            # is_khoan
            loai_cong = normalize_text(vals.get("loai_cong", "")).lower()
            is_khoan = "kho" in loai_cong  # "Khoán" → True

            self.nk_buffer.append((
                farm_id, ngay, doi_id, lo_id, cv_id,
                so_cong, klcv, dinh_muc, ti_le_display, thanh_tien, is_khoan, False
            ))

    # ── Xử lý Sheet Vật Tư (VT) — Master hoặc Team ──
    def process_vattu_sheet(self, data, farm_id, source_name, override_doi=None):
        """Xử lý sheet Vật Tư (cả Master lẫn Team)."""
        header_idx = detect_header_row(data)
        header = data[header_idx]
        col_map = map_columns(header)

        mapped_names = set(col_map.values())
        if "thanh_tien" not in mapped_names and "so_luong" not in mapped_names:
            print(f"  ⚠️ {source_name}: Thiếu cột VT cần thiết (mapped: {mapped_names})")
            return

        rows = data[header_idx + 1:]
        print(f"  📥 {source_name}: {len(rows)} dòng (header row {header_idx})")

        for row in rows:
            self.stats["vt_total"] += 1

            vals = {}
            for idx, target in col_map.items():
                if idx < len(row):
                    vals[target] = row[idx]

            ngay = parse_date(vals.get("ngay"))
            if not ngay:
                self.stats["vt_skipped"] += 1
                continue

            # Lô mapping (ưu tiên lo_raw > lo_code, CI fallback)
            lo_raw = normalize_text(vals.get("lo_raw", ""))
            lo_code_val = normalize_text(vals.get("lo_code", ""))
            lo_id = _resolve_lo(lo_raw, lo_code_val, farm_id, self.maps, self.missing["lo"])

            # Công việc (VT giữ lại dù thiếu hạng mục — khác NK)
            ma_cv = normalize_text(vals.get("ma_cv", ""))
            hang_muc = normalize_text(vals.get("hang_muc", ""))
            cv_id = _resolve_cv(ma_cv, hang_muc, "",
                                self.maps, self.conn, self.missing["cv"])

            # Vật tư: thử mã VT trước, rồi tên VT (case-insensitive)
            vt_code = normalize_text(vals.get("ma_vt", ""))
            vt_name = normalize_text(vals.get("ten_vt", ""))
            vt_id = None
            if vt_code:
                vt_id = _map_value(vt_code, self.maps["vt"], self.missing["vt"])
            if not vt_id and vt_name:
                vt_key = vt_name.lower()
                vt_id = self.maps["vt_by_name"].get(vt_key)
                if not vt_id:
                    self.missing["vt"].add(vt_name)

            so_luong = parse_number(vals.get("so_luong"))
            don_gia = parse_number(vals.get("don_gia"))
            thanh_tien = parse_number(vals.get("thanh_tien"))

            # Tự tính thanh_tien nếu = 0
            if thanh_tien == 0 and so_luong > 0 and don_gia > 0:
                thanh_tien = so_luong * don_gia

            if thanh_tien == 0 and so_luong == 0:
                self.stats["vt_skipped"] += 1
                continue

            # RULE: Bỏ lô lỗi nhập (12, 12.00)
            lo_check = lo_raw or lo_code_val
            if lo_check in ("12", "12.00"):
                self.stats["vt_skipped"] += 1
                continue

            # RULE: Bỏ VT outlier — thanh_tien > 100 triệu VND/record
            # (Nguyên nhân: nhập sai đơn giá hoặc lẫn đơn mua hàng lô lớn)
            VT_OUTLIER_THRESHOLD = 100_000_000
            if thanh_tien > VT_OUTLIER_THRESHOLD:
                self.stats["vt_skipped"] += 1
                vt_label = vt_name or vt_code or "?"
                if not hasattr(self, '_vt_outlier_logged'):
                    self._vt_outlier_logged = set()
                key = f"{vt_label}|{ngay}"
                if key not in self._vt_outlier_logged:
                    self._vt_outlier_logged.add(key)
                continue

            self.vt_buffer.append((
                farm_id, lo_id, cv_id, vt_id,
                ngay, so_luong, don_gia, thanh_tien
            ))

    # ── INSERT Methods ──
    def insert_incremental(self):
        """INSERT ... ON CONFLICT DO NOTHING — chỉ thêm mới."""
        insert_nk = """
            INSERT INTO fact_nhat_ky_san_xuat (
                farm_id, ngay, doi_id, lo_id, cong_viec_id,
                so_cong, klcv, dinh_muc, ti_le_display, thanh_tien, is_ho_tro
            ) VALUES %s
            ON CONFLICT ON CONSTRAINT uq_nk_natural_key DO NOTHING
        """

        insert_vt = """
            INSERT INTO fact_vat_tu (
                farm_id, lo_id, cong_viec_id, vat_tu_id,
                ngay, so_luong, don_gia, thanh_tien
            ) VALUES %s
            ON CONFLICT ON CONSTRAINT uq_vt_natural_key DO NOTHING
        """

        new_nk = new_vt = 0
        try:
            with self.conn.cursor() as cur:
                if self.nk_buffer:
                    vals = [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], False)
                            for r in self.nk_buffer]
                    before = self._count_rows(cur, "fact_nhat_ky_san_xuat")
                    psycopg2.extras.execute_values(cur, insert_nk, vals, page_size=500)
                    after = self._count_rows(cur, "fact_nhat_ky_san_xuat")
                    new_nk = after - before

                if self.vt_buffer:
                    before = self._count_rows(cur, "fact_vat_tu")
                    psycopg2.extras.execute_values(cur, insert_vt, self.vt_buffer, page_size=500)
                    after = self._count_rows(cur, "fact_vat_tu")
                    new_vt = after - before

                self.conn.commit()

            print(f"\n✅ Nhật Ký: {new_nk} mới / {len(self.nk_buffer)} tổng ({len(self.nk_buffer) - new_nk} trùng)")
            print(f"✅ Vật Tư: {new_vt} mới / {len(self.vt_buffer)} tổng ({len(self.vt_buffer) - new_vt} trùng)")

        except Exception as e:
            self.conn.rollback()
            print(f"❌ Lỗi INSERT: {e}")
            raise

    def full_reload(self, farm_ids):
        """Xoá dữ liệu cũ của các farm, rồi insert lại + dedup."""
        try:
            with self.conn.cursor() as cur:
                ph = ",".join(["%s"] * len(farm_ids))
                cur.execute(f"DELETE FROM fact_nhat_ky_san_xuat WHERE farm_id IN ({ph})", farm_ids)
                del_nk = cur.rowcount
                cur.execute(f"DELETE FROM fact_vat_tu WHERE farm_id IN ({ph})", farm_ids)
                del_vt = cur.rowcount
                print(f"🗑️ Đã xoá: {del_nk} NK + {del_vt} VT")

                insert_nk = """
                    INSERT INTO fact_nhat_ky_san_xuat (
                        farm_id, ngay, doi_id, lo_id, cong_viec_id,
                        so_cong, klcv, dinh_muc, ti_le_display, thanh_tien, is_ho_tro
                    ) VALUES %s
                    ON CONFLICT ON CONSTRAINT uq_nk_natural_key DO NOTHING
                """
                insert_vt = """
                    INSERT INTO fact_vat_tu (
                        farm_id, lo_id, cong_viec_id, vat_tu_id,
                        ngay, so_luong, don_gia, thanh_tien
                    ) VALUES %s
                    ON CONFLICT ON CONSTRAINT uq_vt_natural_key DO NOTHING
                """
                if self.nk_buffer:
                    vals = [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], False)
                            for r in self.nk_buffer]
                    psycopg2.extras.execute_values(cur, insert_nk, vals, page_size=500)
                if self.vt_buffer:
                    psycopg2.extras.execute_values(cur, insert_vt, self.vt_buffer, page_size=500)

                self.conn.commit()
            print(f"✅ Full Reload: {len(self.nk_buffer)} NK + {len(self.vt_buffer)} VT inserted")

            # Dedup: loại bỏ duplicate dựa trên natural key (NULL-safe)
            self._dedup()

        except Exception as e:
            self.conn.rollback()
            print(f"❌ Lỗi full reload: {e}")
            raise

    def _dedup(self):
        """Loại bỏ duplicate rows sau insert (NULL-safe)."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM fact_nhat_ky_san_xuat
                    WHERE nhat_ky_id NOT IN (
                        SELECT MIN(nhat_ky_id)
                        FROM fact_nhat_ky_san_xuat
                        GROUP BY farm_id, ngay, COALESCE(doi_id, -1), COALESCE(lo_id, -1),
                                 cong_viec_id, so_cong, klcv, thanh_tien
                    )
                """)
                dup_nk = cur.rowcount

                cur.execute("""
                    DELETE FROM fact_vat_tu
                    WHERE vat_tu_fact_id NOT IN (
                        SELECT MIN(vat_tu_fact_id)
                        FROM fact_vat_tu
                        GROUP BY farm_id, ngay, COALESCE(lo_id, -1), COALESCE(cong_viec_id, -1),
                                 COALESCE(vat_tu_id, -1), so_luong, don_gia, thanh_tien
                    )
                """)
                dup_vt = cur.rowcount

                self.conn.commit()

                if dup_nk or dup_vt:
                    print(f"🧹 Dedup: xoá {dup_nk} NK + {dup_vt} VT trùng lặp")
                else:
                    print("✅ Không có duplicate")

        except Exception as e:
            self.conn.rollback()
            print(f"⚠️ Lỗi dedup (non-critical): {e}")

    def _count_rows(self, cur, table):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]

    def print_summary(self):
        print(f"\n{'='*50}")
        print("📊 THỐNG KÊ")
        print(f"{'='*50}")
        print(f"  NK: {self.stats['nk_total']} tổng, {self.stats['nk_skipped']} bỏ qua, {len(self.nk_buffer)} hợp lệ")
        print(f"  VT: {self.stats['vt_total']} tổng, {self.stats['vt_skipped']} bỏ qua, {len(self.vt_buffer)} hợp lệ")

        for key, vals in self.missing.items():
            if vals:
                display = sorted(list(vals))[:15]
                extra = f" (+{len(vals)-15} more)" if len(vals) > 15 else ""
                print(f"  ⚠️ Missing {key.upper()}: {display}{extra}")


# ──────────────────────────────────────────────────────────────
# GSheet Helper: Mở workbook với retry
# ──────────────────────────────────────────────────────────────
def open_gsheet_with_retry(gc, doc_id, retries=3):
    """Mở GSheet workbook, retry nếu bị rate limit."""
    for attempt in range(retries):
        try:
            wb = gc.open_by_key(doc_id)
            return wb
        except gspread.exceptions.APIError as e:
            if "429" in str(e):
                wait = 15 * (attempt + 1)
                print(f"  ⏳ Rate limit, chờ {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ❌ API Error: {e}")
                return None
        except Exception as e:
            print(f"  ❌ Lỗi mở GSheet: {e}")
            return None
    return None


def read_sheet_data(wb, sheet_name):
    """Đọc dữ liệu sheet, trả về list[list] hoặc None."""
    try:
        ws = wb.worksheet(sheet_name)
        data = ws.get_all_values()
        return data if data else None
    except gspread.exceptions.WorksheetNotFound:
        return None
    except Exception as e:
        print(f"  ❌ Lỗi đọc sheet '{sheet_name}': {e}")
        return None


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ETL: GSheets → Supabase (Unified)")
    parser.add_argument("--full-reload", action="store_true", help="Xoá hết + INSERT lại")
    parser.add_argument("--farm", type=str, help="Chỉ chạy cho 1 farm (VD: 126, 157, 195)")
    args = parser.parse_args()

    print("=" * 55)
    print(f"🚀 ETL SYNC — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Mode: {'FULL RELOAD' if args.full_reload else 'INCREMENTAL'}")
    if args.farm:
        print(f"   Farm: {args.farm}")
    print("=" * 55)

    # Filter sources
    sources = ETL_SOURCES
    if args.farm:
        farm_key = f"Farm {args.farm}"
        if farm_key not in sources:
            print(f"❌ Farm '{args.farm}' không tồn tại. Có: {list(sources.keys())}")
            sys.exit(1)
        sources = {farm_key: sources[farm_key]}

    # Connect
    print("\n📡 Khởi tạo kết nối...")
    gc = get_google_client()
    pool = get_db_pool()
    conn = pool.getconn()

    print("\n📦 Load Dimension Tables...")
    dim_maps = load_dim_maps(conn)

    processor = ETLProcessor(conn, dim_maps)
    processed_farm_ids = []

    for farm_label, source in sources.items():
        print(f"\n{'='*55}")
        print(f"🏠 {farm_label}")
        print(f"{'='*55}")

        farm_code = source["farm_code"]
        farm_id = dim_maps["farm"].get(farm_code)
        if not farm_id:
            print(f"  ❌ Không tìm thấy farm_id cho '{farm_code}' trong dim_farm!")
            continue
        processed_farm_ids.append(farm_id)

        # ── Routing: Teams vs Master vs Both ──
        if source["type"] == "teams":
            _process_teams(gc, processor, source, farm_id, farm_label)
        elif source["type"] == "both":
            # Đọc Master trước (data cũ đầy đủ), rồi Teams (bổ sung data mới)
            print("  📋 Mode: Master + Teams (combined)")
            _process_master(gc, processor, source, farm_id, farm_label)
            time.sleep(3)
            _process_teams(gc, processor, source, farm_id, farm_label)
        else:
            _process_master(gc, processor, source, farm_id, farm_label)

        time.sleep(3)  # Delay giữa các farm tránh rate limit

    # Summary
    processor.print_summary()

    # Insert
    if not processor.nk_buffer and not processor.vt_buffer:
        print("\n⚠️ Không có dữ liệu nào để insert!")
    else:
        print(f"\n{'='*55}")
        print("💾 CHUYỂN DỮ LIỆU VÀO SUPABASE")
        print(f"{'='*55}")

        if args.full_reload:
            processor.full_reload(processed_farm_ids)
        else:
            processor.insert_incremental()

    # Final verify
    _print_final_verify(conn)

    pool.putconn(conn)
    pool.closeall()
    print(f"\n✅ HOÀN TẤT — {datetime.now().strftime('%H:%M:%S')}")


def _process_teams(gc, processor, source, farm_id, farm_label):
    """Xử lý Farm 126: đọc trực tiếp từ GSheet các đội."""
    teams = source.get("teams", [])
    print(f"  📋 {len(teams)} đội cần xử lý")

    for team in teams:
        team_name = team["name"]
        doc_id = team["id"]
        print(f"\n  📂 Đội: {team_name}...")

        wb = open_gsheet_with_retry(gc, doc_id)
        if not wb:
            print(f"  ❌ Không mở được file của {team_name}, bỏ qua.")
            continue

        try:
            print(f"  ✅ \"{wb.title}\"")
        except Exception:
            pass

        for sheet_info in team["sheets"]:
            sheet_name = sheet_info["name"]
            sheet_type = sheet_info["type"]

            data = read_sheet_data(wb, sheet_name)
            if not data:
                print(f"    ⏭️ Sheet '{sheet_name}' không tìm thấy hoặc rỗng")
                continue

            tag = f"{farm_label}/{team_name}/{sheet_name}"
            if sheet_type == "nk":
                processor.process_cong_sheet(data, farm_id, tag, override_doi=team_name)
            elif sheet_type == "vt":
                processor.process_vattu_sheet(data, farm_id, tag, override_doi=team_name)

        time.sleep(2)  # Delay giữa các đội tránh rate limit


def _process_master(gc, processor, source, farm_id, farm_label):
    """Xử lý Farm 157/195: đọc từ Master GSheet."""
    doc_id = source["master"]
    print(f"  📂 Đang mở GSheet: {doc_id}...")

    wb = open_gsheet_with_retry(gc, doc_id)
    if not wb:
        print(f"  ❌ Không thể mở GSheet cho {farm_label}, bỏ qua.")
        return

    try:
        print(f"  ✅ \"{wb.title}\"")
    except Exception:
        pass

    # Tìm và xử lý sheet Công (fact)
    cong_sheet_name = source.get("fact_cong_sheet")
    if cong_sheet_name:
        data = read_sheet_data(wb, cong_sheet_name)
        if data:
            processor.process_cong_sheet(data, farm_id, f"{farm_label}/{cong_sheet_name}")
        else:
            print(f"  ⚠️ Không tìm thấy sheet '{cong_sheet_name}'")
            # Thử tìm tự động
            for ws in wb.worksheets():
                if "công" in ws.title.lower() and "fact" in ws.title.lower():
                    print(f"  🔎 Tìm thấy sheet thay thế: '{ws.title}'")
                    data = ws.get_all_values()
                    if data:
                        processor.process_cong_sheet(data, farm_id, f"{farm_label}/{ws.title}")
                    break
        time.sleep(2)

    # Tìm và xử lý sheet Vật Tư (fact)
    vt_sheet_name = source.get("fact_vt_sheet")
    if vt_sheet_name:
        data = read_sheet_data(wb, vt_sheet_name)
        if data:
            processor.process_vattu_sheet(data, farm_id, f"{farm_label}/{vt_sheet_name}")
        else:
            print(f"  ⚠️ Không tìm thấy sheet '{vt_sheet_name}'")
            for ws in wb.worksheets():
                if "vật tư" in ws.title.lower() and "fact" in ws.title.lower():
                    print(f"  🔎 Tìm thấy: '{ws.title}'")
                    data = ws.get_all_values()
                    if data:
                        processor.process_vattu_sheet(data, farm_id, f"{farm_label}/{ws.title}")
                    break
    else:
        # Thử tìm tự động sheet VT
        print(f"  🔎 Tìm tự động sheet Vật Tư...")
        try:
            for ws in wb.worksheets():
                title_lower = ws.title.lower()
                if ("vật tư" in title_lower and "fact" in title_lower) or \
                   "nhập vật tư" in title_lower:
                    print(f"  🔎 Tìm thấy: '{ws.title}'")
                    data = ws.get_all_values()
                    if data:
                        processor.process_vattu_sheet(data, farm_id, f"{farm_label}/{ws.title}")
                    break
        except Exception as e:
            print(f"  ❌ Lỗi tìm tự động VT: {e}")


def _print_final_verify(conn):
    """In bảng verify cuối cùng: coverage lô, date range."""
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT f.farm_code, 
                    COUNT(*) as nk_rows, 
                    COUNT(nk.lo_id) as nk_lo_ok,
                    MIN(nk.ngay)::text as min_date, 
                    MAX(nk.ngay)::text as max_date
                FROM fact_nhat_ky_san_xuat nk
                JOIN dim_farm f ON f.farm_id = nk.farm_id
                GROUP BY f.farm_code
                ORDER BY f.farm_code
            """)
            rows = cur.fetchall()

            if rows:
                print(f"\n{'='*55}")
                print("📊 VERIFY DATA")
                print(f"{'='*55}")
                print(f"  {'Farm':<12} {'NK rows':>8} {'Lô OK%':>8} {'Từ':>12} {'Đến':>12}")
                print(f"  {'-'*52}")
                for r in rows:
                    pct = round(100.0 * r["nk_lo_ok"] / r["nk_rows"], 1) if r["nk_rows"] > 0 else 0
                    print(f"  {r['farm_code']:<12} {r['nk_rows']:>8} {pct:>7.1f}% {r['min_date']:>12} {r['max_date']:>12}")
    except Exception as e:
        print(f"  ⚠️ Lỗi verify: {e}")


if __name__ == "__main__":
    main()
