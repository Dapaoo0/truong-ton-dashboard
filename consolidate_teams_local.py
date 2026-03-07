"""
consolidate_teams_local.py
==========================
Tổng hợp dữ liệu Công và Vật tư từ 6 sheet đội → Farm 126 sheet.
Sử dụng Incremental Update (chỉ append dòng mới, không ghi đè).
Dedup bằng Composite Key so sánh trực tiếp.

Chạy: python consolidate_teams_local.py
       python consolidate_teams_local.py --dry-run     (chỉ kiểm tra, không ghi)
       python consolidate_teams_local.py --audit-only   (chỉ quét trùng lặp)
"""

import os
import sys
import argparse
import pandas as pd
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# ==============================================================================
# CONFIG
# ==============================================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

TEAM_SHEETS = {
    'Đội 1':         'https://docs.google.com/spreadsheets/d/1K7IxcAeZ_Qe82mLSDo2nM8PaZxdqe52TNPsgCpCY8aQ/edit',
    'Đội 2':         'https://docs.google.com/spreadsheets/d/1tMl4yhmStVjGsVhem3ICgfw9W10JVly9Y49uPPSFytA/edit',
    'Đội Thu Hoạch': 'https://docs.google.com/spreadsheets/d/1TYcbDTZLJjPdBSvf_Qo_rNe14myq3gUoWvXR6_U2W0s/edit',
    'Đội BVTV':      'https://docs.google.com/spreadsheets/d/17rQY5n--JLht6KuU3Vmg7lhqgzxpommcYeCc7jQJVf4/edit',
    'Đội Điện Nước': 'https://docs.google.com/spreadsheets/d/1by_0MyQb1pRPjTsxxE7z0BjIRzkfCOrApbVwP5_d8UE/edit',
    'Đội Cơ Giới':   'https://docs.google.com/spreadsheets/d/1WSD8mYp0jbhqTh-c3bZo638ihDnpcVugapdC1HdHViM/edit',
}

FARM_126_URL = 'https://docs.google.com/spreadsheets/d/1FJFVAUnDLp4C2w6n4le4iVNPUVdhYandy8NQaf2bcB0/edit'

# Composite keys dùng để dedup (so sánh trực tiếp, không hash)
DEDUP_KEY_CONG = ['Ngày', 'Lô', 'Lô 2', 'Mã CV', 'Số Công', 'KLCV']
DEDUP_KEY_VT   = ['Ngày', 'Lô', 'Lô 2', 'Mã CV', 'Vật Tư', 'SL']

# Thứ tự cột mong đợi trong Farm 126 (từ explore_sheets_output.txt)
FARM_CONG_COLS = [
    'STT', 'Mã CV', 'Lô', 'Lô 2', 'Đội Thực Hiện', 'Ngày',
    'Hạng mục công việc', 'Loại công', 'Số Công', 'KLCV', 'ĐVT',
    'Đơn Giá', 'Định Mức', 'Thành Tiền', 'Công Đoạn', 'Ghi Chú',
    'Hỗ Trợ Đội Khác'
]

FARM_VT_COLS = [
    'STT', 'Mã CV', 'Lô', 'Lô 2', 'Ngày', 'Hạng mục công việc',
    'Vật Tư', 'SL', 'ĐVT', 'Đơn Giá', 'Thành Tiền', 'Công Đoạn',
    'Loại Vật Tư'
]


# ==============================================================================
# AUTH (reuse logic từ sync_data_local.py)
# ==============================================================================
def authenticate():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("🌐 Đang mở trình duyệt để xác thực Google...")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return gspread.authorize(creds)


# ==============================================================================
# HELPERS
# ==============================================================================
def extract_sheet_id(url):
    return url.split('/d/')[1].split('/')[0]


