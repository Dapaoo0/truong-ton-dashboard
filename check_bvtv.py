import sys
import pandas as pd
from db import query

print("Checking data for BVTV in Farm 126 and 157...")
df = query("""
    SELECT f.farm_code, d.doi_code, nk.ngay, SUM(nk.so_cong) as total_cong
    FROM fact_nhat_ky_san_xuat nk
    JOIN dim_farm f ON f.farm_id = nk.farm_id
    JOIN dim_doi d ON d.doi_id = nk.doi_id
    WHERE f.farm_code IN ('Farm 126', 'Farm 157')
      AND d.doi_code ILIKE %s
    GROUP BY f.farm_code, d.doi_code, nk.ngay
    ORDER BY f.farm_code, nk.ngay
""", params=('%BVTV%',))

for farm in ['Farm 126', 'Farm 157']:
    farm_df = df[df['farm_code'] == farm]
    if farm_df.empty:
        print(f"No BVTV data for {farm}")
        continue
    
    print(f"\n--- {farm} BVTV Data ---")
    farm_df['ngay'] = pd.to_datetime(farm_df['ngay'])
    farm_df = farm_df.set_index('ngay')
    
    # Resample by month or week to see the distribution
    monthly = farm_df.resample('M')['total_cong'].sum()
    print(monthly)

    min_d = farm_df.index.min()
    max_d = farm_df.index.max()
    print(f"Date range: {min_d.strftime('%Y-%m-%d')} to {max_d.strftime('%Y-%m-%d')}")
    
    # Find gaps (days with no data)
    all_days = pd.date_range(start=min_d, end=max_d)
    missing_days = all_days.difference(farm_df.index)
    print(f"Total missing days: {len(missing_days)}")
    if not missing_days.empty:
        print("Missing dates:", [d.strftime('%Y-%m-%d') for d in missing_days])
        
    # Identify large gaps (> 7 days)
    if not missing_days.empty:
        gap_starts = []
        current_gap_start = missing_days[0]
        for i in range(1, len(missing_days)):
            if (missing_days[i] - missing_days[i-1]).days > 1:
                gap_end = missing_days[i-1]
                if (gap_end - current_gap_start).days >= 7:
                    gap_starts.append((current_gap_start, gap_end))
                current_gap_start = missing_days[i]
        
        # Check last gap
        gap_end = missing_days[-1]
        if (gap_end - current_gap_start).days >= 7:
            gap_starts.append((current_gap_start, gap_end))
            
        if gap_starts:
            print("Large gaps (>7 days):")
            for start, end in gap_starts:
                print(f"  {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ({(end-start).days + 1} days)")

