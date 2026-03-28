from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import pandas as pd
import gspread
from config_google_auth import get_google_credentials
import os
import streamlit as st
import numpy as np

# Load Env Vars
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

def xoa_toan_bo_du_lieu_157(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM fact_nhat_ky_san_xuat 
                WHERE farm_id = (SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 157')
            """)
            
            cur.execute("""
                DELETE FROM fact_vat_tu 
                WHERE farm_id = (SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 157')
            """)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e

def normalize_text(text):
    if pd.isna(text): return ""
    return str(text).strip()

def build_dim_doi(conn):
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT doi_id, doi_code FROM dim_doi")
            mapping = {row['doi_code'].strip(): row['doi_id'] for row in cur.fetchall()}
            
            # Thêm alias Farm 157
            alias_map = {
                "Điện nước": "Đội Điện Nước", 
                "Cờ Giới 157": "Đội Cơ Giới",
                "Thu hoạch 157": "Đội Thu Hoạch"
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
        # Lay lo cua farm 157 (id = 2)
        cur.execute("SELECT lo_id, lo_code FROM dim_lo WHERE farm_id = 2")
        return {row['lo_code'].strip(): row['lo_id'] for row in cur.fetchall()}

def build_dim_cv(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT cong_viec_id, ma_cv FROM dim_cong_viec")
        return {row['ma_cv'].strip(): row['cong_viec_id'] for row in cur.fetchall()}

def build_dim_vt(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT vat_tu_id, ma_vat_tu FROM dim_vat_tu")
        return {row['ma_vat_tu'].strip(): row['vat_tu_id'] for row in cur.fetchall()}

def download_sheet(wb, sheet_name, start_row=1):
    try:
        sheet = wb.worksheet(sheet_name)
        data = sheet.get_all_values()
        if not data or len(data) <= start_row:
            print(f"  ⏭️ Bảng {sheet_name} rỗng")
            return pd.DataFrame()
            
        columns = data[start_row-1]
        df = pd.DataFrame(data[start_row:], columns=columns)
        print(f"  📥 Đã tải {len(df)} dòng từ {sheet_name}")
        return df
    except gspread.exceptions.WorksheetNotFound:
        print(f"  ⚠️ Cảnh báo: Không tìm thấy sheet '{sheet_name}'")
        return pd.DataFrame()

def transform_dataframe(df):
    col_mapping = {}
    for col in df.columns:
        c_lower = str(col).lower().strip()
        if 'lô' in c_lower: col_mapping[col] = 'lo_name'
        elif 'mã cv' in c_lower or 'mã công việc' in c_lower: col_mapping[col] = 'ma_cv'
        elif 'ngày ghi' in c_lower or 'ngày' in c_lower: col_mapping[col] = 'ngay'
        elif 'công' in c_lower or 'số công' in c_lower: col_mapping[col] = 'so_cong'
        elif 'khối lượng' in c_lower: col_mapping[col] = 'klcv'
        elif 'thành tiền' in c_lower: col_mapping[col] = 'thanh_tien'
        elif 'mã vật tư' in c_lower or 'mã vt' in c_lower: col_mapping[col] = 'ma_vt'
        elif 'số lượng' in c_lower: col_mapping[col] = 'so_luong'
        elif 'đơn giá' in c_lower: col_mapping[col] = 'don_gia'
        elif 'ttien' in c_lower or 't.tiền' in c_lower: col_mapping[col] = 'thanh_tien'
        elif c_lower == 'đội': col_mapping[col] = 'doi_name'

    df = df.rename(columns=col_mapping)
    return df

class PhedataProcessor:
    def __init__(self):
        self.conn = pool.getconn()
        self.doi_dict = build_dim_doi(self.conn)
        self.lo_dict = build_dim_lo(self.conn)
        self.cv_dict = build_dim_cv(self.conn)
        self.vt_dict = build_dim_vt(self.conn)
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT farm_id FROM dim_farm WHERE farm_code = 'Farm 157'")
                self.farm_id = cur.fetchone()[0]
        except:
            self.farm_id = 2
            
        self.df_nhatky = []
        self.df_vattu = []
        
        # Thống kê
        self.missing = {
            'lo': set(), 'cv': set(), 'vt': set(), 'doi': set()
        }
        
    def _map(self, val, map_dict, miss_type):
        if not val: return None
        v = str(val).strip()
        mapped = map_dict.get(v)
        if not mapped:
            self.missing[miss_type].add(v)
            return None
        return mapped

    def process_nhatky_tong_hop(self, df):
        df = transform_dataframe(df)
        
        # Bảng Tổng Hợp theo Định Dạng Kế Toán
        if 'ngay' not in df.columns or ('so_cong' not in df.columns and 'thanh_tien' not in df.columns):
            print("  ⚠️ Bảng rỗng không đúng chuẩn NK Tổng Hợp")
            return
            
        for _, row in df.iterrows():
            ngay = None
            if 'ngay' in row and row['ngay']:
                try: 
                    ngay = pd.to_datetime(str(row['ngay']), dayfirst=True).strftime('%Y-%m-%d')
                except: pass
            if not ngay: continue

            lo_id = self._map(row.get('lo_name'), self.lo_dict, 'lo')
            cv_id = self._map(row.get('ma_cv'), self.cv_dict, 'cv')
            doi_id = self._map(row.get('doi_name', 'Tổng Hợp Điện/Nước/CG'), self.doi_dict, 'doi')
            
            try: so_cong = float(str(row.get('so_cong', 0)).replace(',',''))
            except: so_cong = 0
            
            try: tt = float(str(row.get('thanh_tien', 0)).replace(',',''))
            except: tt = 0
            
            if so_cong == 0 and tt == 0: continue
            
            self.df_nhatky.append({
                'farm_id': self.farm_id,
                'ngay': ngay,
                'doi_id': doi_id,
                'lo_id': lo_id,
                'cong_viec_id': cv_id,
                'so_cong': so_cong,
                'klcv': 0,
                'thanh_tien': tt,
                'is_khoan': False,
                'is_ho_tro': False
            })

    def process_vattu_tong_hop(self, df):
        df = transform_dataframe(df)
        
        if 'ngay' not in df.columns or 'ma_vt' not in df.columns:
            print("  ⚠️ Bảng VT không đúng chuẩn")
            return
            
        for _, row in df.iterrows():
            ngay = None
            if 'ngay' in row and row['ngay']:
                try: ngay = pd.to_datetime(str(row['ngay']), dayfirst=True).strftime('%Y-%m-%d')
                except: pass
            if not ngay: continue

            lo_id = self._map(row.get('lo_name'), self.lo_dict, 'lo')
            cv_id = self._map(row.get('ma_cv'), self.cv_dict, 'cv')
            vt_id = self._map(row.get('ma_vt'), self.vt_dict, 'vt')
            
            try: tong = float(str(row.get('thanh_tien', 0)).replace(',',''))
            except: tong = 0
            
            if tong == 0: continue
            
            self.df_vattu.append({
                'farm_id': self.farm_id,
                'lo_id': lo_id,
                'cong_viec_id': cv_id,
                'vat_tu_id': vt_id,
                'ngay': ngay,
                'so_luong': 0,
                'don_gia': 0,
                'thanh_tien': tong
            })

    def insert_db(self):
        print("\n⏳ Đang xoá dữ liệu cũ của Farm 157...")
        xoa_toan_bo_du_lieu_157(self.conn)
        
        insert_nk = """
            INSERT INTO fact_nhat_ky_san_xuat (
                farm_id, ngay, doi_id, lo_id, cong_viec_id, 
                so_cong, klcv, thanh_tien, is_khoan, is_ho_tro
            ) VALUES %s
        """
        
        insert_vt = """
            INSERT INTO fact_vat_tu (
                farm_id, lo_id, cong_viec_id, vat_tu_id,
                ngay, so_luong, don_gia, thanh_tien
            ) VALUES %s
        """
        
        try:
            with self.conn.cursor() as cur:
                if self.df_nhatky:
                    values_nk = [(
                        r['farm_id'], r['ngay'], r['doi_id'], r['lo_id'], r['cong_viec_id'],
                        r['so_cong'], r['klcv'], r['thanh_tien'], r['is_khoan'], r['is_ho_tro']
                    ) for r in self.df_nhatky]
                    psycopg2.extras.execute_values(cur, insert_nk, values_nk)
                    print(f"✅ Đã chèn {len(values_nk)} dòng Nhật ký")
                    
                if self.df_vattu:
                    values_vt = [(
                        r['farm_id'], r['lo_id'], r['cong_viec_id'], r['vat_tu_id'],
                        r['ngay'], r['so_luong'], r['don_gia'], r['thanh_tien']
                    ) for r in self.df_vattu]
                    psycopg2.extras.execute_values(cur, insert_vt, values_vt)
                    print(f"✅ Đã chèn {len(values_vt)} dòng Vật tư")
                    
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Lỗi chèn dữ liệu: {e}")
            raise e

    def close(self):
        pool.putconn(self.conn)

def main():
    # ID File "SỔ KẾ TOÁN THÁNG" của 157
    DOC_ID = "1e8-7l9rA8L6H9E2K3m4xZ1wV5cTnB_yVpQrP1VbXkA8" 
    
    print("===========================================")
    print("🚀 BẮT ĐẦU ĐỒNG BỘ FARM 157 (TỔNG HỢP)")
    print("===========================================")
    
    processor = PhedataProcessor()
    try:
        wb = gc.open_by_key(DOC_ID)
        
        # Nhật Ký Công
        print("\n▶️ Xử lý SHEET: NHẬT KÝ CHI CÔNG")
        df_nk = download_sheet(wb, "TH NKCG T3", start_row=2)
        if not df_nk.empty:
            processor.process_nhatky_tong_hop(df_nk)
            
        print("\n▶️ Xử lý SHEET: XUẤT KHO VẬT TƯ")
        df_vt = download_sheet(wb, "TH VT T3", start_row=2)
        if not df_vt.empty:
            processor.process_vattu_tong_hop(df_vt)
            
        processor.insert_db()
        
        for k, v in processor.missing.items():
            if v: print(f"⚠️ Thiếu mapping {k.upper()}: {v}")
            
    except Exception as e:
        print(f"❌ Lỗi xử lý: {e}")
    finally:
        processor.close()

if __name__ == "__main__":
    main()