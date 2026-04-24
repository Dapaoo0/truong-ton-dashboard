"""Analyze October 2025 Vat Tu outliers across all farms."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from db import query

# 1. Monthly VT totals per farm to identify where the spike is
print("=== Monthly VT Totals by Farm ===")
monthly = query("""
    SELECT f.farm_code,
           to_char(vt.ngay, 'YYYY-MM') as month,
           COUNT(*) as records,
           SUM(vt.thanh_tien) as total_tien
    FROM fact_vat_tu vt
    JOIN dim_farm f ON f.farm_id = vt.farm_id
    WHERE vt.ngay >= '2025-08-01' AND vt.ngay <= '2026-04-30'
    GROUP BY f.farm_code, to_char(vt.ngay, 'YYYY-MM')
    ORDER BY f.farm_code, month
""")

for farm in monthly['farm_code'].unique():
    print(f"\n--- {farm} ---")
    fd = monthly[monthly['farm_code'] == farm]
    for _, r in fd.iterrows():
        flag = " ⚠️ HIGH" if float(r['total_tien']) > 5_000_000_000 else ""
        print(f"  {r['month']} | {r['records']:>5} rec | {float(r['total_tien']):>15,.0f} VND{flag}")

# 2. Deep dive into October 2025 - top items by thanh_tien
print("\n\n=== October 2025: Top VT Records by thanh_tien ===")
oct_top = query("""
    SELECT f.farm_code, vt.ngay, 
           v.ten_vat_tu, cv.ten_cong_viec,
           vt.so_luong, vt.don_gia, vt.thanh_tien,
           l.lo_code
    FROM fact_vat_tu vt
    JOIN dim_farm f ON f.farm_id = vt.farm_id
    LEFT JOIN dim_vat_tu v ON v.vat_tu_id = vt.vat_tu_id
    LEFT JOIN dim_cong_viec cv ON cv.cong_viec_id = vt.cong_viec_id
    LEFT JOIN dim_lo l ON l.lo_id = vt.lo_id
    WHERE vt.ngay >= '2025-10-01' AND vt.ngay <= '2025-10-31'
    ORDER BY vt.thanh_tien DESC
    LIMIT 30
""")

for _, r in oct_top.iterrows():
    print(f"  {r['farm_code']} | {r['ngay']} | {str(r['ten_vat_tu']):30s} | {float(r['thanh_tien']):>15,.0f} | qty={r['so_luong']} | price={r['don_gia']} | {r['lo_code']}")

# 3. Statistical analysis - IQR based outlier detection
print("\n\n=== Outlier Detection (IQR Method) ===")
all_vt = query("""
    SELECT f.farm_code, vt.ngay, vt.thanh_tien, vt.so_luong, vt.don_gia,
           v.ten_vat_tu, cv.ten_cong_viec, l.lo_code
    FROM fact_vat_tu vt
    JOIN dim_farm f ON f.farm_id = vt.farm_id
    LEFT JOIN dim_vat_tu v ON v.vat_tu_id = vt.vat_tu_id
    LEFT JOIN dim_cong_viec cv ON cv.cong_viec_id = vt.cong_viec_id
    LEFT JOIN dim_lo l ON l.lo_id = vt.lo_id
    WHERE vt.ngay >= '2025-10-01' AND vt.ngay <= '2025-10-31'
      AND vt.thanh_tien > 0
""")

q1 = all_vt['thanh_tien'].quantile(0.25)
q3 = all_vt['thanh_tien'].quantile(0.75)
iqr = q3 - q1
upper_bound = q3 + 3 * iqr  # Use 3x IQR for extreme outliers

print(f"  Q1: {float(q1):,.0f}")
print(f"  Q3: {float(q3):,.0f}")
print(f"  IQR: {float(iqr):,.0f}")
print(f"  Upper bound (Q3 + 3*IQR): {float(upper_bound):,.0f}")

outliers = all_vt[all_vt['thanh_tien'] > upper_bound].sort_values('thanh_tien', ascending=False)
print(f"\n  Outliers found: {len(outliers)} records")
print(f"  Total outlier value: {float(outliers['thanh_tien'].sum()):,.0f} VND")
print(f"  Non-outlier total: {float(all_vt[all_vt['thanh_tien'] <= upper_bound]['thanh_tien'].sum()):,.0f} VND")

print(f"\n  Top outliers:")
for _, r in outliers.head(20).iterrows():
    print(f"    {r['farm_code']} | {r['ngay']} | {str(r['ten_vat_tu']):30s} | {float(r['thanh_tien']):>15,.0f} | qty={r['so_luong']} | price={r['don_gia']} | {r['lo_code']}")