def norm(val):
    """Normalize giá trị để so sánh composite key."""
    if pd.isna(val) or val is None:
        return ''
    s = str(val).strip()
    if s.lower() in ('nan', 'none', ''):
        return ''
    # Bỏ dấu phẩy trong số (ví dụ "375,000" → "375000")
    try:
        cleaned = s.replace(',', '')
        num = float(cleaned)
        # Trả về dạng chuẩn: 375000.0 → "375000", 0.5 → "0.5"
        if num == int(num):
            return str(int(num))
        return str(num)
    except ValueError:
        return s.lower().strip()


def make_key(row, key_cols):
    """Tạo composite key tuple từ 1 dòng DataFrame."""
    return tuple(norm(row.get(c, '')) for c in key_cols)


def is_empty_row(row_values):
    """Kiểm tra xem dòng có rỗng hoàn toàn không."""
    return all(
        str(v).strip() in ('', '0', '0.0', 'nan', 'None', 'NaN')
        for v in row_values
    )


def read_sheet(gc, url, tab_name):
    """Đọc 1 tab từ Google Sheet, trả về DataFrame (hoặc None)."""
    try:
        sheet_id = extract_sheet_id(url)
        ws = gc.open_by_key(sheet_id).worksheet(tab_name)
        all_vals = ws.get_all_values()

        if not all_vals or len(all_vals) < 2:
            return None

        headers = all_vals[0]

        # Xử lý header trùng/rỗng
        seen = {}
        clean_headers = []
        for i, h in enumerate(headers):
            h = h.strip()
            if not h or h in seen:
                clean_headers.append(f'_empty_{i}')
            else:
                clean_headers.append(h)
                seen[h] = True

        # Bỏ dòng rỗng
        data = [r for r in all_vals[1:] if not is_empty_row(r)]
        if not data:
            return None

        df = pd.DataFrame(data, columns=clean_headers)

        # Drop cột rỗng / unnamed
        drop_cols = [c for c in df.columns if c.startswith('_empty_')]
        if drop_cols:
            df = df.drop(columns=drop_cols)

        # Drop cột STT nếu có
        if 'STT' in df.columns:
            df = df.drop(columns=['STT'])

        return df

    except Exception as e:
        print(f"      ❌ Lỗi đọc {tab_name}: {e}")
        return None


# ==============================================================================
# PHASE 1: ĐỌC DỮ LIỆU TỪ CÁC ĐỘI
# ==============================================================================
def read_all_teams(gc, data_type="Công"):
    """Đọc dữ liệu từ tất cả team sheets."""
    tab = "Công (fact)" if data_type == "Công" else "Vật Tư (fact)"
    frames = []

    print(f"\n{'='*60}")
    print(f"📋 ĐỌC DỮ LIỆU {data_type.upper()} TỪ CÁC ĐỘI")
    print(f"{'='*60}")

    for team_name, url in TEAM_SHEETS.items():
        print(f"\n   📖 {team_name}...", end=" ")
        df = read_sheet(gc, url, tab)
        if df is not None and not df.empty:
            # Auto-fill cột Đội Thực Hiện cho Công
            if data_type == "Công" and 'Đội Thực Hiện' not in df.columns:
                df['Đội Thực Hiện'] = team_name

            # Lọc dòng rác: dòng thiếu Ngày VÀ thiếu dữ liệu chính
            if 'Ngày' in df.columns:
                blank = df['Ngày'].astype(str).str.strip().isin(['', 'nan', 'None'])
                before = len(df)
                df = df[~blank]
                skipped = before - len(df)
                if skipped:
                    print(f"(lọc {skipped} dòng rác)", end=" ")

            frames.append(df)
            print(f"✅ {len(df)} dòng")
        else:
            print(f"⚠️ Trống")

    if not frames:
        print(f"\n   ❌ Không có dữ liệu {data_type}!")
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    print(f"\n   📊 Tổng: {len(result):,} dòng từ {len(frames)} đội")
    return result


