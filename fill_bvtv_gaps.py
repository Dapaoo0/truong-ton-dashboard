"""
Fill BVTV Farm 126 missing months (Jan-Feb 2026)
Strategy: Clone December 2025 records with seasonal adjustment from Farm 157.
All generated records marked with is_estimated = TRUE.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import psycopg2
import psycopg2.extras
from datetime import date, timedelta
from db import query
import os

# --- Connect ---
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
            try:
                val = int(val)
            except ValueError:
                pass
            cfg[key.strip()] = val

conn = psycopg2.connect(
    host=cfg["host"], port=cfg.get("port", 6543),
    database=cfg.get("database", "postgres"),
    user=cfg["user"], password=cfg["password"],
    sslmode="require", options="-c search_path=public"
)
print("✅ Connected to Supabase")

# --- Step 1: Get December 2025 BVTV Farm 126 records as template ---
print("\n📋 Loading December 2025 BVTV Farm 126 records...")
dec_records = query("""
    SELECT nk.farm_id, nk.ngay, nk.doi_id, nk.lo_id, nk.cong_viec_id,
           nk.so_cong, nk.klcv, nk.dinh_muc, nk.ti_le_display, 
           nk.thanh_tien, nk.is_ho_tro
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code = 'Farm 126'
      AND d.doi_code ILIKE %s
      AND nk.ngay >= '2025-12-01' AND nk.ngay <= '2025-12-31'
    ORDER BY nk.ngay
""", params=('%BVTV%',))

print(f"  Found {len(dec_records)} December records")
if dec_records.empty:
    print("❌ No December data to clone!")
    sys.exit(1)

# --- Step 2: Calculate seasonal ratios from Farm 157 BVTV ---
print("\n📊 Calculating seasonal ratios from Farm 157 BVTV...")
f157_monthly = query("""
    SELECT to_char(nk.ngay, 'YYYY-MM') as month,
           SUM(nk.so_cong) as total_cong
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code = 'Farm 157' AND d.doi_code ILIKE %s
      AND nk.ngay >= '2025-12-01' AND nk.ngay <= '2026-02-28'
    GROUP BY to_char(nk.ngay, 'YYYY-MM')
    ORDER BY month
