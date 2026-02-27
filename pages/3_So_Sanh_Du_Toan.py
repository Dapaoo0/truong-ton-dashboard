import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import query
from style import (inject_css, page_header, kpi_row, section_header,
                   tip, apply_plotly_style, C, BAR_CONG, BAR_VAT_TU)

st.set_page_config(page_title="So Sánh Dự Toán · Farm 195", page_icon="🎯", layout="wide")
inject_css()

TX  = C["text"];  TM = C["text_muted"]; TS = C["text_sub"]
SF  = C["surface"]; BD = C["border"]; SF2 = C["surface2"]; BD2 = C["border2"]
GRN = C["green"]; AMB = C["amber"]; RED = C["red"]; BLU = C["blue"]
PUR = C["purple"]; GP = C["green_pale"]; AP = C["amber_pale"]; RP = C["red_pale"]

# Màu theo loại chi phí
LOAI_COLOR = {
    "Công":    GRN,
    "Vườn Ươm": PUR,
    "Vật Tư":  AMB,
    "ĐTBĐ":   BLU,
}

def fmt_m(val):
    if val is None or (isinstance(val, float) and pd.isna(val)): return "—"
    if abs(val) >= 1e9: return f"{val/1e9:.2f} tỷ"
    if abs(val) >= 1e6: return f"{val/1e6:.1f}M"
    return f"{val:,.0f}"

def fmt_vnd(val):
    if val is None or (isinstance(val, float) and pd.isna(val)): return "—"
    return f"{val:,.0f} VND"

def pct_color(pct):
    """Màu cho % thực hiện: xanh nếu <=100 (tiết kiệm hoặc đúng), đỏ nếu >100 (vượt)."""
    if pct is None or pd.isna(pct): return TM
    if pct > 100: return RED
    if pct >= 80: return GRN
    return AMB

def calc_pct(thuc_te, du_toan):
    if du_toan and du_toan != 0:
        return round(thuc_te / du_toan * 100, 1)
    return None

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_tong():
    return query("""
        SELECT
            tong_id,
            loai_du_lieu,
            loai_chi_phi,
            gia_tri,
            ngay,
            ngay_bat_dau_khau_hao,
            COALESCE(ngay, ngay_bat_dau_khau_hao) AS ngay_eff,
            lo, lo_2, loai_lo, dien_tich_ha,
            COALESCE(hang_muc_du_toan_cong,
                     hang_muc_du_toan_vat_tu,
                     hang_muc_du_toan_dtbd)          AS hang_muc,
            hang_muc_du_toan_cong,
            hang_muc_du_toan_vat_tu,
            hang_muc_du_toan_dtbd,
            ngoai_du_toan,
            doi_thuc_hien,
            hang_muc_cong_viec,
            ma_cv, ma_dtbd,
            ten_vt_dtbd, phan_loai_dtbd,
            vat_tu, so_luong, loai_vat_tu,
            so_cong, dvt, don_gia,
            vu, tien_do_vu
        FROM fact_195_tong
        ORDER BY loai_chi_phi, ngay_eff NULLS LAST
    """)

raw = load_tong()
if raw.empty:
    st.error("Không có dữ liệu trong fact_195_tong. Hãy chạy script push trước.")
    st.stop()

for col in ["gia_tri", "so_cong", "so_luong", "don_gia", "dien_tich_ha", "tien_do_vu"]:
    raw[col] = pd.to_numeric(raw[col], errors="coerce")
raw["ngay_eff"] = pd.to_datetime(raw["ngay_eff"], errors="coerce")
raw["thang"] = raw["ngay_eff"].dt.to_period("M").dt.to_timestamp()
raw["thang_str"] = raw["ngay_eff"].dt.strftime("%m/%Y")
raw["thang_str"] = raw["thang_str"].fillna("Không rõ tháng")

# Tách 2 chiều: thực tế và dự toán
df_tt = raw[raw["loai_du_lieu"] == "Thực tế"].copy()
df_dt = raw[raw["loai_du_lieu"] == "Dự toán"].copy()