# ==============================================================================
# PHASE 2: DEDUP — SO SÁNH VỚI DỮ LIỆU HIỆN CÓ
# ==============================================================================
def dedup_against_existing(gc, new_df, data_type="Công"):
    """Đọc Farm 126 sheet, so sánh composite key, trả về chỉ dòng mới."""
    tab = "Công (fact)" if data_type == "Công" else "Vật Tư (fact)"
    key_cols = DEDUP_KEY_CONG if data_type == "Công" else DEDUP_KEY_VT

    print(f"\n{'='*60}")
    print(f"🔍 DEDUP: SO SÁNH VỚI FARM 126 ({data_type})")
    print(f"{'='*60}")
    print(f"   Composite key: {key_cols}")

    existing_df = read_sheet(gc, FARM_126_URL, tab)

    if existing_df is None or existing_df.empty:
        print(f"   ℹ️ Farm 126 sheet trống → tất cả {len(new_df)} dòng đều mới")
        return new_df, 0

    print(f"   📊 Farm 126 hiện có: {len(existing_df):,} dòng")

    # Tạo set các composite key hiện có
    existing_keys = set()
    for _, row in existing_df.iterrows():
        existing_keys.add(make_key(row, key_cols))

    # Lọc ra dòng mới
    is_new = []
    for _, row in new_df.iterrows():
        key = make_key(row, key_cols)
        is_new.append(key not in existing_keys)

    new_only = new_df[is_new].reset_index(drop=True)
    dup_count = len(new_df) - len(new_only)

    print(f"   ✅ Dòng MỚI (sẽ append): {len(new_only):,}")
    print(f"   ⏭️ Dòng TRÙNG (skip):    {dup_count:,}")

    return new_only, dup_count


# ==============================================================================
# PHASE 3: APPEND VÀO FARM 126
# ==============================================================================
def append_to_farm(gc, new_df, data_type="Công", dry_run=False):
    """Append dòng mới vào cuối sheet Farm 126."""
    tab = "Công (fact)" if data_type == "Công" else "Vật Tư (fact)"
    farm_cols = FARM_CONG_COLS if data_type == "Công" else FARM_VT_COLS
    # Bỏ STT — sẽ để trống cho Farm 126 tự tính
    farm_cols_no_stt = [c for c in farm_cols if c != 'STT']

    if new_df.empty:
        print(f"\n   ℹ️ Không có dòng mới để append cho {data_type}")
        return

    print(f"\n{'='*60}")
    print(f"📤 APPEND VÀO FARM 126 ({data_type})")
    print(f"{'='*60}")

    if dry_run:
        print(f"   🏃 DRY RUN — Không ghi gì cả!")
        print(f"   Sẽ append {len(new_df):,} dòng nếu chạy thật.")
        # In mẫu 5 dòng đầu
        print(f"\n   📋 Mẫu 5 dòng đầu:")
        for i, (_, row) in enumerate(new_df.head().iterrows()):
            key_str = " | ".join(
                f"{c}={str(row.get(c, '')).strip()[:20]}"
                for c in (DEDUP_KEY_CONG if data_type == "Công" else DEDUP_KEY_VT)
                if c in row.index
            )
            print(f"      {i+1}. {key_str}")
        return

    # Chuẩn hóa cột trước khi ghi
    # Đảm bảo DataFrame có đúng thứ tự cột của Farm 126
    for col in farm_cols_no_stt:
        if col not in new_df.columns:
            new_df[col] = ''

    export_df = new_df[farm_cols_no_stt].copy()
    # Thêm cột STT trống ở đầu
    export_df.insert(0, 'STT', '')

    # Chuẩn hóa giá trị
    for col in export_df.columns:
        export_df[col] = export_df[col].apply(
            lambda v: '' if pd.isna(v) or str(v).strip().lower() in ('nan', 'none') else str(v).strip()
        )

    # Append vào sheet
    sheet_id = extract_sheet_id(FARM_126_URL)
    ws = gc.open_by_key(sheet_id).worksheet(tab)

    rows_to_append = export_df.values.tolist()
    ws.append_rows(rows_to_append, value_input_option='USER_ENTERED')

    print(f"   ✅ Đã append {len(rows_to_append):,} dòng vào Farm 126 → {tab}")


