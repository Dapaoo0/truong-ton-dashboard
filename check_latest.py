import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from db import query

# Check latest data timestamp per farm/doi
df = query("""
    SELECT f.farm_code, d.doi_code, 
           MAX(nk.ngay) as latest_date,
           COUNT(*) as total_records
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code IN ('Farm 126', 'Farm 157')
    GROUP BY f.farm_code, d.doi_code
    ORDER BY f.farm_code, latest_date DESC
""")

for farm in ['Farm 126', 'Farm 157']:
    print(f"\n--- {farm} ---")
    farm_data = df[df['farm_code'] == farm]
    for _, row in farm_data.iterrows():
        print(f"  {row['doi_code']:20s} latest={row['latest_date']}  ({row['total_records']} records)")