# ─────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="font-size:13px;font-weight:600;color:{TX};padding:10px 0 6px">🔍 Bộ lọc</div>',
        unsafe_allow_html=True)

    all_loai = sorted(raw["loai_chi_phi"].dropna().unique().tolist())
    sel_loai = st.multiselect("Loại chi phí", all_loai, default=all_loai, key="loai_cp_dt")
    if not sel_loai:
        st.warning("Chọn ít nhất 1 loại chi phí"); st.stop()

    # Tháng
    all_thang = sorted([t for t in raw["thang_str"].dropna().unique() if t != "Không rõ tháng"])
    sel_thang = st.multiselect("Tháng", all_thang, default=all_thang, key="thang_dt")
    if not sel_thang:
        st.warning("Chọn ít nhất 1 tháng"); st.stop()

    # Ngoài / Trong dự toán
    ngoai_options = ["Trong dự toán", "Ngoài dự toán"]
    sel_ngoai = st.multiselect("Phân loại dự toán", ngoai_options,
                               default=ngoai_options, key="ngoai_dt")
    if not sel_ngoai:
        st.warning("Chọn ít nhất 1 loại"); st.stop()

    # Hạng mục
    all_hm = sorted(raw["hang_muc"].dropna().unique().tolist())
    sel_hm = st.multiselect("Hạng mục", all_hm, default=[], key="hm_dt",
                            help="Để trống = tất cả")

    st.markdown("---")
    st.markdown(
        f'<div style="font-size:11px;color:{TM};line-height:1.8">'
        f'📌 <b style="color:{GRN}">Xanh</b>: ≤ 100% DT (tiết kiệm/đúng)<br>'
        f'📌 <b style="color:{RED}">Đỏ</b>: > 100% DT (vượt ngân sách)<br>'
        f'📌 <b style="color:{AMB}">Vàng</b>: &lt; 80% DT (chưa giải ngân)<br>'
        f'📌 <b style="color:{TM}">Xám</b>: Ngoài dự toán (không có kế hoạch)'
        f'</div>',
        unsafe_allow_html=True)

# Áp dụng filter
def apply_filters(df):
    d = df.copy()
    if sel_loai: d = d[d["loai_chi_phi"].isin(sel_loai)]
    if sel_thang:
        d = d[d["thang_str"].isin(sel_thang) | (d["thang_str"] == "Không rõ tháng")]
    if sel_ngoai: d = d[d["ngoai_du_toan"].isin(sel_ngoai)]
    if sel_hm:    d = d[d["hang_muc"].isin(sel_hm)]
    return d

df_tt = apply_filters(df_tt)
df_dt = apply_filters(df_dt)

if df_tt.empty and df_dt.empty:
    st.warning("Không có dữ liệu với filter này."); st.stop()

# ─────────────────────────────────────────────
# KPI TỔNG QUAN
# ─────────────────────────────────────────────
page_header("🎯", "So Sánh Thành Tiền vs Dự Toán — Farm 195",
            "Nguồn: fact_195_tong · chỉ tính nhóm Trong dự toán cho % thực hiện")

# Tính KPI chỉ trên "Trong dự toán" (có dự toán thực sự)
tt_trong = df_tt[df_tt["ngoai_du_toan"] == "Trong dự toán"]["gia_tri"].sum()
dt_trong = df_dt[df_dt["ngoai_du_toan"] == "Trong dự toán"]["gia_tri"].sum()
pct_tong = calc_pct(tt_trong, dt_trong)
tt_ngoai = df_tt[df_tt["ngoai_du_toan"] == "Ngoài dự toán"]["gia_tri"].sum()
chenh_lech = tt_trong - dt_trong

kpi_row([
    dict(label="Thực tế (Trong DT)", value=fmt_m(tt_trong) + " VND",
         icon="💰", color=GRN, footnote="tổng thành tiền có kế hoạch DT"),
    dict(label="Dự toán kế hoạch",   value=fmt_m(dt_trong) + " VND",
         icon="📋", color=BLU, footnote="ngân sách phân bổ"),
    dict(label="% Thực hiện",
         value=f"{pct_tong:.1f}%" if pct_tong is not None else "—",
         icon="📊",
         color=pct_color(pct_tong) if pct_tong else TM,
         delta=("✅ Trong ngân sách" if pct_tong and pct_tong <= 100
                else "⚠️ Vượt ngân sách" if pct_tong else "—"),
         delta_positive=(pct_tong is not None and pct_tong <= 100)),
    dict(label="Phát sinh Ngoài DT", value=fmt_m(tt_ngoai) + " VND",
         icon="⚠️", color=AMB,
         footnote="chi phí không có trong kế hoạch"),
])