# ==============================================================================
# PHASE 4: AUDIT DUPLICATE TRONG FARM 126 (từ 01/01/2026)
# ==============================================================================
def audit_duplicates(gc, data_type="Công", since_date="01/01/2026"):
    """Quét Farm 126 sheet tìm dòng trùng lặp."""
    tab = "Công (fact)" if data_type == "Công" else "Vật Tư (fact)"
    key_cols = DEDUP_KEY_CONG if data_type == "Công" else DEDUP_KEY_VT

    print(f"\n{'='*60}")
    print(f"🔎 AUDIT TRÙNG LẶP: FARM 126 — {data_type} (từ {since_date})")
    print(f"{'='*60}")

    df = read_sheet(gc, FARM_126_URL, tab)
    if df is None or df.empty:
        print(f"   ℹ️ Sheet trống, không có gì để audit")
        return

    print(f"   📊 Tổng dòng: {len(df):,}")

    # Lọc từ since_date trở đi
    if 'Ngày' in df.columns:
        df['_parsed_date'] = pd.to_datetime(df['Ngày'], format='%d/%m/%Y', errors='coerce')
        cutoff = pd.to_datetime(since_date, format='%d/%m/%Y')
        df_filtered = df[df['_parsed_date'] >= cutoff].copy()
        df_filtered = df_filtered.drop(columns=['_parsed_date'])
        df = df.drop(columns=['_parsed_date'])
    else:
        df_filtered = df

    print(f"   📊 Dòng từ {since_date}: {len(df_filtered):,}")

    if df_filtered.empty:
        print(f"   ℹ️ Không có dữ liệu từ {since_date}")
        return

    # Tìm duplicate
    keys = []
    for _, row in df_filtered.iterrows():
        keys.append(make_key(row, key_cols))

    key_series = pd.Series(keys)
    dup_mask = key_series.duplicated(keep=False)
    dup_count = dup_mask.sum()

    if dup_count == 0:
        print(f"   ✅ Không tìm thấy dòng trùng lặp!")
        return

    print(f"   ⚠️ Phát hiện {dup_count} dòng trùng lặp ({dup_count // 2} cặp ước tính)")

    # In chi tiết 10 cặp đầu
    dup_indices = df_filtered.index[dup_mask]
    shown = set()
    pair_count = 0
    for idx in dup_indices:
        key = keys[list(df_filtered.index).index(idx)]
        if key in shown:
            continue
        shown.add(key)
        pair_count += 1
        if pair_count > 10:
            print(f"   ... và {len(shown) - 10} cặp trùng khác")
            break
        key_str = " | ".join(f"{c}={v}" for c, v in zip(key_cols, key) if v)
        print(f"      [{pair_count}] {key_str}")

    return dup_count


