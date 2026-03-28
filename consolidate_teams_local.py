from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import pandas as pd
import gspread
from config_google_auth import get_google_credentials
import os
import streamlit as st
from openpyxl.utils import get_column_letter

# --- THIẾT LẬP KẾT NỐI ---
try:
    load_dotenv(override=True)
    DB_URL = os.getenv("SUPABASE_URL")
    if not DB_URL and "supabase" in st.secrets:
        DB_URL = st.secrets["supabase"]["url"]
    
    if not DB_URL:
        print("❌ Không tìm thấy SUPABASE_URL")
        exit(1)
        
    print(f"🔗 Đang kết nối DB: {DB_URL.split('@')[1] if '@' in DB_URL else 'Unknown'}")
    
    pool = SimpleConnectionPool(
        1, 10,
        dsn=DB_URL,
        sslmode='require',
        options="-c search_path=public",
        connect_timeout=10
    )
    print("✅ Đã kết nối Supabase Postgres")
    
    # Kết nối Google Sheets
    print("🔑 Đang xác thực Google Sheets...")
    creds = get_google_credentials()
    gc = gspread.authorize(creds)
    print("✅ Đã kết nối Google Sheets")
except Exception as e:
    print(f"❌ Lỗi khởi tạo: {e}")
    exit(1)

def xoa_toan_bo_du_lieu_126(conn):
    """Giữ nguyên logic của hệ thống hiện tại"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM fact_nhat_ky_san_xuat 
                WHERE farm_id = (SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 126')
            """)
            
            cur.execute("""
                DELETE FROM fact_vat_tu 
                WHERE farm_id = (SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 126')
            """)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e

# --- CÁC HÀM MAPPING VÀ CHUẨN HOÁ GIỮ NGUYÊN ---
def normalize_text(text):
    if pd.isna(text): return ""
    return str(text).strip()

def print_mapping_stats(mapping_name, lookup_dict, found_count, miss_count, missing_values):
    print(f"\n📊 {mapping_name} Stats:")
    print(f"  - Total definitions: {len(lookup_dict)}")
    print(f"  - Matched: {found_count}")
    print(f"  - Missed: {miss_count}")
    if missing_values:
        print(f"  - Unmatched values: {sorted(list(missing_values))}")

def build_dim_doi(conn):
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT doi_id, doi_code FROM dim_doi")
            mapping = {row['doi_code'].strip(): row['doi_id'] for row in cur.fetchall()}
            
            # Thêm các alias phổ biến ở đây luôn
            alias_map = {
                "Điện nước": "Đội Điện Nước", 
                "Cơ giới": "Đội Cơ Giới",
                "Thu hoạch": "Đội Thu Hoạch"
            }
            # Cập nhật mapping với alias
            for alias, real_name in alias_map.items():
                if real_name in mapping:
                    mapping[alias] = mapping[real_name]
            
            return mapping
    except Exception as e:
        print(f"Lỗi build_dim_doi: {e}")
        return {}
        
