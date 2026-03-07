import os
import pandas as pd
import unidecode
from datetime import datetime
from sqlalchemy import create_engine, text
import toml
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

print("=" * 80)
print("🚀 FULL LOAD (ROBUST LOCAL) — Tự động tìm Header & Map Cột".center(80))
print("=" * 80)

# ==============================================================================
# XÁC THỰC GOOGLE SHEETS LOCAL
# ==============================================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def authenticate_google_sheets():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Đang mở trình duyệt để xác thực Google...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"❌ Lỗi xác thực OAuth: {e}")
                raise SystemExit
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
    return gspread.authorize(creds)

gc = authenticate_google_sheets()
print("\n✅ Xác thực Google Sheets thành công\n")

# ==============================================================================
# CẤU HÌNH VÀ KẾT NỐI DB (Từ Streamlit Secrets)
# ==============================================================================
FARM_SHEETS = {
    "Farm 126": "https://docs.google.com/spreadsheets/d/1FJFVAUnDLp4C2w6n4le4iVNPUVdhYandy8NQaf2bcB0/edit",
    "Farm 157": "https://docs.google.com/spreadsheets/d/1dA8HIOEUDtp_ip6Dg0Yz7sCF9I90KMKiycixF0jus04/edit",
    "Farm 195": "https://docs.google.com/spreadsheets/d/1q1aEV1ZPSIhF4lPIoJ7FrAlUGC-Q3nvreh6bGIWdxZQ/edit",
}

def get_db_connection_string():
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    with open(secrets_path, "r", encoding="utf-8") as f:
        secrets = toml.load(f)["supabase"]
    return f"postgresql://{secrets['user']}:{secrets['password']}@{secrets['host']}:{secrets['port']}/{secrets['database']}"

engine = create_engine(get_db_connection_string())
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
print("✅ Kết nối Supabase thành công\n")


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def clean_col(name):
    """Làm sạch tên cột: Bỏ dấu, in thường, xóa khoảng trắng thừa, thay bằng _"""
    return (unidecode.unidecode(str(name))
            .lower().strip()
            .replace(" ", "_").replace(".", "")
            .replace("/", "_").replace("(", "").replace(")", ""))

def get_val(row, *cols):
    """Trả về giá trị của cột đầu tiên tìm thấy và có dữ liệu."""
    for col in cols:
        if col in row.index:
            v = str(row[col]).strip()
            if v and v.lower() != "nan":
                return v
    return ""

def to_numeric_col(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").str.strip(),
                errors="coerce"
            ).fillna(0)
    return df

def normalize(s):
    return str(s).strip().lower() if s else ""

def find_header_and_data(rows, required_keywords):
    """Quét 10 dòng đầu để tìm dòng Header thực sự bằng các từ khóa"""
    if len(rows) < 2: return None, []
    
    for i in range(min(10, len(rows))):
        clean_row = [clean_col(c) for c in rows[i]]
        # Nếu dòng hiện tại chứa ít nhất 2 keyword thiết yếu (như ngay, ma_cv, lo)
        matches = sum(1 for kw in required_keywords if any(kw in c for c in clean_row))
        if matches >= 2:
            return clean_row, rows[i+1:]
            
    return None, []

def read_sheet_robust(url, sheet_name, keywords):
    """Đọc sheet và sử dụng logic tìm Header động"""
    sheet_id = url.split("/d/")[1].split("/")[0]
    ws = gc.open_by_key(sheet_id).worksheet(sheet_name)
    rows = ws.get_all_values()
    
    headers, data = find_header_and_data(rows, keywords)
    if not headers or not data:
        return pd.DataFrame()
        
    df = pd.DataFrame(data, columns=headers)
    # Loại bỏ các dòng hoàn toàn trống
    df = df.dropna(how='all')
    # Loại bỏ các cột không có tên (rỗng) - đây là fix triệt để cho Farm 157
    df = df.loc[:, (df.columns != "") & ~df.columns.str.startswith("unnamed")]
    return df

# ==============================================================================
# STEP 1: Load dim tables → lookup dicts
# ==============================================================================
print("📥 Đang load dim tables từ Supabase...")

