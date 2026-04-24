import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import gspread, json, os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from db import query
from collections import Counter

# --- Auth ---
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

# ============================================================
# CHECK BOTH FARMS
# ============================================================
checks = [
    {
        "farm": "Farm 126",
        "sheet_id": "17rQY5n--JLht6KuU3Vmg7lhqgzxpommcYeCc7jQJVf4",
        "expected_sheet": "Công (fact)",
    },
    {
        "farm": "Farm 157",
        "sheet_id": "12BUt2pyxomDYo71dVmbT6i_mIMv_ERMVnCb6O6r5ddw",
        "expected_sheet": "Nhập công hàng ngày",
    },
]

for chk in checks:
    print(f"\n{'='*60}")
    print(f"  {chk['farm']} BVTV - GSheet: {chk['sheet_id'][:20]}...")
    print(f"  ETL expects sheet: '{chk['expected_sheet']}'")
    print(f"{'='*60}")
    
    ss = gc.open_by_key(chk['sheet_id'])
    
    print(f"\nActual worksheets:")
    for ws in ss.worksheets():
        print(f"  - '{ws.title}' ({ws.row_count}r x {ws.col_count}c)")
    
    # Try to open the expected sheet
    target_ws = None
    try:
        target_ws = ss.worksheet(chk['expected_sheet'])
        print(f"\n✅ Found expected sheet '{chk['expected_sheet']}'")
    except gspread.exceptions.WorksheetNotFound:
        print(f"\n❌ Sheet '{chk['expected_sheet']}' NOT FOUND!")
        # Try alternatives
        for ws in ss.worksheets():
            if 'công' in ws.title.lower() or 'cong' in ws.title.lower() or 'fact' in ws.title.lower():
                print(f"  → Possible match: '{ws.title}'")
                if target_ws is None:
                    target_ws = ws
    
    if target_ws is None:
        print("  No matching sheet found, skipping...")
        continue
    
    print(f"\nReading sheet '{target_ws.title}'...")
    all_values = target_ws.get_all_values()
    print(f"Total rows: {len(all_values)}")
    
    if not all_values:
        continue
    
    print(f"Headers: {all_values[0]}")
    
    # Find date column
    header = [str(h).strip().lower() for h in all_values[0]]
    date_col_idx = None
    for i, h in enumerate(header):
        if 'ngày' in h or 'ngay' in h or 'date' in h:
            date_col_idx = i
            break
    
    if date_col_idx is None:
        print("Cannot find date column!")
        print(f"Header: {header}")
        continue
    
    # Collect dates
    dates = []
    for row in all_values[1:]:
        if date_col_idx < len(row):
            val = str(row[date_col_idx]).strip()
            if val:
                dates.append(val)
    
    print(f"Total rows with dates: {len(dates)}")
    print(f"First 3: {dates[:3]}")
    print(f"Last 5: {dates[-5:]}")
    
    # Monthly counts
    month_counts = Counter()
    for d in dates:
        parts = d.split('/')
        if len(parts) == 3:
            day, month, year = parts[0], parts[1], parts[2]
            if len(year) == 2:
                year = '20' + year
            month_key = f"{year}-{month.zfill(2)}"
            month_counts[month_key] += 1
        elif '-' in d:
            month_counts[d[:7]] += 1
    
    print(f"\nGSheet monthly breakdown:")
    for m in sorted(month_counts.keys()):
        print(f"  {m}: {month_counts[m]} records")
    
    # DB comparison
    db_df = query("""
        SELECT to_char(nk.ngay, 'YYYY-MM') as month, COUNT(*) as cnt
        FROM fact_nhat_ky_san_xuat nk
        JOIN dim_farm f ON f.farm_id = nk.farm_id
        JOIN dim_doi d ON d.doi_id = nk.doi_id
        WHERE f.farm_code = %s AND d.doi_code ILIKE %s
        GROUP BY to_char(nk.ngay, 'YYYY-MM')
        ORDER BY month
    """, params=(chk['farm'], '%BVTV%'))
    
    print(f"\nDB monthly breakdown:")
    for _, row in db_df.iterrows():
        print(f"  {row['month']}: {row['cnt']} records")
    
    # Diff
    all_months = sorted(set(list(month_counts.keys()) + list(db_df['month'].values)))
    print(f"\nDIFF:")
    for m in all_months:
        gs = month_counts.get(m, 0)
        db = int(db_df[db_df['month'] == m]['cnt'].values[0]) if m in db_df['month'].values else 0
        diff = gs - db
        if diff != 0:
            marker = "⚠️ MISSING FROM DB" if diff > 0 else "🔄 EXTRA IN DB (from Master)"
            print(f"  {m}: GSheet={gs}, DB={db} → {marker}")
