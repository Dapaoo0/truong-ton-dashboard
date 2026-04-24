"""Check what doi_name values appear in BVTV team sheets."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json, os
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

sys.path.insert(0, os.path.dirname(__file__))
from etl_sync import detect_header_row, map_columns, parse_date, normalize_text

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

from collections import Counter

tests = [
    ("Farm 126 BVTV", "17rQY5n--JLht6KuU3Vmg7lhqgzxpommcYeCc7jQJVf4", "Công (fact)"),
    ("Farm 157 BVTV", "12BUt2pyxomDYo71dVmbT6i_mIMv_ERMVnCb6O6r5ddw", "Nhập công hàng ngày"),
]

for label, sheet_id, sheet_name in tests:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    
    wb = gc.open_by_key(sheet_id)
    ws = wb.worksheet(sheet_name)
    data = ws.get_all_values()
    
    header_idx = detect_header_row(data)
    header = data[header_idx]
    col_map = map_columns(header)
    
    # Find doi_name column index
    doi_col = None
    for idx, target in col_map.items():
        if target == "doi_name":
            doi_col = idx
            break
    
    print(f"  doi_name column index: {doi_col}")
    if doi_col is not None:
        print(f"  Header at that col: '{header[doi_col]}'")
    
    # Count unique doi_name values in rows with valid dates
    doi_counter = Counter()
    rows = data[header_idx + 1:]
    for row in rows:
        vals = {}
        for idx, target in col_map.items():
            if idx < len(row):
                vals[target] = row[idx]
        
        ngay = parse_date(vals.get("ngay"))
        if not ngay:
            continue
        
        doi_raw = str(vals.get("doi_name", "")).strip()
        doi_normalized = normalize_text(doi_raw)
        doi_counter[f"{doi_raw} -> [{doi_normalized}]"] += 1
    
    print(f"\n  Doi name values (only rows with valid dates):")
    for doi_val, cnt in doi_counter.most_common():
        print(f"    '{doi_val}': {cnt} records")