with engine.connect() as conn:
    df_farm = pd.read_sql("SELECT farm_id, farm_code FROM dim_farm", conn)
    df_lo   = pd.read_sql("SELECT lo_id, lo_code, farm_id FROM dim_lo", conn)
    df_doi  = pd.read_sql("SELECT doi_id, doi_code, farm_id FROM dim_doi", conn)
    df_cv   = pd.read_sql("SELECT cong_viec_id, ma_cv, ten_cong_viec FROM dim_cong_viec", conn)
    df_vt   = pd.read_sql("SELECT vat_tu_id, ten_vat_tu, dvt FROM dim_vat_tu", conn)

farm_lookup = {normalize(r.farm_code): r.farm_id for _, r in df_farm.iterrows()}
lo_lookup   = {(r.farm_id, normalize(r.lo_code)): r.lo_id for _, r in df_lo.iterrows()}
doi_lookup  = {(r.farm_id, normalize(r.doi_code)): r.doi_id for _, r in df_doi.iterrows()}

cv_by_ma_cv = {normalize(r.ma_cv): r.cong_viec_id for _, r in df_cv.iterrows() if r.ma_cv and str(r.ma_cv).strip()}
cv_by_name  = {normalize(r.ten_cong_viec): r.cong_viec_id for _, r in df_cv.iterrows() if r.ten_cong_viec}
vt_lookup   = {(normalize(r.ten_vat_tu), normalize(r.dvt)): r.vat_tu_id for _, r in df_vt.iterrows()}

print(f"   Farm: {len(farm_lookup)} | Lô: {len(lo_lookup)} | Đội: {len(doi_lookup)}")
print(f"   Công việc (ma_cv): {len(cv_by_ma_cv)} | (ten_cv): {len(cv_by_name)}")
print(f"   Vật tư: {len(vt_lookup)}\n")

# ==============================================================================
# UPSERT HELPERS
# ==============================================================================
def upsert_dim_cong_viec(conn, ma_cv_raw, ten_cv, cong_doan):
    ten_cv = ten_cv.strip()
    cong_doan = (cong_doan or "").strip()
    if ma_cv_raw and ma_cv_raw.strip():
        existing = conn.execute(text(
            "SELECT cong_viec_id FROM dim_cong_viec WHERE TRIM(ma_cv) = :ma"
        ), {"ma": ma_cv_raw.strip()}).scalar()
        if existing: return existing

    existing = conn.execute(text(
        "SELECT cong_viec_id FROM dim_cong_viec WHERE LOWER(TRIM(ten_cong_viec)) = LOWER(:ten)"
    ), {"ten": ten_cv}).scalar()
    if existing: return existing

    ma_cv_insert = ma_cv_raw.strip() if (ma_cv_raw and ma_cv_raw.strip()) else f"AUTO-{ten_cv[:30]}"
    row = conn.execute(text("""
        INSERT INTO dim_cong_viec (ma_cv, ten_cong_viec, cong_doan, created_at, updated_at)
        VALUES (:ma, :ten, :cd, NOW(), NOW())
        ON CONFLICT (ma_cv) DO UPDATE SET updated_at = NOW()
        RETURNING cong_viec_id
    """), {"ma": ma_cv_insert, "ten": ten_cv, "cd": cong_doan}).fetchone()
    return row[0] if row else None

def upsert_dim_vat_tu(conn, ten_vt, dvt_raw, loai_vt):
    ten_vt  = ten_vt.strip()
    dvt_val = dvt_raw.strip() if dvt_raw and dvt_raw.strip() else "—"
    loai_vt = (loai_vt or "").strip()

    existing = conn.execute(text("""
        SELECT vat_tu_id FROM dim_vat_tu
        WHERE LOWER(TRIM(ten_vat_tu)) = LOWER(:ten) AND TRIM(dvt) = :dvt
    """), {"ten": ten_vt, "dvt": dvt_val}).scalar()
    if existing: return existing

    row = conn.execute(text("""
        INSERT INTO dim_vat_tu (ten_vat_tu, dvt, loai_vat_tu, created_at, updated_at)
        VALUES (:ten, :dvt, :loai, NOW(), NOW())
        ON CONFLICT (ten_vat_tu, dvt) DO UPDATE SET updated_at = NOW()
        RETURNING vat_tu_id
    """), {"ten": ten_vt, "dvt": dvt_val, "loai": loai_vt}).fetchone()
    return row[0] if row else None