""", params=('%BVTV%',))

f157_dec = float(f157_monthly[f157_monthly['month'] == '2025-12']['total_cong'].values[0])
f157_jan = float(f157_monthly[f157_monthly['month'] == '2026-01']['total_cong'].values[0])
f157_feb = float(f157_monthly[f157_monthly['month'] == '2026-02']['total_cong'].values[0])

ratio_jan = f157_jan / f157_dec  # ~0.82
ratio_feb = f157_feb / f157_dec  # ~0.69

print(f"  Farm 157 Dec: {f157_dec}, Jan: {f157_jan} (ratio: {ratio_jan:.2f}), Feb: {f157_feb} (ratio: {ratio_feb:.2f})")

# --- Step 3: Generate imputed records ---
def generate_month_records(template_df, target_year, target_month, ratio, days_in_month):
    """Clone template records to a new month with seasonal adjustment."""
    records = []
    
    # Map template days to target month days
    unique_days = sorted(template_df['ngay'].unique())
    num_template_days = len(unique_days)
    
    # Scale: pick proportional number of days
    target_days = max(1, int(num_template_days * ratio))
    
    # Create day mapping: spread template days across target month
    import numpy as np
    target_dates = []
    step = days_in_month / target_days
    for i in range(target_days):
        day_num = min(days_in_month, max(1, int(1 + i * step)))
        target_dates.append(date(target_year, target_month, day_num))
    
    # Map each template day to a target day
    day_map = {}
    for i, src_day in enumerate(unique_days):
        target_idx = min(i, len(target_dates) - 1)
        day_map[src_day] = target_dates[target_idx]
    
    for _, row in template_df.iterrows():
        new_date = day_map.get(row['ngay'])
        if not new_date:
            continue
        
        # Adjust numeric values by ratio
        so_cong = float(row['so_cong']) * ratio if row['so_cong'] else 0
        klcv = float(row['klcv']) * ratio if row['klcv'] else 0
        thanh_tien = float(row['thanh_tien']) * ratio if row['thanh_tien'] else 0
        dinh_muc = float(row['dinh_muc']) if row['dinh_muc'] else None
        
        # Recalculate ti_le_display
        ti_le_display = None
        if so_cong > 0 and dinh_muc and dinh_muc > 0:
            ns_thuc = klcv / so_cong
            ti_le_display = (ns_thuc / dinh_muc) * 100
        
        records.append((
            row['farm_id'],
            new_date,
            row['doi_id'],
            row['lo_id'],
            row['cong_viec_id'],
            round(so_cong, 2),
            round(klcv, 2),
            dinh_muc,
            round(ti_le_display, 2) if ti_le_display else None,
            round(thanh_tien, 0),
            row['is_ho_tro'],
            True,  # is_estimated = TRUE
        ))
    
    return records

print("\n🔧 Generating imputed records...")

# January 2026: 31 days
jan_records = generate_month_records(dec_records, 2026, 1, ratio_jan, 31)
print(f"  January 2026: {len(jan_records)} records (ratio={ratio_jan:.2f})")

# February 2026: 28 days (2026 is not leap year)
feb_records = generate_month_records(dec_records, 2026, 2, ratio_feb, 28)
print(f"  February 2026: {len(feb_records)} records (ratio={ratio_feb:.2f})")

all_records = jan_records + feb_records
print(f"  Total to insert: {len(all_records)} records")

# --- Step 4: Delete any existing estimated records first ---
print("\n🗑️ Cleaning up any existing estimated records for BVTV Farm 126 Jan-Feb 2026...")
with conn.cursor() as cur:
    cur.execute("""
        DELETE FROM fact_nhat_ky_san_xuat
        WHERE is_estimated = TRUE
          AND farm_id = (SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 126')
          AND doi_id IN (SELECT doi_id FROM dim_doi WHERE doi_code ILIKE '%%BVTV%%')
          AND ngay >= '2026-01-01' AND ngay <= '2026-02-28'
    """)
    deleted = cur.rowcount
    print(f"  Deleted {deleted} existing estimated records")
    conn.commit()

# --- Step 5: Insert ---
print("\n💾 Inserting imputed records...")
insert_sql = """
    INSERT INTO fact_nhat_ky_san_xuat (
        farm_id, ngay, doi_id, lo_id, cong_viec_id,
        so_cong, klcv, dinh_muc, ti_le_display, thanh_tien, is_ho_tro, is_estimated
    ) VALUES %s
    ON CONFLICT ON CONSTRAINT uq_nk_natural_key DO NOTHING
"""

with conn.cursor() as cur:
    psycopg2.extras.execute_values(cur, insert_sql, all_records, page_size=200)
    conn.commit()

print(f"✅ Inserted {len(all_records)} estimated records")

# --- Step 6: Verify ---
print("\n📊 Verification: BVTV Farm 126 monthly after imputation")
verify = query("""
    SELECT to_char(nk.ngay, 'YYYY-MM') as month,
           COUNT(*) as records,
           SUM(nk.so_cong) as total_cong,
           COUNT(DISTINCT nk.ngay) as days,
           SUM(CASE WHEN nk.is_estimated THEN 1 ELSE 0 END) as estimated
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code = 'Farm 126' AND d.doi_code ILIKE %s
    GROUP BY to_char(nk.ngay, 'YYYY-MM')
    ORDER BY month
""", params=('%BVTV%',))

for _, r in verify.iterrows():
    est_label = f" ({r['estimated']} estimated)" if int(r['estimated']) > 0 else ""
    print(f"  {r['month']} | {r['records']:>4} rec | {float(r['total_cong']):>7.1f} công | {r['days']} days{est_label}")

conn.close()
print("\n✅ Done!")
