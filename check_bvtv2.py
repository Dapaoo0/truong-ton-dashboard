import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from db import query

# 1. Check all doi codes for farm 126 and 157
print("=== ALL DOI CODES ===")
doi_df = query("""
    SELECT DISTINCT f.farm_code, d.doi_code, d.doi_id
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code IN ('Farm 126', 'Farm 157')
    ORDER BY f.farm_code, d.doi_code
""")
for _, row in doi_df.iterrows():
    print(f"  {row['farm_code']} | {row['doi_code']} (id={row['doi_id']})")

# 2. Date range per doi per farm
print("\n=== DATE RANGES PER DOI ===")
range_df = query("""
    SELECT f.farm_code, d.doi_code,
           MIN(nk.ngay) as min_date,
           MAX(nk.ngay) as max_date,
           COUNT(DISTINCT nk.ngay) as num_days
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code IN ('Farm 126', 'Farm 157')
    GROUP BY f.farm_code, d.doi_code
    ORDER BY f.farm_code, d.doi_code
""")
for _, row in range_df.iterrows():
    print(f"  {row['farm_code']} | {str(row['doi_code']):20s} | {row['min_date']} -> {row['max_date']} | {row['num_days']} days")

# 3. Monthly breakdown for all teams
print("\n=== MONTHLY DISTINCT DAYS PER DOI ===")
monthly_df = query("""
    SELECT f.farm_code, d.doi_code,
           to_char(nk.ngay, 'YYYY-MM') as month,
           COUNT(DISTINCT nk.ngay) as distinct_days
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code IN ('Farm 126', 'Farm 157')
    GROUP BY f.farm_code, d.doi_code, to_char(nk.ngay, 'YYYY-MM')
    ORDER BY f.farm_code, d.doi_code, month
""")

for farm in ['Farm 126', 'Farm 157']:
    print(f"\n--- {farm} ---")
    farm_data = monthly_df[monthly_df['farm_code'] == farm]
    for doi in sorted(farm_data['doi_code'].unique()):
        doi_data = farm_data[farm_data['doi_code'] == doi]
        months_str = ", ".join([f"{r['month']}({r['distinct_days']}d)" for _, r in doi_data.iterrows()])
        print(f"  [{doi}]: {months_str}")