def upsert_dim_lo(conn, lo_code, farm_id, lo_type="Lô thực"):
    lo_code = lo_code.strip()
    row = conn.execute(text("""
        INSERT INTO dim_lo (lo_code, farm_id, lo_type, is_active, created_at, updated_at)
        VALUES (:code, :fid, :ltype, TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING
        RETURNING lo_id
    """), {"code": lo_code, "fid": farm_id, "ltype": lo_type}).fetchone()
    if row: return row[0]
    return conn.execute(text("SELECT lo_id FROM dim_lo WHERE TRIM(lo_code) = :code AND farm_id = :fid"), {"code": lo_code, "fid": farm_id}).scalar()

def upsert_dim_doi(conn, doi_code, farm_id):
    doi_code = doi_code.strip()
    row = conn.execute(text("""
        INSERT INTO dim_doi (doi_code, farm_id, is_active, created_at, updated_at)
        VALUES (:code, :fid, TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING
        RETURNING doi_id
    """), {"code": doi_code, "fid": farm_id}).fetchone()
    if row: return row[0]
    return conn.execute(text("SELECT doi_id FROM dim_doi WHERE TRIM(doi_code) = :code AND farm_id = :fid"), {"code": doi_code, "fid": farm_id}).scalar()


# ==============================================================================
# STEP 2 & 3: ĐỌC SHEET CÔNG & VẬT TƯ
# ==============================================================================
print("=" * 60)
print("📋 BƯỚC 2: Đọc sheet CÔNG")
print("=" * 60)

cong_frames = []
for farm_name, url in FARM_SHEETS.items():
    print(f"\n   📖 {farm_name}...")
    try:
        # Nhận diện Header qua 2 cột quan trọng: 'ngay' và ('ma_cv' hoặc 'cong_doan')
        df = read_sheet_robust(url, "Công (fact)", ["ngay", "ma_cv", "lo"])
    except Exception as e:
        print(f"      ❌ Lỗi đọc sheet: {e}"); continue

    if df.empty:
        print(f"      ⚠️  Sheet trống"); continue

    print(f"      Cột đã Map: {list(df.columns)}")

    if "ngay" not in df.columns:
        print(f"      ❌ Không tìm thấy cột 'ngay'"); continue

    # Loại bỏ dòng rác: Dòng thiếu ngày và thiếu cả ID công việc
    cv_col = next((c for c in ["hang_muc_cong_viec", "ten_cong_viec", "ma_cv"] if c in df.columns), None)
    if cv_col:
        blank_ngay = df["ngay"].astype(str).str.strip().isin(["", "nan", "none", "null"])
        blank_cv   = df[cv_col].astype(str).str.strip().isin(["", "nan", "none", "null"])
        before = len(df)
        df = df[~(blank_ngay & blank_cv)]
        if before - len(df):
            print(f"      → Lọc {before - len(df)} dòng rác (trống Ngày & CV)")

    df["ngay"] = pd.to_datetime(df["ngay"], format="%d/%m/%Y", errors="coerce")
    df = df.dropna(subset=["ngay"])
    if df.empty:
        print(f"      ⚠️  Không dòng hợp lệ sau parse ngày"); continue

    df["_farm_name"] = farm_name
    cong_frames.append(df)
    print(f"      ✅ {len(df):,} dòng hợp lệ | {df['ngay'].min().date()} → {df['ngay'].max().date()}")

if not cong_frames:
    print("❌ Không có data Công!")
else:
    df_cong_raw = pd.concat(cong_frames, ignore_index=True)
    to_numeric_col(df_cong_raw, ["so_cong", "klcv", "don_gia", "dinh_muc", "thanh_tien"])
    print(f"\n   Tổng cộng: {len(df_cong_raw):,} dòng Công")


print("\n" + "=" * 60)
print("📋 BƯỚC 3: Đọc sheet VẬT TƯ")
print("=" * 60)

