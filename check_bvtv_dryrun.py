"""Dry-run: Simulate ETL reading team BVTV sheets and trace why rows are skipped."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json, os
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Import ETL functions directly
sys.path.insert(0, os.path.dirname(__file__))
from etl_sync import (
    detect_header_row, map_columns, parse_date, parse_number,
    normalize_text
)

# Auth
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

# ── Test both BVTV sheets ──
tests = [
    ("Farm 126 BVTV", "17rQY5n--JLht6KuU3Vmg7lhqgzxpommcYeCc7jQJVf4", "Công (fact)"),
    ("Farm 157 BVTV", "12BUt2pyxomDYo71dVmbT6i_mIMv_ERMVnCb6O6r5ddw", "Nhập công hàng ngày"),
]

for label, sheet_id, sheet_name in tests:
    print(f"\n{'='*60}")
    print(f"  DRY-RUN: {label}")
    print(f"  Sheet: '{sheet_name}'")
    print(f"{'='*60}")
    
    wb = gc.open_by_key(sheet_id)
    try:
        ws = wb.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"  ❌ Sheet '{sheet_name}' NOT FOUND!")
        print(f"  Available: {[w.title for w in wb.worksheets()]}")
        continue
    
    data = ws.get_all_values()
    print(f"  Raw rows: {len(data)}")
    
    # Step 1: detect header
    header_idx = detect_header_row(data)
    header = data[header_idx]
    print(f"  Header row index: {header_idx}")
    print(f"  Header: {header[:10]}")
    
    # Step 2: map columns
    col_map = map_columns(header)
    print(f"  Column mapping: {col_map}")
    mapped_names = set(col_map.values())
    print(f"  Mapped names: {mapped_names}")
    
    # Check if mapping passes the gate
    has_cv_col = "ma_cv" in mapped_names or "hang_muc" in mapped_names
    has_num_col = "so_cong" in mapped_names or "thanh_tien" in mapped_names
    if not has_cv_col or not has_num_col:
        print(f"  ❌ GATE FAILED: has_cv_col={has_cv_col}, has_num_col={has_num_col}")
        print(f"  THIS IS WHY DATA IS SKIPPED!")
        continue
    else:
        print(f"  ✅ Gate passed: has_cv_col={has_cv_col}, has_num_col={has_num_col}")
    
    # Step 3: process rows
    rows = data[header_idx + 1:]
    total = 0
    skipped_no_date = 0
    skipped_empty = 0
    skipped_no_cv = 0
    ok = 0
    
    for row in rows:
        vals = {}
        for idx, target in col_map.items():
            if idx < len(row):
                vals[target] = row[idx]
        
        # Date check
        ngay = parse_date(vals.get("ngay"))
        if not ngay:
            skipped_no_date += 1
            total += 1
            continue
        
        # Numbers
        so_cong = parse_number(vals.get("so_cong"))
        klcv = parse_number(vals.get("klcv"))
        thanh_tien = parse_number(vals.get("thanh_tien"))
        
        # Empty check
        if so_cong == 0 and klcv == 0 and thanh_tien == 0:
            skipped_empty += 1
            total += 1
            continue
        
        # CV check (simplified - would need DB lookup in real ETL)
        ma_cv = normalize_text(vals.get("ma_cv", ""))
        hang_muc = normalize_text(vals.get("hang_muc", ""))
        doi_name = normalize_text(vals.get("doi_name", ""))
        
        ok += 1
        total += 1
        
        # Print first 3 ok rows
        if ok <= 3:
            print(f"  Sample OK row: date={ngay}, doi={doi_name}, ma_cv={ma_cv}, hang_muc={hang_muc}, so_cong={so_cong}")
    
    print(f"\n  SUMMARY:")
    print(f"    Total rows: {total}")
    print(f"    Skipped (no date): {skipped_no_date}")
    print(f"    Skipped (empty): {skipped_empty}")
    print(f"    Would process: {ok}")