def build_dim_lo(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT lo_id, lo_code FROM dim_lo WHERE farm_id = 1")
        return {row['lo_code'].strip(): row['lo_id'] for row in cur.fetchall()}

def build_dim_cv(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT cong_viec_id, ma_cv FROM dim_cong_viec")
        return {row['ma_cv'].strip(): row['cong_viec_id'] for row in cur.fetchall()}

def build_dim_vt(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT vat_tu_id, ma_vat_tu FROM dim_vat_tu")
        return {row['ma_vat_tu'].strip(): row['vat_tu_id'] for row in cur.fetchall()}

def detect_start_row(sheet, expected_headers):
    try:
        data = sheet.get_all_values()
        if not data: return None
        for i, row in enumerate(data):
            row_str = " ".join([str(cell).lower().strip() for cell in row if cell])
            if sum(1 for h in expected_headers if h.lower() in row_str) >= 2:
                return i
        return 0
    except Exception as e:
        print(f"Lỗi detect_start_row: {e}")
        return 0

def transform_dataframe(df):
    if len(df.columns) > 20: 
        df = df.iloc[:, :20]
    
    col_mapping = {}
    for col in df.columns:
        c_lower = str(col).lower().strip()
        if any(x in c_lower for x in ['đội', 'tên đội', 'nhóm']): col_mapping[col] = 'doi_name'
        elif any(x in c_lower for x in ['lô', 'lô làm']): col_mapping[col] = 'lo_name'
        elif any(x in c_lower for x in ['hạng mục', 'công đoạn', 'giai đoạn']): col_mapping[col] = 'hm_name'
        elif any(x in c_lower for x in ['mã cv', 'mã công việc', 'mã cv\n(bắt buộc)']): col_mapping[col] = 'ma_cv'
        elif 'ngày' in c_lower and 'tháng' in c_lower: col_mapping[col] = 'ngay'
        elif c_lower == 'ngày': col_mapping[col] = 'ngay'
        elif 'số công' in c_lower or c_lower == 'công': col_mapping[col] = 'so_cong'
        elif 'khối lượng' in c_lower or 'klcv' in c_lower: col_mapping[col] = 'klcv'
        elif 'thành tiền' in c_lower or 'số tiền' in c_lower: col_mapping[col] = 'thanh_tien'
        elif 'ca máy' in c_lower or 'số giờ' in c_lower: col_mapping[col] = 'so_cong'
        elif 'đơn giá' in c_lower: col_mapping[col] = 'don_gia'
        elif 'tên công việc' in c_lower: col_mapping[col] = 'ten_cv_goc'
        elif c_lower == 'tên vật tư' or 'vật tư' in c_lower: col_mapping[col] = 'ten_vt_goc'
        elif 'mã vt' in c_lower or 'mã vật tư' in c_lower or 'mã vt\n(bắt buộc)' in c_lower: col_mapping[col] = 'ma_vt'
        elif 'số lượng' in c_lower: col_mapping[col] = 'so_luong'
        elif 'đvt' in c_lower or 'đơn vị tính' in c_lower: col_mapping[col] = 'dvt'
        
    df = df.rename(columns=col_mapping)
    return df

class TeamProcessor:
    def __init__(self):
        self.conn = pool.getconn()
        self.doi_dict = build_dim_doi(self.conn)
        self.lo_dict = build_dim_lo(self.conn)
        self.cv_dict = build_dim_cv(self.conn)
        self.vt_dict = build_dim_vt(self.conn)
        
        # Tracking dictionaries
        self.missing_doi = set()
        self.missing_lo = set()
        self.missing_cv = set()
        self.missing_vt = set()
        
        self.stats = {
            'doi': {'found': 0, 'miss': 0},
            'lo': {'found': 0, 'miss': 0},
            'cv': {'found': 0, 'miss': 0},
            'vt': {'found': 0, 'miss': 0}
        }
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 126'")
                self.farm_id = cur.fetchone()[0]
        except Exception as e:
            print(f"Lỗi lấy farm_id: {e}")
            self.farm_id = 1
            
        self.df_nhatky = []
        self.df_vattu = []
        
    def _map_value(self, value, val_dict, missing_set, stat_type):
        if pd.isna(value) or not str(value).strip():
            # Treat empty tracking as found (none expected) vs error
            return None
        v = str(value).strip()
        mapped = val_dict.get(v)
        if mapped:
            self.stats[stat_type]['found'] += 1
            return mapped
        else:
            self.stats[stat_type]['miss'] += 1
            missing_set.add(v)
            return None

    def process_nhatky(self, df, source_name):
        df = transform_dataframe(df)
        required = ['ma_cv', 'so_cong']
        
        # Nếu không có ma_cv, lấy gì thay thế? 
        # Cần ít nhất một cột mapping được
        has_min_cols = any(c in df.columns for c in ['ma_cv', 'ten_cv_goc']) and \
                       any(c in df.columns for c in ['so_cong', 'thanh_tien'])
                       
        if not has_min_cols:
            print(f"⚠️ Bỏ qua Nhật Ký {source_name} - Thiếu cột (Các cột hiện có: {list(df.columns)})")
            return 0
            
        print(f"✅ Đang xử lý Nhật Ký {source_name} - {len(df)} dòng")
        added_count = 0
        
        for _, row in df.iterrows():
            # Xử lý ngày
            ngay = None
            if 'ngay' in row and not pd.isna(row['ngay']):
                try:
                    ngay_str = str(row['ngay']).strip()
                    if '/' in ngay_str or '-' in ngay_str:
                        ngay = pd.to_datetime(ngay_str, dayfirst=True).strftime('%Y-%m-%d')
                except:
                    pass
            if not ngay: continue
            
            # Xử lý foreign keys
            doi_val = normalize_text(row.get('doi_name', ''))
            lo_val = normalize_text(row.get('lo_name', ''))
            cv_val = normalize_text(row.get('ma_cv', ''))
            
            doi_id = self._map_value(doi_val, self.doi_dict, self.missing_doi, 'doi')
            lo_id = self._map_value(lo_val, self.lo_dict, self.missing_lo, 'lo')
            cv_id = self._map_value(cv_val, self.cv_dict, self.missing_cv, 'cv')
            
            # Xử lý số liệu
            try: so_cong = float(str(row.get('so_cong', 0)).replace(',', '')) if pd.notna(row.get('so_cong')) else 0
            except: so_cong = 0
            
            try: klcv = float(str(row.get('klcv', 0)).replace(',', '')) if pd.notna(row.get('klcv')) else 0
            except: klcv = 0
            
            try: thanh_tien = float(str(row.get('thanh_tien', 0)).replace(',', '')) if pd.notna(row.get('thanh_tien')) else 0
            except: thanh_tien = 0
            
            # Bỏ qua nếu dòng trống hoàn toàn về số liệu
            if so_cong == 0 and klcv == 0 and thanh_tien == 0:
                continue
                
            self.df_nhatky.append({
                'farm_id': self.farm_id,
                'ngay': ngay,
                'doi_id': doi_id if doi_id else None,
                'lo_id': lo_id if lo_id else None,
                'cong_viec_id': cv_id if cv_id else None,
                'so_cong': so_cong,
                'klcv': klcv,
                'thanh_tien': thanh_tien,
                'is_ho_tro': False,
                'is_khoan': False,
                'source_row': f"{source_name}_NK"
            })
            added_count += 1
            
        return added_count
        
    def process_vattu(self, df, source_name):
        df = transform_dataframe(df)
        
        has_min_cols = ('ma_vt' in df.columns or 'ten_vt_goc' in df.columns) and 'thanh_tien' in df.columns
        if not has_min_cols:
            print(f"⚠️ Bỏ qua Vật Tư {source_name} - Thiếu cột (Các cột hiện có: {list(df.columns)})")
            return 0
            
        print(f"✅ Đang xử lý Vật Tư {source_name} - {len(df)} dòng")
        added_count = 0
        
        for _, row in df.iterrows():
            ngay = None
            if 'ngay' in row and not pd.isna(row['ngay']):
                try:
                    ngay_str = str(row['ngay']).strip()
                    if '/' in ngay_str or '-' in ngay_str:
                        ngay = pd.to_datetime(ngay_str, dayfirst=True).strftime('%Y-%m-%d')
                except:
                    pass
            if not ngay: continue
            
            lo_val = normalize_text(row.get('lo_name', ''))
            vt_val = normalize_text(row.get('ma_vt', ''))
            cv_val = normalize_text(row.get('ma_cv', '')) # Vật tư cũng map công việc
            
            lo_id = self._map_value(lo_val, self.lo_dict, self.missing_lo, 'lo')
            vt_id = self._map_value(vt_val, self.vt_dict, self.missing_vt, 'vt')
            cv_id = self._map_value(cv_val, self.cv_dict, self.missing_cv, 'cv')
            
            try: so_luong = float(str(row.get('so_luong', 0)).replace(',', '')) if pd.notna(row.get('so_luong')) else 0
            except: so_luong = 0
            
            try: don_gia = float(str(row.get('don_gia', 0)).replace(',', '')) if pd.notna(row.get('don_gia')) else 0
            except: don_gia = 0
            
            try: thanh_tien = float(str(row.get('thanh_tien', 0)).replace(',', '')) if pd.notna(row.get('thanh_tien')) else 0
            except: thanh_tien = 0
            
            # Custom logic: if thanh_tien = 0 but have sl and dg
            # if thanh_tien == 0 and so_luong > 0 and don_gia > 0:
            #     thanh_tien = so_luong * don_gia
                
            if thanh_tien == 0 and so_luong == 0:
                continue
                
            self.df_vattu.append({
                'farm_id': self.farm_id,
                'lo_id': lo_id if lo_id else None,
                'cong_viec_id': cv_id if cv_id else None,
                'vat_tu_id': vt_id if vt_id else None,
                'ngay': ngay,
                'so_luong': so_luong,
                'don_gia': don_gia,
                'thanh_tien': thanh_tien,
                'source_row': f"{source_name}_VT"
            })
            added_count += 1
            
        return added_count
        
    def insert_to_db(self):
        print("\n⏳ Đang xoá dữ liệu cũ của Farm 126...")
        xoa_toan_bo_du_lieu_126(self.conn)
        
        insert_nhatky = """
            INSERT INTO fact_nhat_ky_san_xuat (
                farm_id, ngay, doi_id, lo_id, cong_viec_id, 
                so_cong, klcv, thanh_tien, is_khoan, is_ho_tro
            ) VALUES %s
        """
        
        insert_vattu = """
            INSERT INTO fact_vat_tu (
                farm_id, lo_id, cong_viec_id, vat_tu_id,
                ngay, so_luong, don_gia, thanh_tien
            ) VALUES %s
        """
        
        inserted_nk = 0
        inserted_vt = 0
        
        try:
            with self.conn.cursor() as cur:
                if self.df_nhatky:
                    values_nk = [(
                        r['farm_id'], r['ngay'], r['doi_id'], r['lo_id'], r['cong_viec_id'],
                        r['so_cong'], r['klcv'], r['thanh_tien'], r['is_khoan'], r['is_ho_tro']
                    ) for r in self.df_nhatky]
                    psycopg2.extras.execute_values(cur, insert_nhatky, values_nk)
                    inserted_nk = len(values_nk)
                    
                if self.df_vattu:
                    values_vt = [(
                        r['farm_id'], r['lo_id'], r['cong_viec_id'], r['vat_tu_id'],
                        r['ngay'], r['so_luong'], r['don_gia'], r['thanh_tien']
                    ) for r in self.df_vattu]
                    psycopg2.extras.execute_values(cur, insert_vattu, values_vt)
                    inserted_vt = len(values_vt)
                    
                self.conn.commit()
                print(f"✅ Đã chèn {inserted_nk} dòng Nhật ký và {inserted_vt} dòng Vật tư")
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Lỗi chèn dữ liệu: {e}")
            raise e
            
    def print_summary(self):
        print_mapping_stats("Đội (Teams)", self.doi_dict, self.stats['doi']['found'], self.stats['doi']['miss'], self.missing_doi)
        print_mapping_stats("Lô (Lots)", self.lo_dict, self.stats['lo']['found'], self.stats['lo']['miss'], self.missing_lo)
        print_mapping_stats("Công Việc (Tasks)", self.cv_dict, self.stats['cv']['found'], self.stats['cv']['miss'], self.missing_cv)
        print_mapping_stats("Vật Tư (Materials)", self.vt_dict, self.stats['vt']['found'], self.stats['vt']['miss'], self.missing_vt)

    def close(self):
        pool.putconn(self.conn)

# --- THIẾT LẬP CÁC NGUỒN DỮ LIỆU CẦN TỔNG HỢP ---
SOURCE_FILES = [
    {
        "id": "1m0L8fJv_p4R2mU9g-8iTz2o4h6cI7QzYd_5f4J5H2l8", 
        "name": "Nông Học CT1",
        "sheets": [
            {"name": "NHẬT KÝ", "type": "nhatky", "header_indicators": ["ngày", "mã cv"]},
            {"name": "XUẤT KHO VT", "type": "vattu", "header_indicators": ["ngày", "mã vt", "thành tiền"]}
        ]
    },
    {
        "id": "1o2A9jXy_p3K5mR9w-4dFb7c2g8lP1VvHn_1e6N3C0v2", 
        "name": "Cactus (Nông học CT2)",
        "sheets": [
            {"name": "NK", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "đội"]},
            {"name": "VT", "type": "vattu", "header_indicators": ["ngày", "mã vt", "thành tiền"]}
        ]
    },
    {
        "id": "17d-2b99s_L8D3pU6w-1fGh5k9x4jT0MqLw_8cB4D5v6", 
        "name": "Quyết Thắng & Mai Vàng",
        "sheets": [
            {"name": "NK QT", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "đội"]},
            {"name": "VT QT", "type": "vattu", "header_indicators": ["ngày", "mã vt", "thành tiền"]},
            {"name": "NK MV", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "đội"]},
            {"name": "VT MV", "type": "vattu", "header_indicators": ["ngày", "mã vt", "thành tiền"]}
        ]
    },
    {
        "id": "0D4r9hQy_p2N7mJ8w-9dFb5c3g8lP7VvEn_1e6N3C0v2", 
        "name": "Toàn Cầu",
        "sheets": [
            {"name": "Nhật Ký", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "tên công việc"]},
            {"name": "Vật Tư", "type": "vattu", "header_indicators": ["ngày", "mã vt", "thành tiền"]}
        ]
    },
    {
        "id": "1H2b9hXj_p5N3mK7w-2dCb5r3g8yP7HvJn_1e6V3C0v2", 
        "name": "Trạm Tưới",
        "sheets": [
            {"name": "T03", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "lô"]},
            {"name": "VT T03", "type": "vattu", "header_indicators": ["ngày", "mã vt", "thành tiền"]}
        ]
    },
    {
        "id": "1V4r8hMj_p7N3mQ5w-4dDb3c1g8uP9RvIn_1e6K3C0v2", 
        "name": "Đội Phun Xịt",
        "sheets": [
            {"name": "Bảng Chấm Công", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "lô"]},
            {"name": "Xuất Kho Thuốc", "type": "vattu", "header_indicators": ["ngày", "mã vt", "thành tiền"]}
        ]
    },
    {
        "id": "1o8s6VjR-1fE9wH4iZpLbM3q7u_NcgGz5lDtT2YxKy0a",
        "name": "Đội Cỏ",
        "sheets": [
            {"name": "Chấm Công", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "lô"]}
            # Đội cỏ thường không có vật tư
        ]
    },
    {
        "id": "1k3P7mD_qRn2sU8hVyLjT9f4wE1cX_b5vM0iZzA_Yg8o",
        "name": "Đội Điện Nước & Cơ Giới & Kho",
        "sheets": [
            {"name": "CG_M", "type": "nhatky", "header_indicators": ["ngày", "mã cv", "tên cv"]},
            {"name": "ĐN", "type": "nhatky", "header_indicators": ["ngày", "mã cv"]},
            {"name": "KHO", "type": "nhatky", "header_indicators": ["ngày", "mã cv"]}
        ]
    }
]