vt_frames = []
for farm_name, url in FARM_SHEETS.items():
    print(f"\n   📖 {farm_name}...")
    try:
        df = read_sheet_robust(url, "Vật Tư (fact)", ["ngay", "ma_cv", "vat_tu", "sl", "so_luong"])
    except Exception as e:
        print(f"      ❌ Lỗi: {e}"); continue

    if df.empty:
        print(f"      ⚠️  Sheet trống"); continue

    print(f"      Cột đã Map: {list(df.columns)}")

    if "ngay" not in df.columns:
        print(f"      ❌ Không tìm thấy cột 'ngay'"); continue

    vt_col = next((c for c in ["vat_tu", "ten_vat_tu", "ma_vat_tu"] if c in df.columns), None)
    if vt_col:
        blank_ngay = df["ngay"].astype(str).str.strip().isin(["", "nan"])
        blank_vt   = df[vt_col].astype(str).str.strip().isin(["", "nan"])
        before = len(df)
        df = df[~(blank_ngay & blank_vt)]
        if before - len(df):
            print(f"      → Lọc {before - len(df)} dòng rác")

    df["ngay"] = pd.to_datetime(df["ngay"], format="%d/%m/%Y", errors="coerce")
    df = df.dropna(subset=["ngay"])
    if df.empty:
        print(f"      ⚠️  Không dòng hợp lệ sau parse ngày"); continue

    df["_farm_name"] = farm_name
    vt_frames.append(df)
    print(f"      ✅ {len(df):,} dòng hợp lệ | {df['ngay'].min().date()} → {df['ngay'].max().date()}")

if not vt_frames:
    print("❌ Không có data Vật Tư!")
else:
    df_vt_raw = pd.concat(vt_frames, ignore_index=True)
    to_numeric_col(df_vt_raw, ["sl", "so_luong", "don_gia", "thanh_tien"])
    print(f"\n   Tổng cộng: {len(df_vt_raw):,} dòng Vật Tư")


# ==============================================================================
# XÁC NHẬN
# ==============================================================================
print(f"\n{'='*80}")
print("⚠️  SẮP CẬP NHẬT DỮ LIỆU LÊN SUPABASE (UPSERT)".center(80))
print(f"{'='*80}")
if cong_frames:
    print(f"   Công    : {len(df_cong_raw):,} dòng -> Cập nhật fact_nhat_ky_san_xuat")
if vt_frames:
    print(f"   Vật tư  : {len(df_vt_raw):,} dòng -> Cập nhật fact_vat_tu")

confirm = input("\n❓ Bấm ENTER để tiếp tục hoặc gõ 'no' để hủy: ").strip().lower()
if confirm == "no":
    print("❌ Đã hủy.")
    raise SystemExit

# ==============================================================================
# STEP 4: UPSERT fact_nhat_ky_san_xuat
# ==============================================================================
print(f"\n{'='*60}")
print("🔄 STEP 4: UPSERT fact_nhat_ky_san_xuat")
print(f"{'='*60}")