# Chênh lệch banner
chenh_color = RED if chenh_lech > 0 else GRN
chenh_icon  = "🔴 Vượt" if chenh_lech > 0 else "🟢 Tiết kiệm"
st.markdown(
    f'<div style="background:{RP if chenh_lech > 0 else GP};'
    f'border:1px solid {chenh_color}33;border-left:4px solid {chenh_color};'
    f'border-radius:0 8px 8px 0;padding:12px 20px;margin:12px 0;'
    f'display:flex;gap:24px;align-items:center">'
    f'<div style="font-size:20px">{chenh_icon}</div>'
    f'<div><span style="font-size:12px;color:{TM}">Chênh lệch Thực tế − Dự toán (Trong DT):</span>'
    f'<span style="font-size:18px;font-weight:700;color:{chenh_color};'
    f'font-family:DM Mono,monospace;margin-left:12px">'
    f'{("+" if chenh_lech > 0 else "")}{fmt_m(chenh_lech)} VND</span></div>'
    f'</div>',
    unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────
# SECTION 1: GROUPED BAR — Thực tế vs Dự toán theo Hạng mục
# ─────────────────────────────────────────────
section_header("Thực tế vs Dự toán theo Hạng mục",
               "chỉ nhóm Trong dự toán · nhóm theo loại chi phí")

# Pivot: mỗi hàng = (loai_chi_phi, hang_muc) → thuc_te + du_toan
grp_tt = (df_tt[df_tt["ngoai_du_toan"] == "Trong dự toán"]
          .groupby(["loai_chi_phi", "hang_muc"])["gia_tri"].sum().reset_index()
          .rename(columns={"gia_tri": "thuc_te"}))
grp_dt = (df_dt[df_dt["ngoai_du_toan"] == "Trong dự toán"]
          .groupby(["loai_chi_phi", "hang_muc"])["gia_tri"].sum().reset_index()
          .rename(columns={"gia_tri": "du_toan"}))
grp = grp_tt.merge(grp_dt, on=["loai_chi_phi", "hang_muc"], how="outer").fillna(0)
grp["hang_muc"] = grp["hang_muc"].fillna("(không rõ)")
grp["label"] = grp["loai_chi_phi"] + " · " + grp["hang_muc"]
grp["pct"] = grp.apply(lambda r: calc_pct(r["thuc_te"], r["du_toan"]), axis=1)
grp = grp.sort_values(["loai_chi_phi", "thuc_te"], ascending=[True, False])

if not grp.empty:
    fig_hm = go.Figure()
    # Bar dự toán (nền)
    fig_hm.add_bar(
        x=grp["label"], y=grp["du_toan"],
        name="Dự toán",
        marker_color=BD2, opacity=0.5,
        hovertemplate="<b>%{x}</b><br>Dự toán: %{y:,.0f} VND<extra></extra>",
    )
    # Bar thực tế (overlay), màu theo loại chi phí
    bar_colors_tt = [LOAI_COLOR.get(r["loai_chi_phi"], GRN) for _, r in grp.iterrows()]
    fig_hm.add_bar(
        x=grp["label"], y=grp["thuc_te"],
        name="Thực tế",
        marker_color=bar_colors_tt,
        opacity=0.9,
        text=[f"{p:.0f}%" if p is not None else "" for p in grp["pct"]],
        textposition="outside",
        textfont=dict(color=TS, size=10),
        hovertemplate="<b>%{x}</b><br>Thực tế: %{y:,.0f} VND<br>%{text} DT<extra></extra>",
    )
    fig_hm.update_layout(
        barmode="overlay",
        yaxis_tickformat=",.0f",
        xaxis=dict(tickangle=-35, automargin=True),
        title=dict(text="Thực tế (màu) chồng lên Dự toán (xám)",
                   font=dict(size=12, color=TM)),
    )
    apply_plotly_style(fig_hm, 400)
    st.plotly_chart(fig_hm, use_container_width=True, key="bar_hm")

    # Progress cards theo từng hạng mục
    tip("Thẻ bên dưới tóm tắt tỉ lệ thực hiện từng hạng mục · xanh = đúng ngân sách · đỏ = vượt")
    cols_per_row = 4
    cards = grp[grp["du_toan"] > 0].reset_index(drop=True)
    n = len(cards)
    for i in range(0, n, cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (_, r) in enumerate(cards.iloc[i:i+cols_per_row].iterrows()):
            pct = r["pct"]
            c = pct_color(pct)
            bar_w = min(pct, 100) if pct else 0
            extra = max(0, pct - 100) if pct else 0
            with cols[j]:
                st.markdown(
                    f'<div style="background:{SF};border:1px solid {BD};'
                    f'border-top:3px solid {LOAI_COLOR.get(r["loai_chi_phi"],GRN)};'
                    f'border-radius:8px;padding:14px 16px;margin-bottom:8px">'
                    f'<div style="font-size:10px;color:{TM};font-weight:600;'
                    f'text-transform:uppercase;letter-spacing:0.08em">{r["loai_chi_phi"]}</div>'
                    f'<div style="font-size:13px;font-weight:600;color:{TX};'
                    f'margin:4px 0">{r["hang_muc"]}</div>'
                    f'<div style="background:{SF2};border-radius:99px;height:6px;margin:8px 0;overflow:hidden">'
                    f'<div style="background:{c};width:{bar_w:.1f}%;height:100%"></div>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:11px">'
                    f'<span style="color:{TM}">TT: {fmt_m(r["thuc_te"])}</span>'
                    f'<span style="color:{c};font-weight:700">{pct:.1f}%</span>'
                    f'</div>'
                    f'<div style="font-size:11px;color:{TM};margin-top:2px">'
                    f'DT: {fmt_m(r["du_toan"])}</div>'
                    + (f'<div style="font-size:10px;color:{RED};margin-top:4px">▲ Vượt {extra:.1f}%</div>'
                       if extra > 0 else "")
                    + f'</div>',
                    unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────
# SECTION 2: XU HƯỚNG THÁNG — Thực tế vs Dự toán cumulative
# ─────────────────────────────────────────────
section_header("Xu hướng tích lũy theo tháng",
               "so sánh tiến độ giải ngân thực tế với kế hoạch dự toán")

col1, col2 = st.columns(2)

with col1:
    # Grouped bar theo tháng: thực tế vs dự toán
    m_tt = (df_tt[df_tt["ngoai_du_toan"] == "Trong dự toán"]
            .groupby("thang_str")["gia_tri"].sum().reset_index()
            .rename(columns={"gia_tri": "thuc_te"}))
    m_dt = (df_dt[df_dt["ngoai_du_toan"] == "Trong dự toán"]
            .groupby("thang_str")["gia_tri"].sum().reset_index()
            .rename(columns={"gia_tri": "du_toan"}))
    m = m_tt.merge(m_dt, on="thang_str", how="outer").fillna(0)
    # Sắp xếp tháng đúng thứ tự
    def thang_sort_key(s):
        try:
            parts = s.split("/")
            return (int(parts[1]), int(parts[0]))
        except: return (9999, 99)
    m = m.sort_values("thang_str", key=lambda x: x.map(thang_sort_key)).reset_index(drop=True)

    fig_thang = go.Figure()
    fig_thang.add_bar(
        x=m["thang_str"], y=m["du_toan"], name="Dự toán",
        marker_color=BD2, opacity=0.6,
        hovertemplate="<b>%{x}</b><br>Dự toán: %{y:,.0f} VND<extra></extra>",
    )
    fig_thang.add_bar(
        x=m["thang_str"], y=m["thuc_te"], name="Thực tế",
        marker_color=GRN, opacity=0.9,
        hovertemplate="<b>%{x}</b><br>Thực tế: %{y:,.0f} VND<extra></extra>",
    )
    fig_thang.update_layout(
        barmode="group",
        yaxis_tickformat=",.0f",
        title=dict(text="Thực tế vs Dự toán theo tháng (Trong DT)",
                   font=dict(size=12, color=TM)),
    )
    apply_plotly_style(fig_thang, 340)
    st.plotly_chart(fig_thang, use_container_width=True, key="thang_bar")

with col2:
    # % thực hiện theo tháng — line chart
    m["pct"] = m.apply(lambda r: calc_pct(r["thuc_te"], r["du_toan"]), axis=1)
    m_valid = m[m["pct"].notna()]

    fig_pct = go.Figure()
    if not m_valid.empty:
        pct_colors = [pct_color(p) for p in m_valid["pct"]]
        fig_pct.add_scatter(
            x=m_valid["thang_str"], y=m_valid["pct"],
            mode="lines+markers+text",
            line=dict(color=GRN, width=2.5),
            marker=dict(size=10, color=pct_colors,
                        line=dict(width=2, color=TX)),
            text=[f"{p:.0f}%" for p in m_valid["pct"]],
            textposition="top center",
            textfont=dict(color=TS, size=11),
            hovertemplate="<b>%{x}</b><br>% thực hiện: %{y:.1f}%<extra></extra>",
        )
    fig_pct.add_hline(y=100, line_dash="dash", line_color=BD2,
                      annotation_text="100%", annotation_font_size=10,
                      annotation_font_color=TM)
    fig_pct.add_hrect(y0=100, y1=200, fillcolor=RED, opacity=0.04, line_width=0)
    fig_pct.update_layout(
        yaxis_ticksuffix="%",
        yaxis_range=[0, max((m_valid["pct"].max() * 1.3 if not m_valid.empty else 150), 120)],
        title=dict(text="% Thực hiện theo tháng",
                   font=dict(size=12, color=TM)),
    )
    apply_plotly_style(fig_pct, 340)
    st.plotly_chart(fig_pct, use_container_width=True, key="pct_thang")

st.markdown("---")

# ─────────────────────────────────────────────
# SECTION 3: BREAKDOWN THEO LOẠI CHI PHÍ (với tháng)
# ─────────────────────────────────────────────
section_header("Chi tiết theo Loại chi phí & Tháng",
               "nhóm Trong dự toán · mỗi tab = 1 loại chi phí")

loai_in_dt = sorted(
    df_tt[df_tt["ngoai_du_toan"] == "Trong dự toán"]["loai_chi_phi"].dropna().unique().tolist()
)

if loai_in_dt:
    tabs = st.tabs([f"{LOAI_COLOR.get(l,'') and ''}{l}" for l in loai_in_dt])

    for tab, loai in zip(tabs, loai_in_dt):
        with tab:
            d_tt_l = df_tt[(df_tt["loai_chi_phi"] == loai) &
                           (df_tt["ngoai_du_toan"] == "Trong dự toán")]
            d_dt_l = df_dt[(df_dt["loai_chi_phi"] == loai) &
                           (df_dt["ngoai_du_toan"] == "Trong dự toán")]

            tt_l = d_tt_l["gia_tri"].sum()
            dt_l = d_dt_l["gia_tri"].sum()
            pct_l = calc_pct(tt_l, dt_l)
            color_l = LOAI_COLOR.get(loai, GRN)

            # Mini KPI
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(
                    f'<div style="background:{SF};border:1px solid {BD};'
                    f'border-top:2px solid {color_l};border-radius:8px;padding:12px 16px">'
                    f'<div style="font-size:10px;color:{TM};font-weight:600;text-transform:uppercase">Thực tế</div>'
                    f'<div style="font-size:18px;font-weight:700;color:{TX};'
                    f"font-family:DM Mono,monospace;margin-top:4px\">{fmt_m(tt_l)} VND</div></div>",
                    unsafe_allow_html=True)
            with k2:
                st.markdown(
                    f'<div style="background:{SF};border:1px solid {BD};'
                    f'border-top:2px solid {BLU};border-radius:8px;padding:12px 16px">'
                    f'<div style="font-size:10px;color:{TM};font-weight:600;text-transform:uppercase">Dự toán</div>'
                    f'<div style="font-size:18px;font-weight:700;color:{TX};'
                    f"font-family:DM Mono,monospace;margin-top:4px\">{fmt_m(dt_l)} VND</div></div>",
                    unsafe_allow_html=True)
            with k3:
                c_pct = pct_color(pct_l)
                st.markdown(
                    f'<div style="background:{SF};border:1px solid {BD};'
                    f'border-top:2px solid {c_pct};border-radius:8px;padding:12px 16px">'
                    f'<div style="font-size:10px;color:{TM};font-weight:600;text-transform:uppercase">% Thực hiện</div>'
                    f'<div style="font-size:18px;font-weight:700;color:{c_pct};'
                    f"font-family:DM Mono,monospace;margin-top:4px\">"
                    f"{f'{pct_l:.1f}%' if pct_l is not None else '—'}</div></div>",
                    unsafe_allow_html=True)
            with k4:
                ch = tt_l - dt_l
                c_ch = RED if ch > 0 else GRN
                st.markdown(
                    f'<div style="background:{SF};border:1px solid {BD};'
                    f'border-top:2px solid {c_ch};border-radius:8px;padding:12px 16px">'
                    f'<div style="font-size:10px;color:{TM};font-weight:600;text-transform:uppercase">Chênh lệch</div>'
                    f'<div style="font-size:18px;font-weight:700;color:{c_ch};'
                    f"font-family:DM Mono,monospace;margin-top:4px\">"
                    f'{"+" if ch > 0 else ""}{fmt_m(ch)} VND</div></div>',
                    unsafe_allow_html=True)

            st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

            # Chart: grouped bar theo hang_muc trong loại này
            col_a, col_b = st.columns([3, 2])
            with col_a:
                hm_tt = (d_tt_l.groupby("hang_muc")["gia_tri"].sum().reset_index()
                         .rename(columns={"gia_tri": "thuc_te"}))
                hm_dt = (d_dt_l.groupby("hang_muc")["gia_tri"].sum().reset_index()
                         .rename(columns={"gia_tri": "du_toan"}))
                hm = hm_tt.merge(hm_dt, on="hang_muc", how="outer").fillna(0)
                hm["hang_muc"] = hm["hang_muc"].fillna("(không rõ)")
                hm = hm.sort_values("thuc_te", ascending=True)
                hm["pct_hm"] = hm.apply(lambda r: calc_pct(r["thuc_te"], r["du_toan"]), axis=1)
                hm["bar_color"] = hm["pct_hm"].apply(
                    lambda p: (RED if p and p > 100 else (color_l if p and p >= 80 else AMB)) if p else BD2)

                fig_l = go.Figure()
                fig_l.add_bar(
                    y=hm["hang_muc"], x=hm["du_toan"],
                    name="Dự toán", orientation="h",
                    marker_color=BD2, opacity=0.5,
                    hovertemplate="<b>%{y}</b><br>Dự toán: %{x:,.0f} VND<extra></extra>",
                )
                fig_l.add_bar(
                    y=hm["hang_muc"], x=hm["thuc_te"],
                    name="Thực tế", orientation="h",
                    marker_color=hm["bar_color"].tolist(),
                    opacity=0.9,
                    text=[f"{p:.0f}%" if p is not None else "" for p in hm["pct_hm"]],
                    textposition="outside",
                    textfont=dict(color=TS, size=10),
                    hovertemplate="<b>%{y}</b><br>Thực tế: %{x:,.0f} VND · %{text}<extra></extra>",
                )
                fig_l.update_layout(
                    barmode="overlay", xaxis_tickformat=",.0f",
                    yaxis=dict(automargin=True),
                    margin=dict(t=36, b=48, l=160, r=40),
                    title=dict(text=f"{loai} — Thực tế vs Dự toán theo Hạng mục",
                               font=dict(size=11, color=TM)),
                )
                apply_plotly_style(fig_l, max(280, len(hm) * 40))
                st.plotly_chart(fig_l, use_container_width=True, key=f"hm_{loai}")

            with col_b:
                # Bảng tóm tắt hạng mục
                tbl = hm[["hang_muc", "thuc_te", "du_toan", "pct_hm"]].copy()
                tbl["thuc_te"] = tbl["thuc_te"].apply(fmt_m)
                tbl["du_toan"] = tbl["du_toan"].apply(fmt_m)
                tbl["pct_hm"]  = tbl["pct_hm"].apply(
                    lambda p: f"{p:.1f}%" if p is not None else "Ngoài DT")
                tbl = tbl.rename(columns={
                    "hang_muc": "Hạng mục",
                    "thuc_te":  "Thực tế",
                    "du_toan":  "Dự toán",
                    "pct_hm":   "% TH",
                })
                st.dataframe(tbl.reset_index(drop=True), use_container_width=True,
                             hide_index=True, height=min(280, len(tbl) * 40 + 40))

else:
    st.info("Không có dữ liệu Trong dự toán với filter hiện tại.")

st.markdown("---")

# ─────────────────────────────────────────────
# SECTION 4: NGOÀI DỰ TOÁN
# ─────────────────────────────────────────────
section_header("Chi phí Ngoài dự toán",
               "các khoản thực tế không có trong kế hoạch · dự toán luôn = 0")

df_ngoai = df_tt[df_tt["ngoai_du_toan"] == "Ngoài dự toán"].copy()

if not df_ngoai.empty:
    col1, col2 = st.columns([2, 1])

    with col1:
        # Bar chart theo loại chi phí x hang_muc
        ngoai_grp = (df_ngoai.groupby(["loai_chi_phi", "hang_muc", "thang_str"])
                     ["gia_tri"].sum().reset_index())
        ngoai_grp["hang_muc"] = ngoai_grp["hang_muc"].fillna("(không có hạng mục)")
        ngoai_grp["label"] = ngoai_grp["loai_chi_phi"] + " · " + ngoai_grp["hang_muc"]
        ngoai_sum = (ngoai_grp.groupby(["loai_chi_phi", "hang_muc", "label"])
                     ["gia_tri"].sum().reset_index()
                     .sort_values("gia_tri", ascending=True))

        fig_ngoai = go.Figure()
        for loai in reversed(sorted(ngoai_sum["loai_chi_phi"].unique())):
            sub = ngoai_sum[ngoai_sum["loai_chi_phi"] == loai]
            fig_ngoai.add_bar(
                y=sub["label"], x=sub["gia_tri"],
                name=loai, orientation="h",
                marker_color=LOAI_COLOR.get(loai, BD2),
                opacity=0.85,
                hovertemplate=f"<b>{loai}</b><br>%{{y}}<br>%{{x:,.0f}} VND<extra></extra>",
            )
        fig_ngoai.update_layout(
            barmode="stack", xaxis_tickformat=",.0f",
            yaxis=dict(automargin=True),
            margin=dict(t=36, b=48, l=220, r=8),
            title=dict(text="Tổng chi phí Ngoài dự toán theo Hạng mục",
                       font=dict(size=12, color=TM)),
        )
        apply_plotly_style(fig_ngoai, max(320, len(ngoai_sum) * 36))
        st.plotly_chart(fig_ngoai, use_container_width=True, key="bar_ngoai")

    with col2:
        # Pie chart phân bổ ngoài dự toán theo loại chi phí
        pie_ngoai = (df_ngoai.groupby("loai_chi_phi")["gia_tri"].sum().reset_index()
                     .sort_values("gia_tri", ascending=False))
        fig_pie_n = go.Figure(go.Pie(
            labels=pie_ngoai["loai_chi_phi"],
            values=pie_ngoai["gia_tri"],
            marker_colors=[LOAI_COLOR.get(l, BD2) for l in pie_ngoai["loai_chi_phi"]],
            hole=0.55, textinfo="percent+label",
            textfont_size=11,
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} VND<br>%{percent}<extra></extra>",
        ))
        fig_pie_n.update_layout(
            title=dict(text="Cơ cấu Ngoài DT", font=dict(size=12, color=TM)),
            showlegend=False,
        )
        apply_plotly_style(fig_pie_n, 320)
        st.plotly_chart(fig_pie_n, use_container_width=True, key="pie_ngoai")

    # Bảng chi tiết ngoài dự toán
    with st.expander("📋 Chi tiết từng dòng Ngoài dự toán"):
        show_ngoai = df_ngoai[[
            "loai_chi_phi", "thang_str", "lo", "hang_muc",
            "hang_muc_cong_viec", "vat_tu", "ma_dtbd",
            "doi_thuc_hien", "gia_tri"
        ]].copy()
        show_ngoai["gia_tri"] = show_ngoai["gia_tri"].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        show_ngoai = show_ngoai.rename(columns={
            "loai_chi_phi":     "Loại",
            "thang_str":        "Tháng",
            "lo":               "Lô",
            "hang_muc":         "Hạng mục DT",
            "hang_muc_cong_viec": "Hạng mục CV",
            "vat_tu":           "Vật tư",
            "ma_dtbd":          "Mã ĐTBĐ",
            "doi_thuc_hien":    "Đội",
            "gia_tri":          "Thành tiền (VND)",
        })
        st.dataframe(show_ngoai.reset_index(drop=True),
                     use_container_width=True, hide_index=True, height=400)
else:
    st.info("Không có chi phí Ngoài dự toán với filter hiện tại.")

st.markdown("---")

# ─────────────────────────────────────────────
# SECTION 5: BẢNG TỔNG HỢP ĐẦY ĐỦ
# ─────────────────────────────────────────────
section_header("Bảng tổng hợp đầy đủ",
               "pivot thực tế vs dự toán · mọi hạng mục · mọi tháng")

full_tt = (df_tt.groupby(["loai_chi_phi", "hang_muc", "ngoai_du_toan", "thang_str"])
           ["gia_tri"].sum().reset_index().rename(columns={"gia_tri": "thuc_te"}))
full_dt = (df_dt.groupby(["loai_chi_phi", "hang_muc", "ngoai_du_toan", "thang_str"])
           ["gia_tri"].sum().reset_index().rename(columns={"gia_tri": "du_toan"}))
full = full_tt.merge(full_dt, on=["loai_chi_phi", "hang_muc", "ngoai_du_toan", "thang_str"],
                     how="outer").fillna(0)
full["hang_muc"] = full["hang_muc"].fillna("(không rõ)")
full["chenh_lech"] = full["thuc_te"] - full["du_toan"]
full["pct"] = full.apply(lambda r: calc_pct(r["thuc_te"], r["du_toan"]), axis=1)

# Sort: loai_chi_phi → thang → hang_muc
def sort_thang_key(s):
    try:
        m, y = s.split("/")
        return (int(y), int(m))
    except: return (9999, 99)

full["_sort"] = full["thang_str"].map(sort_thang_key)
full = full.sort_values(["loai_chi_phi", "_sort", "ngoai_du_toan", "hang_muc"])
full = full.drop(columns=["_sort"])

# Format cho display
def style_pct(p):
    if p is None or pd.isna(p): return "—"
    return f"{p:.1f}%"

display = full.rename(columns={
    "loai_chi_phi": "Loại", "hang_muc": "Hạng mục",
    "ngoai_du_toan": "DT", "thang_str": "Tháng",
    "thuc_te": "Thực tế", "du_toan": "Dự toán",
    "chenh_lech": "Chênh lệch", "pct": "% TH",
}).copy()
display["Thực tế"]   = display["Thực tế"].apply(lambda x: f"{int(x):,}")
display["Dự toán"]   = display["Dự toán"].apply(lambda x: f"{int(x):,}")
display["Chênh lệch"] = display["Chênh lệch"].apply(
    lambda x: f"+{int(x):,}" if x > 0 else f"{int(x):,}")
display["% TH"] = full["pct"].apply(style_pct)

st.dataframe(display.reset_index(drop=True),
             use_container_width=True, hide_index=True, height=500)

# Download
csv = full.to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    "⬇️ Tải bảng CSV",
    data=csv,
    file_name="farm195_du_toan_vs_thuc_te.csv",
    mime="text/csv",
    key="dl_csv"
)