def download_and_process():
    processor = TeamProcessor()
    print("===========================================")
    print("🚀 BẮT ĐẦU TỔNG HỢP TỪ CÁC ĐỘI FARM 126")
    print("===========================================")
    
    total_files_processed = 0
    
    for source in SOURCE_FILES:
        doc_id = source["id"]
        doc_name = source["name"]
        print(f"\n📂 Đang mở tài liệu: {doc_name}...")
        
        try:
            wb = gc.open_by_key(doc_id)
            total_files_processed += 1
            
            for sheet_info in source["sheets"]:
                sheet_name = sheet_info["name"]
                
                try:
                    sheet = wb.worksheet(sheet_name)
                    data = sheet.get_all_values()
                    
                    if not data:
                        print(f"  ⏭️ Sheet {sheet_name} rỗng, bỏ qua")
                        continue
                        
                    # Tìm header row
                    header_row_idx = detect_start_row(sheet, sheet_info["header_indicators"])
                    
                    if header_row_idx is None:
                        print(f"  ⏭️ Không tìm thấy header trong {sheet_name}")
                        continue
                        
                    df = pd.DataFrame(data[header_row_idx+1:], columns=data[header_row_idx])
                    # Xoá cột rỗng
                    df = df.loc[:, ~df.columns.duplicated()]
                    df = df.loc[:, df.columns != '']
                    
                    if df.empty:
                        print(f"  ⏭️ Bảng {sheet_name} không có dữ liệu")
                        continue
                        
                    print(f"  📥 Tải {len(df)} dòng từ {sheet_name}...")
                    
                    # Xử lý theo loại
                    source_tag = f"{doc_name}_{sheet_name}"
                    if sheet_info["type"] == "nhatky":
                        processor.process_nhatky(df, source_tag)
                    elif sheet_info["type"] == "vattu":
                        processor.process_vattu(df, source_tag)
                        
                except gspread.exceptions.WorksheetNotFound:
                    print(f"  ⚠️ Cảnh báo: Không tìm thấy sheet '{sheet_name}' trong file {doc_name}")
                except Exception as e:
                    print(f"  ❌ Lỗi khi tải sheet {sheet_name}: {e}")
                    
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 404:
                print(f"❌ LỖI: Không tìm thấy document ID '{doc_id}' ({doc_name})")
                print("   -> Vui lòng kiểm tra lại ID hoặc thêm quyền truy cập cho email Service Account")
            else:
                print(f"❌ LỖI API khi tải {doc_name}: {e}")
        except Exception as e:
            print(f"❌ LỖI KHÔNG XÁC ĐỊNH với {doc_name}: {e}")

    # Chèn dữ liệu và in thống kê
    print("\n===========================================")
    print("💾 TIẾN HÀNH CHUYỂN DỮ LIỆU VÀO SUPABASE")
    print("===========================================")
    
    if len(processor.df_nhatky) == 0 and len(processor.df_vattu) == 0:
        print("⚠️ Không có dữ liệu nào được trích xuất thành công để Cập nhật!")
    else:
        processor.insert_to_db()
        
    processor.print_summary()
    processor.close()
    
    print("\n✅ HOÀN TẤT!")

if __name__ == "__main__":
    download_and_process()
