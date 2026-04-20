import streamlit as st
import psycopg2
import psycopg2.extras
import psycopg2.pool
import pandas as pd


@st.cache_resource
def _get_pool():
    """Tạo connection pool (cache theo resource → chỉ tạo 1 lần)."""
    cfg = st.secrets["supabase"]
    return psycopg2.pool.SimpleConnectionPool(
        minconn=1, maxconn=5,
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["user"], password=cfg["password"],
        sslmode="require", connect_timeout=10,
    )


def query(sql: str, params=None) -> pd.DataFrame:
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])
    finally:
        pool.putconn(conn)


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
def load_seasons(farm_ids: tuple):
    """Load danh sách vụ có sẵn cho các farm đã chọn."""
    if not farm_ids:
        return pd.DataFrame()
    ph = ",".join(["%s"] * len(farm_ids))
    return query(f"""
        SELECT lo_id, lo_code, farm, vu, loai_trong, vu_start, vu_end
        FROM v_season_date_ranges
        WHERE lo_id IN (
            SELECT lo_id FROM dim_lo WHERE farm_id IN ({ph})
        )
        ORDER BY farm, lo_code, vu
    """, list(farm_ids))

@st.cache_data(ttl=300)
def load_lo_vu_summary(farm_ids: tuple, s, e, lo_types=(), sel_los=()):
    """Tổng chi phí theo Lô & Vụ — JOIN date-based với v_season_date_ranges."""
    ph = ",".join(["%s"] * len(farm_ids))
    conds_c = [f"nk.farm_id IN ({ph})"]
    conds_v = [f"vt.farm_id IN ({ph})"]
    params_c = list(farm_ids)
    params_v = list(farm_ids)
    conds_c.append("nk.ngay BETWEEN %s AND %s"); params_c += [str(s), str(e)]
    conds_v.append("vt.ngay BETWEEN %s AND %s"); params_v += [str(s), str(e)]
    if lo_types:
        ph_lt = ",".join(["%s"] * len(lo_types))
        conds_c.append(f"lc.lo_type IN ({ph_lt})"); params_c += list(lo_types)
        conds_v.append(f"lv.lo_type IN ({ph_lt})"); params_v += list(lo_types)
    if sel_los:
        ph_lo = ",".join(["%s"] * len(sel_los))
        conds_c.append(f"lc.lo_code IN ({ph_lo})"); params_c += list(sel_los)
        conds_v.append(f"lv.lo_code IN ({ph_lo})"); params_v += list(sel_los)

    cong_df = query(f"""
        SELECT COALESCE(lc.lo_code, 'Khác') as lo_code, fc.farm_code,
               COALESCE(vsr.vu, 'Chưa có vụ') as vu,
               SUM(nk.thanh_tien) as tien_cong,
               SUM(nk.so_cong)    as so_cong
        FROM fact_nhat_ky_san_xuat nk
        LEFT JOIN dim_lo   lc ON lc.lo_id = nk.lo_id
        JOIN dim_farm fc ON fc.farm_id = nk.farm_id
        LEFT JOIN v_season_date_ranges vsr
               ON vsr.lo_id = nk.lo_id AND nk.ngay BETWEEN vsr.vu_start AND vsr.vu_end
        WHERE {' AND '.join(conds_c)}
        GROUP BY COALESCE(lc.lo_code, 'Khác'), fc.farm_code, vsr.vu
    """, params_c)

    vt_df = query(f"""
        SELECT COALESCE(lv.lo_code, 'Khác') as lo_code, fv.farm_code,
               COALESCE(vsr.vu, 'Chưa có vụ') as vu,
               SUM(vt.thanh_tien) as tien_vt
        FROM fact_vat_tu vt
        LEFT JOIN dim_lo   lv ON lv.lo_id = vt.lo_id
        JOIN dim_farm fv ON fv.farm_id = vt.farm_id
        LEFT JOIN v_season_date_ranges vsr
               ON vsr.lo_id = vt.lo_id AND vt.ngay BETWEEN vsr.vu_start AND vsr.vu_end
        WHERE {' AND '.join(conds_v)}
        GROUP BY COALESCE(lv.lo_code, 'Khác'), fv.farm_code, vsr.vu
    """, params_v)

    if cong_df.empty and vt_df.empty:
        return pd.DataFrame()
    if cong_df.empty:
        merged = vt_df.copy(); merged["tien_cong"] = 0.0; merged["so_cong"] = 0.0
    elif vt_df.empty:
        merged = cong_df.copy(); merged["tien_vt"] = 0.0
    else:
        merged = pd.merge(cong_df, vt_df, on=["lo_code", "farm_code", "vu"], how="outer").fillna(0)
    for col in ["tien_cong", "tien_vt", "so_cong"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    merged["total"] = merged["tien_cong"] + merged["tien_vt"]
    return merged.sort_values(["farm_code", "lo_code", "vu"]).reset_index(drop=True)

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
