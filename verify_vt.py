"""Quick verify VT monthly after outlier filter."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from db import query

monthly = query("""
    SELECT f.farm_code, to_char(vt.ngay, 'YYYY-MM') as month,
           COUNT(*) as records, SUM(vt.thanh_tien) as total_tien
    FROM fact_vat_tu vt
    JOIN dim_farm f ON f.farm_id = vt.farm_id
    WHERE f.farm_code = 'Farm 126'
    GROUP BY f.farm_code, to_char(vt.ngay, 'YYYY-MM')
    ORDER BY month
""")
print("=== Farm 126 VT Monthly (after outlier filter) ===")
for _, r in monthly.iterrows():
    print(f"  {r['month']} | {r['records']:>5} rec | {float(r['total_tien']):>15,.0f} VND")