if cong_frames:
    fact_cong_rows = []
    skipped_cong   = []

    with engine.begin() as conn:
        for i, row in df_cong_raw.iterrows():
            farm_name = row["_farm_name"]
            farm_id   = farm_lookup.get(normalize(farm_name))
            if not farm_id:
                skipped_cong.append((i, f"Không tìm thấy farm: {farm_name}")); continue

            lo_raw = get_val(row, "lo", "lo_code", "ma_lo")
            if not lo_raw:
                skipped_cong.append((i, "Thiếu tên lô")); continue
            lo_key = (farm_id, normalize(lo_raw))
            lo_id  = lo_lookup.get(lo_key)
            if not lo_id:
                lo_id = upsert_dim_lo(conn, lo_raw, farm_id)
                lo_lookup[lo_key] = lo_id

            doi_raw = get_val(row, "doi_thuc_hien", "doi", "ten_doi", "doi_code", "ma_doi")
            if not doi_raw:
                skipped_cong.append((i, "Thiếu tên đội")); continue
            doi_key = (farm_id, normalize(doi_raw))
            doi_id  = doi_lookup.get(doi_key)
            if not doi_id:
                doi_id = upsert_dim_doi(conn, doi_raw, farm_id)
                doi_lookup[doi_key] = doi_id

            ma_cv_raw = get_val(row, "ma_cv")
            cv_raw    = get_val(row, "hang_muc_cong_viec", "ten_cong_viec", "ma_cv")
            if not cv_raw:
                skipped_cong.append((i, "Thiếu tên CV")); continue

            cong_doan_raw = get_val(row, "cong_doan")
            cv_id = cv_by_ma_cv.get(normalize(ma_cv_raw)) if ma_cv_raw else None
            if not cv_id: cv_id = cv_by_name.get(normalize(cv_raw))
            if not cv_id:
                cv_id = upsert_dim_cong_viec(conn, ma_cv_raw, cv_raw, cong_doan_raw)
                if ma_cv_raw: cv_by_ma_cv[normalize(ma_cv_raw)] = cv_id
                cv_by_name[normalize(cv_raw)] = cv_id

            ht_raw = get_val(row, "ho_tro_doi_khac", "is_ho_tro").lower()
            is_ho_tro = ht_raw in ["true", "1", "yes", "có", "co", "x"]

            # Chỉ đưa các Measure và FKs theo Schema 3NF, không dính columns text dư thừa (đã xóa trc đó)
            fact_cong_rows.append({
                "farm_id":               farm_id,
                "lo_id":                 lo_id,
                "doi_id":                doi_id,
                "cong_viec_id":          cv_id,
                "ngay":                  row["ngay"].date(),
                "so_cong":               float(row.get("so_cong", 0) or 0),
                "klcv":                  float(row.get("klcv", 0) or 0),
                "dinh_muc":              float(row.get("dinh_muc", 0) or 0),
                "don_gia":               float(row.get("don_gia", 0) or 0),
                "thanh_tien":            float(row.get("thanh_tien", 0) or 0),
                "ghi_chu":               get_val(row, "ghi_chu"),
                "hang_muc_du_toan_cong": get_val(row, "hang_muc_du_toan_cong"),
                "lo_2":                  get_val(row, "lo_2"),
                "is_ho_tro":             is_ho_tro,
            })

        if fact_cong_rows:
            df_insert = pd.DataFrame(fact_cong_rows)
            # UNIQUE (farm_id, lo_id, doi_id, cong_viec_id, ngay, so_cong, klcv) - theo constraint trước đó ở Supabase
            df_insert = df_insert.drop_duplicates(subset=["farm_id", "lo_id", "doi_id", "cong_viec_id", "ngay", "so_cong", "klcv"], keep="last")
            
            # Xóa cũ trước khi import mới (Full load logic của Colab) 
            deleted = conn.execute(text("DELETE FROM fact_nhat_ky_san_xuat")).rowcount
            print(f"   🗑️  Xóa {deleted:,} dòng cũ\n")

            df_insert.to_sql("fact_nhat_ky_san_xuat", conn, if_exists="append", index=False, chunksize=500, method='multi')
            count = conn.execute(text("SELECT COUNT(*) FROM fact_nhat_ky_san_xuat")).scalar()
            print(f"\n   ✅ Đã UPSERT {len(df_insert):,} dòng | Tổng DB: {count:,} dòng")

        if skipped_cong:
            print(f"\n   ⚠️  Bỏ qua {len(skipped_cong)} dòng do lỗi map:")
            for idx, reason in skipped_cong[:5]: print(f"      Dòng {idx}: {reason}")


# ==============================================================================
# STEP 5: UPSERT fact_vat_tu
# ==============================================================================
print(f"\n{'='*60}")
print("🔄 STEP 5: UPSERT fact_vat_tu")
print(f"{'='*60}")

