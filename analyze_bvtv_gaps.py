"""Analyze BVTV Farm 126 data gaps and patterns for imputation proposal."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from db import query

# 1. Monthly breakdown for BVTV Farm 126
print("=== BVTV Farm 126: Monthly Data ===")
df = query("""
    SELECT nk.ngay, nk.so_cong, nk.klcv, nk.thanh_tien, nk.dinh_muc,
           cv.ten_cong_viec, cv.ma_cv,
           l.lo_code
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    LEFT JOIN dim_cong_viec cv ON cv.cong_viec_id = nk.cong_viec_id
    LEFT JOIN dim_lo l ON l.lo_id = nk.lo_id
    WHERE f.farm_code = 'Farm 126' AND d.doi_code ILIKE %s
    ORDER BY nk.ngay
""", params=('%BVTV%',))

df['ngay'] = pd.to_datetime(df['ngay'])
df['month'] = df['ngay'].dt.to_period('M')

print(f"Total records: {len(df)}")
print(f"Date range: {df['ngay'].min()} → {df['ngay'].max()}")

# Monthly summary
monthly = df.groupby('month').agg(
    records=('so_cong', 'count'),
    total_cong=('so_cong', 'sum'),
    total_klcv=('klcv', 'sum'),
    total_tien=('thanh_tien', 'sum'),
    unique_days=('ngay', 'nunique'),
    unique_cv=('ten_cong_viec', 'nunique'),
    unique_lo=('lo_code', 'nunique'),
).reset_index()

print("\nMonthly Summary:")
print(f"{'Month':>10} | {'Rec':>5} | {'Days':>4} | {'Công':>8} | {'KLCV':>10} | {'Tiền':>12} | {'CV#':>3} | {'Lô#':>3}")
print("-" * 75)

# Check all months from min to max
all_months = pd.period_range(start=df['ngay'].min(), end=df['ngay'].max(), freq='M')
for m in all_months:
    row = monthly[monthly['month'] == m]
    if row.empty:
        print(f"{str(m):>10} | {'---':>5} | {'---':>4} | {'MISSING':>8} | {'MISSING':>10} | {'MISSING':>12} | {'--':>3} | {'--':>3}")
    else:
        r = row.iloc[0]
        print(f"{str(m):>10} | {int(r['records']):>5} | {int(r['unique_days']):>4} | {float(r['total_cong']):>8.1f} | {float(r['total_klcv']):>10.1f} | {float(r['total_tien']):>12,.0f} | {int(r['unique_cv']):>3} | {int(r['unique_lo']):>3}")

# 2. What types of work does BVTV do?
print("\n=== Top Công Việc of BVTV Farm 126 ===")
cv_summary = df.groupby('ten_cong_viec').agg(
    records=('so_cong', 'count'),
    total_cong=('so_cong', 'sum'),
    avg_cong_per_day=('so_cong', 'mean'),
).sort_values('records', ascending=False).head(15)

for cv_name, r in cv_summary.iterrows():
    print(f"  {cv_name:30s} | {int(r['records']):>4} rec | {float(r['total_cong']):>7.1f} công | avg={float(r['avg_cong_per_day']):.2f}/rec")

# 3. Check if Master has data for those missing months
print("\n=== Master GSheet data for BVTV in missing months? ===")
master_df = query("""
    SELECT to_char(nk.ngay, 'YYYY-MM') as month, 
           d.doi_code,
           COUNT(*) as cnt, 
           SUM(nk.so_cong) as total_cong
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code = 'Farm 126'
      AND to_char(nk.ngay, 'YYYY-MM') BETWEEN '2026-01' AND '2026-02'
    GROUP BY to_char(nk.ngay, 'YYYY-MM'), d.doi_code
    ORDER BY month, d.doi_code
""")
if master_df.empty:
    print("  No data at all for Farm 126 in Jan-Feb 2026 for any team")
else:
    for _, r in master_df.iterrows():
        print(f"  {r['month']} | {r['doi_code']:20s} | {r['cnt']} records, {r['total_cong']} công")

# 4. Check other farms' BVTV patterns for reference
print("\n=== Farm 157 BVTV Monthly (for comparison) ===")
df157 = query("""
    SELECT to_char(nk.ngay, 'YYYY-MM') as month,
           COUNT(*) as records,
           SUM(nk.so_cong) as total_cong,
           COUNT(DISTINCT nk.ngay) as days
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code = 'Farm 157' AND d.doi_code ILIKE %s
    GROUP BY to_char(nk.ngay, 'YYYY-MM')
    ORDER BY month
""", params=('%BVTV%',))
for _, r in df157.iterrows():
    print(f"  {r['month']} | {r['records']:>4} rec | {float(r['total_cong']):>7.1f} công | {r['days']} days")
