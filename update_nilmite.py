"""
Targeted update: Read Nilmite rows from BVTV 157 GSheet and update fact_vat_tu.
No full-reload — only touches Nilmite records.
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import gspread
import psycopg2
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

sys.path.insert(0, os.path.dirname(__file__))
from etl_sync import detect_header_row, map_columns, parse_date, parse_number, normalize_text

# --- Auth GSheet ---
token_path = os.path.join(os.path.dirname(__file__), "token.json")
with open(token_path) as f:
    tok = json.load(f)
creds = Credentials(
    token=tok["token"], refresh_token=tok["refresh_token"],
    token_uri=tok["token_uri"], client_id=tok["client_id"],
    client_secret=tok["client_secret"], scopes=tok["scopes"],
)
if creds.expired or not creds.valid:
    creds.refresh(Request())
gc = gspread.authorize(creds)

# --- Read BVTV 157 VT sheet ---
BVTV_157_SHEET_ID = "12BUt2pyxomDYo71dVmbT6i_mIMv_ERMVnCb6O6r5ddw"
VT_SHEET_NAME = "Nhập vật tư hàng ngày"

print("📂 Đang đọc sheet BVTV 157...")
wb = gc.open_by_key(BVTV_157_SHEET_ID)
ws = wb.worksheet(VT_SHEET_NAME)
data = ws.get_all_values()

header_idx = detect_header_row(data)
header = data[header_idx]
col_map = map_columns(header)
rows = data[header_idx + 1:]

print(f"  Header: {header}")
print(f"  Col map: {col_map}")
print(f"  Total rows: {len(rows)}")

# --- Filter Nilmite rows ---
nilmite_rows = []
for row in rows:
    vals = {}
    for idx, target in col_map.items():
        if idx < len(row):
            vals[target] = row[idx]
    
    vt_name = normalize_text(vals.get("ten_vt", ""))
    if "nilmite" not in vt_name.lower():
        continue
    
    ngay = parse_date(vals.get("ngay"))
    if not ngay:
        continue
    
    so_luong = parse_number(vals.get("so_luong"))
    don_gia = parse_number(vals.get("don_gia"))
    thanh_tien = parse_number(vals.get("thanh_tien"))
    
    if thanh_tien == 0 and so_luong > 0 and don_gia > 0:
        thanh_tien = so_luong * don_gia
    
    lo_raw = normalize_text(vals.get("lo_raw", ""))
    
    nilmite_rows.append({
        "ngay": ngay,
        "vt_name": vt_name,
        "lo_raw": lo_raw,
        "so_luong": so_luong,
        "don_gia": don_gia,
        "thanh_tien": thanh_tien,
    })

print(f"\n📋 Found {len(nilmite_rows)} Nilmite rows in GSheet:")
for r in nilmite_rows:
    print(f"  {r['ngay']} | {r['vt_name']:20s} | qty={r['so_luong']:>8} | price={r['don_gia']:>10} | total={r['thanh_tien']:>15,.0f} | lô={r['lo_raw']}")

# --- Connect to DB ---
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
cfg = {}
section = None
with open(secrets_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif "=" in line and section == "supabase":
            key, val = line.split("=", 1)
            val = val.strip().strip('"').strip("'")
            try: val = int(val)
            except: pass
            cfg[key.strip()] = val

conn = psycopg2.connect(
    host=cfg["host"], port=cfg.get("port", 6543),
    database=cfg.get("database", "postgres"),
    user=cfg["user"], password=cfg["password"],
    sslmode="require", options="-c search_path=public"
)

# --- Check current DB state ---
print("\n📊 Current Nilmite in DB (Farm 157):")
with conn.cursor() as cur:
    cur.execute("""
        SELECT vt.ngay, v.ten_vat_tu, vt.so_luong, vt.don_gia, vt.thanh_tien, l.lo_code
        FROM fact_vat_tu vt
        JOIN dim_farm f ON f.farm_id = vt.farm_id
        LEFT JOIN dim_vat_tu v ON v.vat_tu_id = vt.vat_tu_id
        LEFT JOIN dim_lo l ON l.lo_id = vt.lo_id
        WHERE f.farm_code = 'Farm 157'
          AND LOWER(v.ten_vat_tu) LIKE '%nilmite%'
        ORDER BY vt.ngay
    """)
    db_rows = cur.fetchall()
    for r in db_rows:
        print(f"  {r[0]} | {r[1]:20s} | qty={r[2]:>8} | price={r[3]:>10} | total={r[4]:>15,.0f} | lô={r[5]}")

# --- Update don_gia and thanh_tien for matching rows ---
print(f"\n🔧 Updating {len(db_rows)} Nilmite records in DB...")
updated = 0
with conn.cursor() as cur:
    # Get farm_id and vat_tu_id for Farm 157 Nilmite
    cur.execute("SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 157'")
    farm_id = cur.fetchone()[0]
    
    cur.execute("SELECT vat_tu_id, ten_vat_tu FROM dim_vat_tu WHERE LOWER(ten_vat_tu) LIKE '%nilmite%'")
    vt_ids = cur.fetchall()
    print(f"  Nilmite vat_tu_ids: {vt_ids}")
    
    # Build lookup from GSheet data: key = (ngay, lo_raw) -> (don_gia, thanh_tien)
    gs_lookup = {}
    for r in nilmite_rows:
        key = (str(r['ngay']), r['lo_raw'].lower())
        gs_lookup[key] = (r['don_gia'], r['thanh_tien'], r['so_luong'])
    
    # For each DB row, try to find matching GSheet row and update
    for vt_id, vt_name in vt_ids:
        cur.execute("""
            SELECT vat_tu_fact_id, vt.ngay, vt.so_luong, vt.don_gia, vt.thanh_tien, l.lo_code
            FROM fact_vat_tu vt
            LEFT JOIN dim_lo l ON l.lo_id = vt.lo_id
            WHERE vt.farm_id = %s AND vt.vat_tu_id = %s
        """, (farm_id, vt_id))
        
        for fact_id, ngay, so_luong, old_price, old_total, lo_code in cur.fetchall():
            lo_key = (lo_code or "").lower()
            key = (str(ngay), lo_key)
            
            if key in gs_lookup:
                new_price, new_total, new_qty = gs_lookup[key]
                new_total_calc = float(so_luong or 0) * new_price if new_price > 0 else new_total
                if new_price != float(old_price or 0):
                    cur.execute("""
                        UPDATE fact_vat_tu
                        SET don_gia = %s, thanh_tien = %s, updated_at = NOW()
                        WHERE vat_tu_fact_id = %s
                    """, (new_price, new_total_calc, fact_id))
                    updated += 1
                    print(f"  ✅ Updated {ngay} lô={lo_code}: price {old_price}->{new_price}, total {old_total}->{new_total_calc:.0f}")
    
    conn.commit()

print(f"\n✅ Done! Updated {updated} records.")

# --- Verify ---
print("\n📊 After update:")
with conn.cursor() as cur:
    cur.execute("""
        SELECT vt.ngay, v.ten_vat_tu, vt.so_luong, vt.don_gia, vt.thanh_tien, l.lo_code
        FROM fact_vat_tu vt
        JOIN dim_farm f ON f.farm_id = vt.farm_id
        LEFT JOIN dim_vat_tu v ON v.vat_tu_id = vt.vat_tu_id
        LEFT JOIN dim_lo l ON l.lo_id = vt.lo_id
        WHERE f.farm_code = 'Farm 157'
          AND LOWER(v.ten_vat_tu) LIKE '%nilmite%'
        ORDER BY vt.ngay
    """)
    for r in cur.fetchall():
        print(f"  {r[0]} | {r[1]:20s} | qty={r[2]:>8} | price={r[3]:>10} | total={r[4]:>15,.0f} | lô={r[5]}")

conn.close()