# ==============================================================================
# PHASE 0: XÓA TRÙNG LẶP TRONG FARM 126
# ==============================================================================
def remove_duplicates(gc, data_type="Công"):
    """Xóa dòng trùng lặp trong Farm 126 sheet (giữ dòng đầu tiên)."""
    tab = "Công (fact)" if data_type == "Công" else "Vật Tư (fact)"
    key_cols = DEDUP_KEY_CONG if data_type == "Công" else DEDUP_KEY_VT

    print(f"\n{'='*60}")
    print(f"🗑️ XÓA TRÙNG LẶP: FARM 126 — {data_type}")
    print(f"{'='*60}")

    sheet_id = extract_sheet_id(FARM_126_URL)
    ws = gc.open_by_key(sheet_id).worksheet(tab)
    all_vals = ws.get_all_values()

    if not all_vals or len(all_vals) < 2:
        print(f"   ℹ️ Sheet trống")
        return

    headers = all_vals[0]
    data_rows = all_vals[1:]
    print(f"   📊 Tổng dòng (trước): {len(data_rows):,}")

    df = pd.DataFrame(data_rows, columns=headers)

    # Tạo composite key cho mỗi dòng
    keys = []
    for _, row in df.iterrows():
        keys.append(make_key(row, key_cols))

    df['_key'] = keys

    # Đánh dấu trùng (giữ dòng đầu tiên)
    dup_mask = df.duplicated(subset=['_key'], keep='first')
    dup_count = dup_mask.sum()

    if dup_count == 0:
        print(f"   ✅ Không có dòng trùng lặp!")
        return

    print(f"   ⚠️ Sẽ xóa {dup_count} dòng trùng (giữ bản gốc đầu tiên)")

    # Giữ lại chỉ dòng không trùng
    df_clean = df[~dup_mask].drop(columns=['_key']).reset_index(drop=True)
    print(f"   📊 Tổng dòng (sau):  {len(df_clean):,}")

    # Ghi lại toàn bộ sheet (header + data)
    ws.clear()
    upload_data = [headers] + df_clean.values.tolist()
    ws.update(range_name='A1', values=upload_data, value_input_option='USER_ENTERED')

    print(f"   ✅ Đã xóa {dup_count} dòng trùng và ghi lại sheet")


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Tổng hợp dữ liệu Đội → Farm 126")
    parser.add_argument('--dry-run', action='store_true',
                        help='Chỉ kiểm tra, không ghi gì vào sheet')
    parser.add_argument('--audit-only', action='store_true',
                        help='Chỉ quét trùng lặp trong Farm 126')
    parser.add_argument('--remove-dupes', action='store_true',
                        help='Xóa dòng trùng lặp trong Farm 126 trước khi append')
    parser.add_argument('--since', default='01/01/2026',
                        help='Ngày bắt đầu audit (dd/mm/yyyy)')
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 CONSOLIDATE TEAMS → FARM 126 (Incremental Update)".center(80))
    print("=" * 80)

    gc = authenticate()
    print("✅ Xác thực Google Sheets thành công\n")

    if args.audit_only:
        audit_duplicates(gc, "Công", args.since)
        audit_duplicates(gc, "Vật Tư", args.since)
        print(f"\n{'='*80}")
        print("✅ HOÀN TẤT AUDIT".center(80))
        print(f"{'='*80}")
        return

    # --- PHASE 0: XÓA TRÙNG (nếu có flag) ---
    if args.remove_dupes:
        remove_duplicates(gc, "Công")
        remove_duplicates(gc, "Vật Tư")

    # --- CÔNG ---
    cong_new = read_all_teams(gc, "Công")
    if not cong_new.empty:
        cong_to_append, cong_dup = dedup_against_existing(gc, cong_new, "Công")
        append_to_farm(gc, cong_to_append, "Công", dry_run=args.dry_run)
    else:
        cong_to_append = pd.DataFrame()
        cong_dup = 0

    # --- VẬT TƯ ---
    vt_new = read_all_teams(gc, "Vật Tư")
    if not vt_new.empty:
        vt_to_append, vt_dup = dedup_against_existing(gc, vt_new, "Vật Tư")
        append_to_farm(gc, vt_to_append, "Vật Tư", dry_run=args.dry_run)
    else:
        vt_to_append = pd.DataFrame()
        vt_dup = 0

    # --- AUDIT ---
    print(f"\n{'─'*80}")
    print("🔎 KIỂM TRA TRÙNG LẶP SAU KHI APPEND")
    print(f"{'─'*80}")
    audit_duplicates(gc, "Công", args.since)
    audit_duplicates(gc, "Vật Tư", args.since)

    # --- TỔNG KẾT ---
    print(f"\n{'='*80}")
    print("🎉 HOÀN TẤT".center(80))
    print(f"{'='*80}")
    mode = "DRY RUN" if args.dry_run else "THỰC THI"
    print(f"   Mode: {mode}")
    print(f"   Công  — Mới: {len(cong_to_append):,} | Trùng skip: {cong_dup:,}")
    print(f"   Vật Tư — Mới: {len(vt_to_append):,} | Trùng skip: {vt_dup:,}")
    if not args.dry_run and (not cong_to_append.empty or not vt_to_append.empty):
        print(f"\n   💡 Chạy 'python sync_data_local.py' để đẩy lên Supabase")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
