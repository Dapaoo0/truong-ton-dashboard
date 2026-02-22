import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd

def get_conn_params():
    cfg = st.secrets["supabase"]
    return dict(host=cfg["host"], port=cfg["port"], database=cfg["database"],
                user=cfg["user"], password=cfg["password"],
                sslmode="require", connect_timeout=10)

def query(sql: str, params=None) -> pd.DataFrame:
    conn = psycopg2.connect(**get_conn_params())
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])
    finally:
        conn.close()

@st.cache_data(ttl=300)
def load_farms():
    return query("SELECT farm_id, farm_code FROM dim_farm ORDER BY farm_code")

@st.cache_data(ttl=300)
def load_filter_options(farm_ids: tuple):
    """Load lo và doi có data thực tế trong các farm đã chọn — cascade filter"""
    if not farm_ids:
        return pd.DataFrame(), pd.DataFrame()
    ph = ",".join(["%s"] * len(farm_ids))

    lo_df = query(f"""
        SELECT DISTINCT l.lo_code, l.lo_type, f.farm_code
        FROM fact_nhat_ky_san_xuat nk
        JOIN dim_lo l ON l.lo_id = nk.lo_id
        JOIN dim_farm f ON f.farm_id = nk.farm_id
        WHERE nk.farm_id IN ({ph})
        ORDER BY l.lo_type, l.lo_code
    """, list(farm_ids))

    doi_df = query(f"""
        SELECT DISTINCT d.doi_code,
               array_to_string(array_agg(DISTINCT f.farm_code ORDER BY f.farm_code), ', ') as farms
        FROM fact_nhat_ky_san_xuat nk
        JOIN dim_doi d ON d.doi_id = nk.doi_id
        JOIN dim_farm f ON f.farm_id = nk.farm_id
        WHERE nk.farm_id IN ({ph})
        GROUP BY d.doi_code
        ORDER BY d.doi_code
    """, list(farm_ids))

    return lo_df, doi_df

@st.cache_data(ttl=300)
def load_date_range(farm_ids: tuple, has_dinh_muc: bool = False):
    ph = ",".join(["%s"] * len(farm_ids))
    extra = "AND dinh_muc > 0" if has_dinh_muc else ""
    r = query(f"SELECT MIN(ngay) as mn, MAX(ngay) as mx FROM fact_nhat_ky_san_xuat WHERE farm_id IN ({ph}) {extra}", list(farm_ids))
    return pd.to_datetime(r["mn"][0]), pd.to_datetime(r["mx"][0])

def format_vnd(val) -> str:
    if pd.isna(val): return "—"
    return f"{val:,.0f} VND"

def format_pct(val) -> str:
    if pd.isna(val): return "—"
    return f"{val:.1f}%"