if vt_frames:
    fact_vt_rows = []
    skipped_vt   = []

    with engine.begin() as conn:
        for i, row in df_vt_raw.iterrows():
            farm_name = row["_farm_name"]
            farm_id   = farm_lookup.get(normalize(farm_name))
            if not farm_id:
                skipped_vt.append((i, f"Không tìm thấy farm: {farm_name}")); continue

            lo_raw = get_val(row, "lo", "lo_code", "ma_lo")
            if not lo_raw:
                skipped_vt.append((i, "Thiếu tên lô")); continue
            lo_key = (farm_id, normalize(lo_raw))
            lo_id  = lo_lookup.get(lo_key)
            if not lo_id:
                lo_id = upsert_dim_lo(conn, lo_raw, farm_id)
                lo_lookup[lo_key] = lo_id

            vt_name_raw = get_val(row, "vat_tu", "ten_vat_tu", "ma_vat_tu")
            if not vt_name_raw:
                skipped_vt.append((i, "Thiếu tên vật tư")); continue

            dvt_raw     = get_val(row, "dvt")
            dvt_norm    = normalize(dvt_raw) if dvt_raw else "—"
            loai_vt_raw = get_val(row, "loai_vat_tu")

            vt_key = (normalize(vt_name_raw), dvt_norm)
            vt_id  = vt_lookup.get(vt_key)
            if not vt_id:
                vt_id = upsert_dim_vat_tu(conn, vt_name_raw, dvt_raw, loai_vt_raw)
                vt_lookup[vt_key] = vt_id

            ma_cv_raw = get_val(row, "ma_cv")
            cv_raw    = get_val(row, "hang_muc_cong_viec", "ten_cong_viec", "ma_cv")
            cv_id     = None
            if cv_raw:
                cv_id = cv_by_ma_cv.get(normalize(ma_cv_raw)) if ma_cv_raw else None
                if not cv_id: cv_id = cv_by_name.get(normalize(cv_raw))
                if not cv_id:
                    cong_doan_raw = get_val(row, "cong_doan")
                    cv_id = upsert_dim_cong_viec(conn, ma_cv_raw, cv_raw, cong_doan_raw)
                    if ma_cv_raw: cv_by_ma_cv[normalize(ma_cv_raw)] = cv_id
                    cv_by_name[normalize(cv_raw)] = cv_id

            sl = float(row.get("sl", 0) or row.get("so_luong", 0) or 0)

            ht_raw = get_val(row, "ho_tro_doi_khac", "is_ho_tro").lower()
            is_ho_tro = ht_raw in ["true", "1", "yes", "có", "co", "x"]

            # Chỉ đưa các Measure và FKs theo Schema 3NF, bỏ 3 cột text thừa
            fact_vt_rows.append({
                "farm_id":                farm_id,
                "lo_id":                  lo_id,
                "cong_viec_id":           cv_id,
                "vat_tu_id":              vt_id,
                "ngay":                   row["ngay"].date(),
                "so_luong":               sl,
                "don_gia":                float(row.get("don_gia", 0) or 0),
                "thanh_tien":             float(row.get("thanh_tien", 0) or 0),
                "hang_muc_du_toan_vat_tu": get_val(row, "hang_muc_du_toan_vat_tu"),
                "lo_2":                   get_val(row, "lo_2"),
                "is_ho_tro":              is_ho_tro,
            })

        if fact_vt_rows:
            df_insert_vt = pd.DataFrame(fact_vt_rows)
            # UNIQUE (farm_id, lo_id, vat_tu_id, ngay, so_luong)
            df_insert_vt = df_insert_vt.drop_duplicates(subset=["farm_id", "lo_id", "vat_tu_id", "ngay", "so_luong"], keep="last")

            # Xóa cũ trước khi import mới
            deleted = conn.execute(text("DELETE FROM fact_vat_tu")).rowcount
            print(f"   🗑️  Xóa {deleted:,} dòng cũ\n")

            df_insert_vt.to_sql("fact_vat_tu", conn, if_exists="append", index=False, chunksize=500, method='multi')
            count = conn.execute(text("SELECT COUNT(*) FROM fact_vat_tu")).scalar()
            print(f"\n   ✅ Đã UPSERT {len(df_insert_vt):,} dòng | Tổng DB: {count:,} dòng")

        if skipped_vt:
            print(f"\n   ⚠️  Bỏ qua {len(skipped_vt)} dòng:")
            for idx, reason in skipped_vt[:5]: print(f"      Dòng {idx}: {reason}")

# ==============================================================================
# TỔNG KẾT
# ==============================================================================
print(f"\n{'='*80}")
print("🎉 HOÀN TẤT ĐỒNG BỘ LOCAL!".center(80))
print(f"{'='*80}")
