import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import query, load_farms, load_filter_options, load_date_range, format_vnd
from style import (inject_css, page_header, kpi_row, section_header, tip,
                   drill_badge, apply_plotly_style, chart_or_table,
                   C, BAR_CONG, BAR_VAT_TU)

st.set_page_config(page_title="Chi Phí", page_icon="💰", layout="wide")
inject_css()

# ── Extra CSS cho farm cards ──────────────────
TX = C["text"]; TM = C["text_muted"]; TS = C["text_sub"]
SF = C["surface"]; SF2 = C["surface2"]; BD = C["border"]; BD2 = C["border2"]
GRN = C["green"]; AMB = C["amber"]; BLU = C["blue"]

st.markdown(f"""
<style>
div[data-testid="stButton"] > button {{
    width: 100%;
    background: {SF} !important;
    border: 1px solid {BD} !important;
    border-radius: 10px !important;
    padding: 18px 12px !important;
    color: {TS} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
    cursor: pointer !important;
    text-align: center !important;
    height: auto !important;
    white-space: pre-wrap !important;
    line-height: 1.6 !important;
}}
div[data-testid="stButton"] > button:hover {{
    background: {SF2} !important;
    border-color: {GRN} !important;
    color: {TX} !important;
    transform: translateY(-1px) !important;
}}
div[data-testid="stButton"] > button[kind="primary"] {{
    border-color: {AMB} !important;
    border-width: 2px !important;
    background: {C["amber_pale"]} !important;
    color: {AMB} !important;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for k in ["cp_farm", "cp_doi", "cp_lo", "flt_farm_cv", "flt_doi_cv", "flt_lo_cv", "flt_hm_cv"]:
    if k not in st.session_state:
        st.session_state[k] = [] if k.startswith("flt_") else None

if "flt_search_cv" not in st.session_state:
    st.session_state["flt_search_cv"] = ""

def clear_all():
    st.session_state.cp_farm = st.session_state.cp_doi = st.session_state.cp_lo = None

def to_num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def fmt_m(val):
    if val >= 1e9: return f"{val/1e9:.1f} tỷ"
    if val >= 1e6: return f"{val/1e6:.0f}M"
    return f"{val:,.0f}"

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def multiselect_all(label, options, key):
    c1, c2 = st.columns([4, 1])
    with c2: all_on = st.checkbox("Tất cả", value=True, key=f"all_{key}")
    with c1: return st.multiselect(label, options,
                                   default=list(options) if all_on else [], key=key)

with st.sidebar:
    st.markdown(f'<div style="font-size:13px;font-weight:600;color:{TX};padding:10px 0 6px">🔍 Bộ lọc</div>',
                unsafe_allow_html=True)
    farms_df = load_farms()
    sel_farms = multiselect_all("Farm", farms_df["farm_code"].tolist(), "farm_cp")
    if not sel_farms:
        st.warning("Chọn ít nhất 1 farm"); st.stop()
    farm_ids = tuple(farms_df[farms_df["farm_code"].isin(sel_farms)]["farm_id"].tolist())

    min_d, max_d = load_date_range(farm_ids)
    dr = st.date_input("Thời gian", (min_d, max_d),
                       min_value=min_d, max_value=max_d, key="date_cp")
    if len(dr) != 2: st.stop()
    start_d, end_d = dr

    lo_df, doi_df = load_filter_options(farm_ids)
    lo_type_opts = sorted(lo_df["lo_type"].dropna().unique())
    sel_lo_types = multiselect_all("Loại lô", lo_type_opts, "lotype_cp")
    lo_opts = sorted(lo_df[lo_df["lo_type"].isin(sel_lo_types)]["lo_code"]
                     .dropna().unique()) if sel_lo_types else []
    sel_los = st.multiselect("Lô", lo_opts, default=[], key="lo_cp",
                             help="Để trống = tất cả")

    doi_df["label"] = doi_df["doi_code"] + doi_df["farms"].apply(
        lambda f: f" ({f})" if "," in f else "")
    doi_labels = dict(zip(doi_df["doi_code"], doi_df["label"]))
    sel_dois = st.multiselect("Đội", doi_df["doi_code"].tolist(),
                               format_func=lambda x: doi_labels.get(x, x),
                               default=[], key="doi_cp", help="Để trống = tất cả")
    show_ht = st.checkbox("Bao gồm công hỗ trợ", value=True, key="ht_cp")

    st.markdown("---")
    drills = [(k, v) for k, v in [("Farm", st.session_state.cp_farm),
                                    ("Đội",  st.session_state.cp_doi),
                                    ("Lô",   st.session_state.cp_lo)] if v]
    if drills:
        st.markdown(f'<div style="font-size:10px;font-weight:600;'
                    f'text-transform:uppercase;color:{TM}">Drill đang bật</div>',
                    unsafe_allow_html=True)
        for lbl, val in drills:
            drill_badge(lbl, val, f"{lbl}_{val}", clear_all)

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_cong(farm_ids, s, e, lo_types, sel_los, sel_dois, show_ht):
    conds = [f"nk.farm_id IN ({','.join(['%s']*len(farm_ids))})"]
    params = list(farm_ids)
    conds.append("nk.ngay BETWEEN %s AND %s"); params += [str(s), str(e)]
    if lo_types: conds.append(f"l.lo_type IN ({','.join(['%s']*len(lo_types))})"); params += list(lo_types)
    if sel_los:  conds.append(f"l.lo_code IN ({','.join(['%s']*len(sel_los))})");  params += list(sel_los)
    if sel_dois: conds.append(f"d.doi_code IN ({','.join(['%s']*len(sel_dois))})"); params += list(sel_dois)
    if not show_ht: conds.append("nk.is_ho_tro = FALSE")
    return query(f"""
        SELECT f.farm_code, l.lo_code, d.doi_code,
               -- FIX: cong_doan nằm trong dim_cong_viec, không phải fact table
               COALESCE(NULLIF(TRIM(cv.cong_doan),''),'Không ghi') as cong_doan,
               COALESCE(NULLIF(TRIM(cv.ten_cong_viec),''),'Không ghi') as ten_cong_viec,
               DATE_TRUNC('month',nk.ngay)::date as thang,
               nk.so_cong, nk.thanh_tien, nk.is_ho_tro
        FROM fact_nhat_ky_san_xuat nk
        JOIN dim_farm f ON f.farm_id=nk.farm_id
        JOIN dim_lo   l ON l.lo_id=nk.lo_id
        JOIN dim_doi  d ON d.doi_id=nk.doi_id
        JOIN dim_cong_viec cv ON cv.cong_viec_id=nk.cong_viec_id
        WHERE {' AND '.join(conds)}
    """, params)

@st.cache_data(ttl=300)
def load_vt(farm_ids, s, e, lo_types, sel_los):
    conds = [f"vt.farm_id IN ({','.join(['%s']*len(farm_ids))})"]
    params = list(farm_ids)
    conds.append("vt.ngay BETWEEN %s AND %s"); params += [str(s), str(e)]
    if lo_types: conds.append(f"l.lo_type IN ({','.join(['%s']*len(lo_types))})"); params += list(lo_types)
    if sel_los:  conds.append(f"l.lo_code IN ({','.join(['%s']*len(sel_los))})");  params += list(sel_los)
    return query(f"""
        SELECT f.farm_code, l.lo_code,
               -- FIX: loai_vat_tu chỉ có trong dim_vat_tu (v), không có trong fact_vat_tu
               COALESCE(NULLIF(TRIM(v.loai_vat_tu), ''), 'Không xác định') as loai_vat_tu,
               COALESCE(NULLIF(TRIM(v.ten_vat_tu),''), 'Không xác định') as ten_vat_tu,
               DATE_TRUNC('month',vt.ngay)::date as thang,
               vt.thanh_tien
        FROM fact_vat_tu vt
        JOIN dim_farm f ON f.farm_id=vt.farm_id
        JOIN dim_lo   l ON l.lo_id=vt.lo_id
        LEFT JOIN dim_vat_tu v ON v.vat_tu_id=vt.vat_tu_id
        WHERE {' AND '.join(conds)}
    """, params)

@st.cache_data(ttl=300)
def load_lo_doi_map(farm_ids):
    return query(f"""
        SELECT l.lo_code, d.doi_code, f.farm_code
        FROM dim_lo_doi ld
        JOIN dim_lo   l ON l.lo_id  = ld.lo_id
        JOIN dim_doi  d ON d.doi_id = ld.doi_id
        JOIN dim_farm f ON f.farm_id = l.farm_id
        WHERE f.farm_id IN ({','.join(['%s']*len(farm_ids))})
    """, list(farm_ids))

raw_c = load_cong(farm_ids, start_d, end_d,
                  tuple(sel_lo_types), tuple(sel_los), tuple(sel_dois), show_ht)
raw_v = load_vt(farm_ids, start_d, end_d, tuple(sel_lo_types), tuple(sel_los))
to_num(raw_c, ["thanh_tien", "so_cong"])
to_num(raw_v, ["thanh_tien"])

lo_doi_map_df = load_lo_doi_map(farm_ids)
_doi_to_los: dict = {}
if not lo_doi_map_df.empty:
    for _, row in lo_doi_map_df.iterrows():
        _doi_to_los.setdefault(row["doi_code"], set()).add(row["lo_code"])

def apply_drill(df):
    d = df.copy()
    if st.session_state.cp_farm and "farm_code" in d.columns:
        d = d[d["farm_code"] == st.session_state.cp_farm]
    if st.session_state.cp_doi:
        if "doi_code" in d.columns:
            d = d[d["doi_code"] == st.session_state.cp_doi]
        elif "lo_code" in d.columns:
            los_of_doi = _doi_to_los.get(st.session_state.cp_doi, set())
            if los_of_doi:
                d = d[d["lo_code"].isin(los_of_doi)]
            else:
                d = d.iloc[0:0]
    if st.session_state.cp_lo and "lo_code" in d.columns:
        d = d[d["lo_code"] == st.session_state.cp_lo]
    return d

dc, dv = apply_drill(raw_c), apply_drill(raw_v)
if dc.empty and dv.empty:
    st.warning("Không có dữ liệu."); st.stop()

tc = dc["thanh_tien"].sum() if not dc.empty else 0
tv = dv["thanh_tien"].sum() if not dv.empty else 0
ta = tc + tv

# ─────────────────────────────────────────────
# HEADER + KPI
# ─────────────────────────────────────────────
page_header("💰", "Chi Phí",
            f"{start_d.strftime('%d/%m/%Y')} → {end_d.strftime('%d/%m/%Y')}")

kpi_row([
    dict(label="Tổng chi phí",   value=format_vnd(ta), icon="📊", color=GRN),
    dict(label="Chi phí Công",   value=format_vnd(tc), icon="👷", color=BLU,
         delta=f"{tc/ta*100:.1f}% tổng" if ta else "", delta_positive=True),
    dict(label="Chi phí Vật tư", value=format_vnd(tv), icon="🧪", color=AMB,
         delta=f"{tv/ta*100:.1f}% tổng" if ta else "", delta_positive=True),
    dict(label="Tổng số công",
         value=f"{dc['so_cong'].sum():,.1f}" if not dc.empty else "0",
         icon="🗓️", color=C["purple"], footnote="công · ngày"),
])

# ─────────────────────────────────────────────
# XU HƯỚNG THÁNG
# ─────────────────────────────────────────────
section_header("Xu hướng theo tháng")
col1, col2 = st.columns([3, 1])
with col1:
    mc = dc.groupby("thang")["thanh_tien"].sum().reset_index()
    mv = dv.groupby("thang")["thanh_tien"].sum().reset_index() if not dv.empty else pd.DataFrame(columns=["thang","thanh_tien"])
    m = mc.merge(mv, on="thang", how="outer", suffixes=("_c", "_v")).fillna(0)
    m["ts"] = pd.to_datetime(m["thang"]).dt.strftime("%m/%Y")
    fig = go.Figure()
    fig.add_bar(x=m["ts"], y=m["thanh_tien_c"], name="Công",   marker_color=BAR_CONG,
                hovertemplate="<b>%{x}</b><br>Công: %{y:,.0f} VND<extra></extra>")
    fig.add_bar(x=m["ts"], y=m["thanh_tien_v"], name="Vật tư", marker_color=BAR_VAT_TU,
                hovertemplate="<b>%{x}</b><br>Vật tư: %{y:,.0f} VND<extra></extra>")
    fig.update_layout(barmode="stack", yaxis_tickformat=",.0f")
    apply_plotly_style(fig, 300)
    chart_or_table(fig, m.rename(columns={"ts":"Tháng","thanh_tien_c":"Công (VND)","thanh_tien_v":"Vật tư (VND)"}),
        key="monthly")
with col2:
    fig2 = go.Figure(go.Pie(
        labels=["Công", "Vật tư"], values=[tc, tv],
        marker_colors=[BAR_CONG, BAR_VAT_TU], hole=0.6,
        textinfo="percent", textfont_size=12,
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} VND<br>%{percent}<extra></extra>"))
    apply_plotly_style(fig2, 300)
    st.plotly_chart(fig2, use_container_width=True, key="pie_tong")

# ═════════════════════════════════════════════
# SECTION 1: FARM — Clickable cards
# ═════════════════════════════════════════════
section_header("Theo Farm", "click card để drill · breakdown xuất hiện bên dưới")

fc = raw_c.groupby("farm_code")["thanh_tien"].sum().reset_index()
fv_g = raw_v.groupby("farm_code")["thanh_tien"].sum().reset_index() if not raw_v.empty else pd.DataFrame(columns=["farm_code","thanh_tien"])
bf = fc.merge(fv_g, on="farm_code", how="outer", suffixes=("_c", "_v")).fillna(0)
to_num(bf, ["thanh_tien_c", "thanh_tien_v"])
bf["total"] = bf["thanh_tien_c"] + bf["thanh_tien_v"]
bf = bf.sort_values("total", ascending=False).reset_index(drop=True)

FARM_ICONS = {"Farm 126": "🌿", "Farm 157": "🌾", "Farm 195": "🌱"}
FARM_COLORS = {"Farm 126": GRN, "Farm 157": BLU, "Farm 195": C["purple"]}
n_farms = len(bf)
card_cols = st.columns(n_farms if n_farms <= 4 else 4)

for i, row in bf.iterrows():
    farm = row["farm_code"]
    total = row["total"]
    cong  = row["thanh_tien_c"]
    vt    = row["thanh_tien_v"]
    fc_pct = f"{cong/total*100:.0f}%" if total else "—"
    vt_pct = f"{vt/total*100:.0f}%"  if total else "—"
    icon  = FARM_ICONS.get(farm, "🏡")
    color = FARM_COLORS.get(farm, GRN)
    is_active = st.session_state.cp_farm == farm

    with card_cols[i % 4]:
        border_style = f"2px solid {AMB}" if is_active else f"1px solid {BD}"
        bg_style     = C["amber_pale"] if is_active else SF
        badge        = f'<span style="background:{AMB};color:{C["bg"]};border-radius:4px;font-size:9px;font-weight:700;padding:2px 6px;margin-left:6px">ĐANG CHỌN</span>' if is_active else ""

        st.markdown(
            f'<div style="background:{bg_style};border:{border_style};border-top:3px solid {color};'
            f'border-radius:10px;padding:16px;margin-bottom:4px">'
            f'<div style="font-size:22px;margin-bottom:4px">{icon}</div>'
            f'<div style="font-size:13px;font-weight:600;color:{TX}">{farm}{badge}</div>'
            f'<div style="font-size:20px;font-weight:700;color:{color};'
            f'font-family:DM Mono,monospace;margin:8px 0 4px">{fmt_m(total)} VND</div>'
            f'<div style="font-size:11px;color:{TM};line-height:1.7">'
            f'👷 Công: {fmt_m(cong)} VND ({fc_pct})<br>'
            f'🧪 Vật tư: {fmt_m(vt)} VND ({vt_pct})'
            f'</div></div>',
            unsafe_allow_html=True
        )
        btn_label = "✕ Bỏ chọn" if is_active else f"📊 Drill vào {farm}"
        if st.button(btn_label, key=f"farm_btn_{farm}",
                     type="primary" if is_active else "secondary"):
            if is_active:
                clear_all()
            else:
                st.session_state.cp_farm = farm
                st.session_state.cp_doi  = None
                st.session_state.cp_lo   = None
            st.rerun()

# ── Breakdown sau khi drill farm ──────────────
if st.session_state.cp_farm:
    active_f = st.session_state.cp_farm
    dc_f = dc.copy()
    dv_f = dv.copy()

    st.markdown(
        f'<div style="background:{C["green_pale"]};border-left:3px solid {GRN};'
        f'border-radius:0 6px 6px 0;padding:8px 14px;margin:8px 0;font-size:12px;color:{GRN}">'
        f'📊 Đang xem chi tiết: <b>{active_f}</b></div>',
        unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        mc_f = dc_f.groupby("thang")["thanh_tien"].sum().reset_index()
        mv_f = dv_f.groupby("thang")["thanh_tien"].sum().reset_index() if not dv_f.empty else pd.DataFrame(columns=["thang","thanh_tien"])
        mf = mc_f.merge(mv_f, on="thang", how="outer", suffixes=("_c","_v")).fillna(0)
        mf["ts"] = pd.to_datetime(mf["thang"]).dt.strftime("%m/%Y")
        fig_ft = go.Figure()
        fig_ft.add_bar(x=mf["ts"], y=mf["thanh_tien_c"], name="Công",   marker_color=BAR_CONG,
                       hovertemplate="<b>%{x}</b><br>Công: %{y:,.0f} VND<extra></extra>")
        fig_ft.add_bar(x=mf["ts"], y=mf["thanh_tien_v"], name="Vật tư", marker_color=BAR_VAT_TU,
                       hovertemplate="<b>%{x}</b><br>Vật tư: %{y:,.0f} VND<extra></extra>")
        fig_ft.update_layout(barmode="stack", yaxis_tickformat=",.0f",
                             title=dict(text=f"Chi phí {active_f} theo tháng",
                                        font=dict(size=12, color=TM)))
        apply_plotly_style(fig_ft, 280)
        st.plotly_chart(fig_ft, use_container_width=True, key="farm_trend")
    with col2:
        doi_f = dc_f.groupby("doi_code")["thanh_tien"].sum().reset_index()
        doi_f["thanh_tien"] = pd.to_numeric(doi_f["thanh_tien"], errors="coerce").fillna(0)
        doi_f = doi_f.sort_values("thanh_tien", ascending=True).tail(10)
        fig_fd = go.Figure(go.Bar(
            y=doi_f["doi_code"], x=doi_f["thanh_tien"], orientation="h",
            marker_color=BAR_CONG,
            hovertemplate="<b>%{y}</b><br>%{x:,.0f} VND<extra></extra>",
            text=[fmt_m(v) for v in doi_f["thanh_tien"]],
            textposition="inside", textfont=dict(color="#fff", size=10)
        ))
        fig_fd.update_layout(showlegend=False, xaxis_tickformat=",.0f",
                             yaxis=dict(automargin=True),
                             margin=dict(t=44, b=48, l=120, r=8),
                             title=dict(text=f"Top đội trong {active_f}",
                                        font=dict(size=12, color=TM)))
        apply_plotly_style(fig_fd, 280)
        st.plotly_chart(fig_fd, use_container_width=True, key="farm_doi")

st.markdown("---")

# ═════════════════════════════════════════════
# SECTION 2: LÔ — Bubble chart
# ═════════════════════════════════════════════
section_header("Theo Lô", "bubble chart: click để drill · x=công · y=vật tư · size=tổng")

lc = dc.groupby(["farm_code", "lo_code"])["thanh_tien"].sum().reset_index()
lc.columns = ["farm_code", "lo_code", "tien_c"]
if not dv.empty:
    lv = dv.groupby(["farm_code", "lo_code"])["thanh_tien"].sum().reset_index()
    lv.columns = ["farm_code", "lo_code", "tien_v"]
    bl = lc.merge(lv, on=["farm_code", "lo_code"], how="outer").fillna(0)
else:
    bl = lc.copy(); bl["tien_v"] = 0.0
bl["tien_c"] = pd.to_numeric(bl["tien_c"], errors="coerce").fillna(0)
bl["tien_v"] = pd.to_numeric(bl["tien_v"], errors="coerce").fillna(0)
bl["total"]  = bl["tien_c"] + bl["tien_v"]
bl = bl[bl["total"] > 0].reset_index(drop=True)

top40 = bl.nlargest(40, "total").reset_index(drop=True)
active_lo = st.session_state.cp_lo

farm_color_map = {
    "Farm 126": GRN, "Farm 157": BLU, "Farm 195": C["purple"]
}

tip("Bubble to = tổng chi phí cao · Vị trí nằm gần trục Y = nhiều vật tư · Gần trục X = nhiều công")

fig_bubble = go.Figure()
for farm_name, grp in top40.groupby("farm_code"):
    color = farm_color_map.get(farm_name, GRN)
    marker_colors = [AMB if row["lo_code"] == active_lo else color
                     for _, row in grp.iterrows()]
    t_max = top40["total"].max()
    t_min = top40["total"].min()
    sizes = [10 + 50 * (row["total"] - t_min) / max(t_max - t_min, 1)
             for _, row in grp.iterrows()]

    fig_bubble.add_scatter(
        x=grp["tien_c"], y=grp["tien_v"],
        mode="markers+text",
        name=farm_name,
        marker=dict(
            size=sizes,
            color=marker_colors,
            opacity=0.85,
            line=dict(width=[2 if row["lo_code"] == active_lo else 0.5
                              for _, row in grp.iterrows()],
                      color=[TX if row["lo_code"] == active_lo else "rgba(0,0,0,0.3)"
                             for _, row in grp.iterrows()])
        ),
        text=[row["lo_code"] for _, row in grp.iterrows()],
        textposition="top center",
        textfont=dict(color=TM, size=9),
        customdata=[[row["lo_code"], row["farm_code"],
                     row["total"], row["tien_c"], row["tien_v"]]
                    for _, row in grp.iterrows()],
        hovertemplate=(
            "<b>%{customdata[1]} · Lô %{customdata[0]}</b><br>"
            "Tổng: %{customdata[2]:,.0f} VND<br>"
            "Công: %{customdata[3]:,.0f} VND<br>"
            "Vật tư: %{customdata[4]:,.0f} VND<extra></extra>"
        ),
    )

fig_bubble.update_layout(
    xaxis=dict(title="Chi phí Công (VND)", tickformat=",.0f"),
    yaxis=dict(title="Chi phí Vật tư (VND)", tickformat=",.0f"),
    title=dict(text="Chi phí Công vs Vật tư theo Lô (click bubble để drill)",
               font=dict(size=12, color=TM)),
)
apply_plotly_style(fig_bubble, 480)
ev_bubble = chart_or_table(fig_bubble, top40[["farm_code","lo_code","tien_c","tien_v","total"]].rename(
    columns={"farm_code":"Farm","lo_code":"Lô","tien_c":"Công (VND)","tien_v":"Vật tư (VND)","total":"Tổng (VND)"}),
    key="lo_bubble", on_select="rerun", selection_mode="points")
if ev_bubble and ev_bubble.selection and ev_bubble.selection.get("points"):
    pt = ev_bubble.selection.get("points")[0]
    lo_clicked = pt.get("customdata", [None])[0] if pt.get("customdata") else None
    if lo_clicked and lo_clicked != st.session_state.cp_lo:
        st.session_state.cp_lo   = lo_clicked
        st.session_state.cp_farm = None
        st.session_state.cp_doi  = None

# ── Breakdown sau khi drill lô ────────────────
if st.session_state.cp_lo:
    active_lo_name = st.session_state.cp_lo
    lo_row = bl[bl["lo_code"] == active_lo_name]
    lo_farm = lo_row["farm_code"].values[0] if not lo_row.empty else ""

    st.markdown(
        f'<div style="background:{C["green_pale"]};border-left:3px solid {GRN};'
        f'border-radius:0 6px 6px 0;padding:8px 14px;margin:8px 0;font-size:12px;color:{GRN}">'
        f'📊 Đang xem chi tiết: <b>{lo_farm} · Lô {active_lo_name}</b></div>',
        unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        mc_lo = dc[dc["lo_code"] == active_lo_name].groupby("thang")["thanh_tien"].sum().reset_index()
        mv_lo = dv[dv["lo_code"] == active_lo_name].groupby("thang")["thanh_tien"].sum().reset_index() if not dv.empty else pd.DataFrame(columns=["thang","thanh_tien"])
        mlo = mc_lo.merge(mv_lo, on="thang", how="outer", suffixes=("_c","_v")).fillna(0)
        mlo["ts"] = pd.to_datetime(mlo["thang"]).dt.strftime("%m/%Y")
        fig_lot = go.Figure()
        fig_lot.add_bar(x=mlo["ts"], y=mlo["thanh_tien_c"], name="Công",   marker_color=BAR_CONG,
                        hovertemplate="<b>%{x}</b><br>Công: %{y:,.0f} VND<extra></extra>")
        fig_lot.add_bar(x=mlo["ts"], y=mlo["thanh_tien_v"], name="Vật tư", marker_color=BAR_VAT_TU,
                        hovertemplate="<b>%{x}</b><br>Vật tư: %{y:,.0f} VND<extra></extra>")
        fig_lot.update_layout(barmode="stack", yaxis_tickformat=",.0f",
                              title=dict(text=f"Lô {active_lo_name} — chi phí theo tháng",
                                         font=dict(size=12, color=TM)))
        apply_plotly_style(fig_lot, 280)
        st.plotly_chart(fig_lot, use_container_width=True, key="lo_trend")
    with col2:
        cd_lo = dc[dc["lo_code"] == active_lo_name].groupby("cong_doan")["thanh_tien"].sum().reset_index()
        cd_lo["thanh_tien"] = pd.to_numeric(cd_lo["thanh_tien"], errors="coerce").fillna(0)
        cd_lo = cd_lo.sort_values("thanh_tien", ascending=True).tail(10)
        fig_locd = go.Figure(go.Bar(
            y=cd_lo["cong_doan"], x=cd_lo["thanh_tien"], orientation="h",
            marker_color=BAR_CONG,
            hovertemplate="<b>%{y}</b><br>%{x:,.0f} VND<extra></extra>",
        ))
        fig_locd.update_layout(showlegend=False, xaxis_tickformat=",.0f",
                               yaxis=dict(automargin=True),
                               margin=dict(t=44, b=48, l=140, r=8),
                               title=dict(text=f"Công đoạn trong Lô {active_lo_name}",
                                          font=dict(size=12, color=TM)))
        apply_plotly_style(fig_locd, 280)
        st.plotly_chart(fig_locd, use_container_width=True, key="lo_cd")

st.markdown("---")

# ═════════════════════════════════════════════
# SECTION 3: ĐỘI — Stacked bar click drill
# ═════════════════════════════════════════════
section_header("Theo Đội", "click bar để drill · breakdown xuất hiện bên dưới")

ht_raw = dc.groupby(["doi_code", "is_ho_tro"])["thanh_tien"].sum().reset_index()
ht_raw["thanh_tien"] = pd.to_numeric(ht_raw["thanh_tien"], errors="coerce").fillna(0)
pv = ht_raw.pivot(index="doi_code", columns="is_ho_tro",
                  values="thanh_tien").fillna(0).reset_index()
pv.columns.name = None
if True  not in pv.columns: pv[True]  = 0.0
if False not in pv.columns: pv[False] = 0.0
pv = pv.rename(columns={False: "Chính chủ", True: "Hỗ trợ"})
pv["total"] = pv["Chính chủ"] + pv["Hỗ trợ"]
pv = pv[pv["total"] > 0].sort_values("total", ascending=True).reset_index(drop=True)
active_doi = st.session_state.cp_doi

fig_doi = go.Figure()
fig_doi.add_bar(
    y=pv["doi_code"], x=pv["Chính chủ"], name="Chính chủ",
    orientation="h",
    marker_color=[AMB if d == active_doi else BAR_CONG for d in pv["doi_code"]],
    hovertemplate="<b>%{y}</b> — Chính chủ<br>%{x:,.0f} VND<extra></extra>",
)
fig_doi.add_bar(
    y=pv["doi_code"], x=pv["Hỗ trợ"], name="Hỗ trợ",
    orientation="h",
    marker_color=[AMB if d == active_doi else C["red"] for d in pv["doi_code"]],
    opacity=0.7,
    hovertemplate="<b>%{y}</b> — Hỗ trợ<br>%{x:,.0f} VND<extra></extra>",
)
_max_label_len = max(len(str(d)) for d in pv["doi_code"]) if not pv.empty else 8
_l_margin = max(80, _max_label_len * 7)

fig_doi.update_layout(
    barmode="stack", xaxis_tickformat=",.0f",
    title=dict(text="Chi phí Công theo Đội — Chính chủ / Hỗ trợ",
               font=dict(size=12, color=TM)),
    yaxis=dict(automargin=True),
    margin=dict(t=44, b=48, l=_l_margin, r=8),
)
apply_plotly_style(fig_doi, max(400, len(pv) * 26))
ev_doi = chart_or_table(fig_doi, pv[["doi_code","Chính chủ","Hỗ trợ","total"]].rename(
    columns={"doi_code":"Đội","total":"Tổng (VND)"}),
    key="doi_bar", on_select="rerun", selection_mode="points")
if ev_doi and ev_doi.selection and ev_doi.selection.get("points"):
    clicked = ev_doi.selection.get("points")[0].get("y")
    if clicked and clicked != st.session_state.cp_doi:
        st.session_state.cp_doi  = clicked
        st.session_state.cp_farm = None
        st.session_state.cp_lo   = None

# ── Breakdown sau khi drill đội ───────────────
if st.session_state.cp_doi:
    active_doi_name = st.session_state.cp_doi
    st.markdown(
        f'<div style="background:{C["green_pale"]};border-left:3px solid {GRN};'
        f'border-radius:0 6px 6px 0;padding:8px 14px;margin:8px 0;font-size:12px;color:{GRN}">'
        f'📊 Đang xem chi tiết: <b>Đội {active_doi_name}</b></div>',
        unsafe_allow_html=True)

    dc_doi = dc[dc["doi_code"] == active_doi_name].copy()
    col1, col2 = st.columns(2)
    with col1:
        doi_farm = dc_doi.groupby("farm_code")["thanh_tien"].sum().reset_index()
        doi_farm["thanh_tien"] = pd.to_numeric(doi_farm["thanh_tien"], errors="coerce").fillna(0)
        fig_df = go.Figure(go.Bar(
            x=doi_farm["farm_code"], y=doi_farm["thanh_tien"],
            marker_color=[farm_color_map.get(f, GRN) for f in doi_farm["farm_code"]],
            text=[fmt_m(v) for v in doi_farm["thanh_tien"]],
            textposition="outside", textfont=dict(color=TS, size=11),
            hovertemplate="<b>%{x}</b><br>%{y:,.0f} VND<extra></extra>",
        ))
        fig_df.update_layout(showlegend=False, yaxis_tickformat=",.0f",
                             title=dict(text=f"Đội {active_doi_name} theo Farm",
                                        font=dict(size=12, color=TM)))
        apply_plotly_style(fig_df, 260)
        st.plotly_chart(fig_df, use_container_width=True, key="doi_farm_break")
    with col2:
        doi_thang = dc_doi.groupby("thang")["thanh_tien"].sum().reset_index()
        doi_thang["ts"] = pd.to_datetime(doi_thang["thang"]).dt.strftime("%m/%Y")
        fig_dt = go.Figure()
        fig_dt.add_scatter(x=doi_thang["ts"], y=doi_thang["thanh_tien"],
                           mode="lines+markers", line=dict(color=BAR_CONG, width=2.5),
                           marker=dict(size=7), fill="tozeroy",
                           fillcolor="rgba(63,185,80,0.08)",
                           hovertemplate="<b>%{x}</b><br>%{y:,.0f} VND<extra></extra>")
        fig_dt.update_layout(yaxis_tickformat=",.0f",
                             title=dict(text=f"Đội {active_doi_name} — xu hướng tháng",
                                        font=dict(size=12, color=TM)))
        apply_plotly_style(fig_dt, 260)
        st.plotly_chart(fig_dt, use_container_width=True, key="doi_trend")

st.markdown("---")

# ═════════════════════════════════════════════
# SECTION 4: CƠ CẤU — Sunburst
# ═════════════════════════════════════════════
section_header("Cơ cấu chi phí chi tiết",
               "click mảnh để zoom · click giữa để quay lại")

SB_COLORS = [GRN, BLU, C["purple"], AMB, C["red"],
             "#79C0FF", "#A5F3B0", "#FCD34D", "#F97583", "#BC8CFF",
             "#58A6FF", "#3FB950", "#F0A800", "#8B949E", "#E6EDF3"]
col1, col2 = st.columns(2)

with col1:
    dc_sb = dc[dc["cong_doan"].notna()].copy()
    dc_sb["thanh_tien"] = pd.to_numeric(dc_sb["thanh_tien"], errors="coerce").fillna(0)
    dc_sb = dc_sb[dc_sb["thanh_tien"] > 0]
    if not dc_sb.empty:
        fig_sb_c = px.sunburst(dc_sb, path=["farm_code", "doi_code", "cong_doan"],
                               values="thanh_tien", color_discrete_sequence=SB_COLORS)
        fig_sb_c.update_traces(
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} VND<br>"
                          "%{percentParent} của %{parent}<extra></extra>",
            insidetextorientation="radial")
        fig_sb_c.update_layout(
            title=dict(text="Chi phí Công: Farm → Đội → Công đoạn",
                       font=dict(size=12, color=TM)))
        apply_plotly_style(fig_sb_c, 420)
        chart_or_table(fig_sb_c, dc_sb.groupby(["farm_code","doi_code","cong_doan"])["thanh_tien"].sum().reset_index().rename(
            columns={"farm_code":"Farm","doi_code":"Đội","cong_doan":"Công đoạn","thanh_tien":"Chi phí (VND)"}),
            key="sb_cong")
    else:
        st.info("Không có dữ liệu công đoạn.")

with col2:
    dv_sb = dv.copy()
    dv_sb["thanh_tien"] = pd.to_numeric(dv_sb["thanh_tien"], errors="coerce").fillna(0)
    dv_sb = dv_sb[dv_sb["thanh_tien"] > 0]
    if not dv_sb.empty:
        fig_sb_v = px.sunburst(dv_sb, path=["farm_code", "lo_code", "loai_vat_tu"],
                               values="thanh_tien", color_discrete_sequence=SB_COLORS[::-1])
        fig_sb_v.update_traces(
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} VND<br>"
                          "%{percentParent} của %{parent}<extra></extra>",
            insidetextorientation="radial")
        fig_sb_v.update_layout(
            title=dict(text="Chi phí Vật tư: Farm → Lô → Loại vật tư",
                       font=dict(size=12, color=TM)))
        apply_plotly_style(fig_sb_v, 420)
        chart_or_table(fig_sb_v, dv_sb.groupby(["farm_code","lo_code","loai_vat_tu"])["thanh_tien"].sum().reset_index().rename(
            columns={"farm_code":"Farm","lo_code":"Lô","loai_vat_tu":"Loại VT","thanh_tien":"Chi phí (VND)"}),
            key="sb_vattu")
    else:
        st.info("Không có dữ liệu vật tư.")

# ═════════════════════════════════════════════
# CHI TIẾT HẠNG MỤC
# ═════════════════════════════════════════════
section_header("Chi tiết hạng mục chi phí",
               "top 20 · click tiêu đề cột để sort · tự lọc theo drill đang bật")

def _drill_label(include_doi=True):
    parts = []
    if st.session_state.cp_farm: parts.append(st.session_state.cp_farm)
    if include_doi and st.session_state.cp_doi:
        parts.append(f"Đội {st.session_state.cp_doi}")
    if st.session_state.cp_lo:   parts.append(f"Lô {st.session_state.cp_lo}")
    return " · ".join(parts) if parts else "Toàn bộ"

PAGE_SIZE = 1000

for _pk in ["cv_page", "vt_page"]:
    if _pk not in st.session_state:
        st.session_state[_pk] = 0

def pagination_controls(total_rows, page_key, page_size=PAGE_SIZE):
    total_pages = max(1, -(-total_rows // page_size))
    page = st.session_state[page_key]
    if page >= total_pages:
        page = total_pages - 1
        st.session_state[page_key] = page

    col_info, col_prev, col_page, col_next = st.columns([4, 1, 2, 1])
    with col_info:
        start = page * page_size
        end   = min(start + page_size, total_rows)
        st.caption(f"Hiển thị **{start+1}–{end}** / {total_rows:,} dòng  ·  Trang {page+1}/{total_pages}  ·  *(click tiêu đề cột để sort)*")
    with col_prev:
        if st.button("◀ Trước", key=f"prev_{page_key}", disabled=(page == 0)):
            st.session_state[page_key] -= 1
            st.rerun()
    with col_page:
        jump = st.number_input("Trang", min_value=1, max_value=total_pages,
                               value=page + 1, step=1, key=f"jump_{page_key}",
                               label_visibility="collapsed")
        if jump - 1 != page:
            st.session_state[page_key] = jump - 1
            st.rerun()
    with col_next:
        if st.button("Tiếp ▶", key=f"next_{page_key}", disabled=(page >= total_pages - 1)):
            st.session_state[page_key] += 1
            st.rerun()
    return start, end

# ════════════════════════════════════════════
# BẢNG CÔNG VIỆC
# ════════════════════════════════════════════
lbl_cv = _drill_label(include_doi=True)
tip(f"Công việc chi tiết theo Lô — {lbl_cv}")

if not dc.empty and "ten_cong_viec" in dc.columns:
    cv_grp = (dc.groupby(["farm_code", "doi_code", "lo_code",
                           "cong_doan", "ten_cong_viec"])["thanh_tien"]
               .sum().reset_index())
    cv_grp["thanh_tien"] = pd.to_numeric(cv_grp["thanh_tien"], errors="coerce").fillna(0)
    cv_all = cv_grp[cv_grp["thanh_tien"] > 0].copy()
    total_c = dc["thanh_tien"].sum()
    cv_all["pct"] = (cv_all["thanh_tien"] / total_c * 100).round(2) if total_c else 0.0
    cv_all = cv_all.sort_values("thanh_tien", ascending=False).reset_index(drop=True)

    with st.expander("🔽 Lọc bảng Công việc", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 3])
        with fc1:
            f_farm_cv = st.multiselect("Farm", sorted(cv_all["farm_code"].unique()),
                                       default=[], key="flt_farm_cv", placeholder="Tất cả")
        with fc2:
            f_doi_cv = st.multiselect("Đội", sorted(cv_all["doi_code"].unique()),
                                      default=[], key="flt_doi_cv", placeholder="Tất cả")
        with fc3:
            f_lo_cv = st.multiselect("Lô", sorted(cv_all["lo_code"].unique()),
                                     default=[], key="flt_lo_cv", placeholder="Tất cả")
        with fc4:
            f_hm_cv = st.multiselect("Hạng mục", sorted(cv_all["cong_doan"].unique()),
                                     default=[], key="flt_hm_cv", placeholder="Tất cả")
        f_search_cv = st.text_input("Tìm tên công việc", key="flt_search_cv",
                                    placeholder="Nhập từ khoá...")

    cv_f = cv_all.copy()
    if f_farm_cv: cv_f = cv_f[cv_f["farm_code"].isin(f_farm_cv)]
    if f_doi_cv:  cv_f = cv_f[cv_f["doi_code"].isin(f_doi_cv)]
    if f_lo_cv:   cv_f = cv_f[cv_f["lo_code"].isin(f_lo_cv)]
    if f_hm_cv:   cv_f = cv_f[cv_f["cong_doan"].isin(f_hm_cv)]
    if f_search_cv:
        cv_f = cv_f[cv_f["ten_cong_viec"].str.contains(f_search_cv, case=False, na=False)]

    _cv_start, _cv_end = pagination_controls(len(cv_f), "cv_page")
    cv_show = cv_f.iloc[_cv_start:_cv_end]

    _cv_display = cv_show[["farm_code", "doi_code", "lo_code",
                            "ten_cong_viec", "cong_doan", "thanh_tien", "pct"]].rename(columns={
        "farm_code":     "Farm",
        "doi_code":      "Đội",
        "lo_code":       "Lô",
        "ten_cong_viec": "Công việc",
        "cong_doan":     "Hạng mục",
        "thanh_tien":    "Chi phí (VND)",
        "pct":           "% tổng Công",
    }).copy()
    _cv_display["Chi phí (VND)"] = _cv_display["Chi phí (VND)"].apply(lambda x: f"{int(x):,}")
    _cv_display["% tổng Công"]   = _cv_display["% tổng Công"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(_cv_display, use_container_width=True, hide_index=True, height=600)
else:
    st.info("Không có dữ liệu công việc.")

st.markdown('<div style="margin-top:28px"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════
# BẢNG VẬT TƯ
# ════════════════════════════════════════════
lbl_vt = _drill_label(include_doi=False)
doi_note = ""
if st.session_state.cp_doi:
    los_of_doi = _doi_to_los.get(st.session_state.cp_doi, set())
    doi_note = (f" · qua {len(los_of_doi)} lô của đội này"
                if los_of_doi else " · đội này không có lô trong dim_lo_doi")
tip(f"Vật tư chi tiết theo Lô — {lbl_vt}{doi_note}")

if not dv.empty and "ten_vat_tu" in dv.columns:
    vt_grp = (dv.groupby(["farm_code", "lo_code",
                           "loai_vat_tu", "ten_vat_tu"])["thanh_tien"]
               .sum().reset_index())
    vt_grp["thanh_tien"] = pd.to_numeric(vt_grp["thanh_tien"], errors="coerce").fillna(0)
    vt_all = vt_grp[vt_grp["thanh_tien"] > 0].copy()
    total_v = dv["thanh_tien"].sum()
    vt_all["pct"] = (vt_all["thanh_tien"] / total_v * 100).round(2) if total_v else 0.0
    vt_all = vt_all.sort_values("thanh_tien", ascending=False).reset_index(drop=True)

    with st.expander("🔽 Lọc bảng Vật tư", expanded=False):
        fv1, fv2, fv3 = st.columns([2, 2, 3])
        with fv1:
            f_farm_vt = st.multiselect("Farm", sorted(vt_all["farm_code"].unique()),
                                       default=[], key="flt_farm_vt", placeholder="Tất cả")
        with fv2:
            f_loai_vt = st.multiselect("Loại vật tư", sorted(vt_all["loai_vat_tu"].unique()),
                                       default=[], key="flt_loai_vt", placeholder="Tất cả")
        with fv3:
            f_lo_vt = st.multiselect("Lô", sorted(vt_all["lo_code"].unique()),
                                     default=[], key="flt_lo_vt", placeholder="Tất cả")
        f_search_vt = st.text_input("Tìm tên vật tư", key="flt_search_vt",
                                    placeholder="Nhập từ khoá...")

    vt_f = vt_all.copy()
    if f_farm_vt:  vt_f = vt_f[vt_f["farm_code"].isin(f_farm_vt)]
    if f_loai_vt:  vt_f = vt_f[vt_f["loai_vat_tu"].isin(f_loai_vt)]
    if f_lo_vt:    vt_f = vt_f[vt_f["lo_code"].isin(f_lo_vt)]
    if f_search_vt:
        vt_f = vt_f[vt_f["ten_vat_tu"].str.contains(f_search_vt, case=False, na=False)]

    _vt_start, _vt_end = pagination_controls(len(vt_f), "vt_page")
    vt_show = vt_f.iloc[_vt_start:_vt_end]

    _vt_display = vt_show[["farm_code", "lo_code", "ten_vat_tu",
                            "loai_vat_tu", "thanh_tien", "pct"]].rename(columns={
        "farm_code":  "Farm",
        "lo_code":    "Lô",
        "ten_vat_tu": "Tên vật tư",
        "loai_vat_tu":"Loại",
        "thanh_tien": "Chi phí (VND)",
        "pct":        "% tổng Vật tư",
    }).copy()
    _vt_display["Chi phí (VND)"] = _vt_display["Chi phí (VND)"].apply(lambda x: f"{int(x):,}")
    _vt_display["% tổng Vật tư"] = _vt_display["% tổng Vật tư"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(_vt_display, use_container_width=True, hide_index=True, height=600)
else:
    st.info("Không có dữ liệu vật tư.")

st.markdown("---")

# ═════════════════════════════════════════════
# BẢNG CHI TIẾT THEO LÔ
# ═════════════════════════════════════════════
with st.expander("📋 Bảng chi tiết theo Lô"):
    _lc = raw_c.groupby(["farm_code", "lo_code"])["thanh_tien"].sum().reset_index()
    _lc.columns = ["farm_code", "lo_code", "tien_c"]
    if not raw_v.empty:
        _lv = raw_v.groupby(["farm_code", "lo_code"])["thanh_tien"].sum().reset_index()
        _lv.columns = ["farm_code", "lo_code", "tien_v"]
        _bl = _lc.merge(_lv, on=["farm_code", "lo_code"], how="outer").fillna(0)
    else:
        _bl = _lc.copy(); _bl["tien_v"] = 0.0
    _bl["tien_c"] = pd.to_numeric(_bl["tien_c"], errors="coerce").fillna(0)
    _bl["tien_v"] = pd.to_numeric(_bl["tien_v"], errors="coerce").fillna(0)
    _bl["Tổng"]   = _bl["tien_c"] + _bl["tien_v"]
    _bl = _bl.sort_values("Tổng", ascending=False).reset_index(drop=True)
    st.dataframe(pd.DataFrame({
        "Farm":   _bl["farm_code"],
        "Lô":     _bl["lo_code"],
        "Công":   _bl["tien_c"].apply(format_vnd),
        "Vật tư": _bl["tien_v"].apply(format_vnd),
        "Tổng":   _bl["Tổng"].apply(format_vnd),
    }), use_container_width=True, hide_index=True)