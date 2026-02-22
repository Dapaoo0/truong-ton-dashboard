import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import query, load_farms, load_filter_options, load_date_range, format_pct
from style import (inject_css, page_header, kpi_row, section_header, progress_bar,
                   tip, drill_badge, apply_plotly_style, C, CLR_DAT, CLR_KHONG, CLR_WARN)

st.set_page_config(page_title="Định Mức", page_icon="📊", layout="wide")
inject_css()

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for k in ["dm_farm","dm_doi","dm_lo"]:
    if k not in st.session_state: st.session_state[k] = None

def clear_all():
    st.session_state.dm_farm = st.session_state.dm_doi = st.session_state.dm_lo = None

def multiselect_all(label, options, key):
    c1, c2 = st.columns([4,1])
    with c2: all_on = st.checkbox("Tất cả", value=True, key=f"all_{key}")
    with c1: return st.multiselect(label, options, default=list(options) if all_on else [], key=key)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div style="font-size:13px;font-weight:600;color:{C["text"]};padding:10px 0 6px">🔍 Bộ lọc</div>',
                unsafe_allow_html=True)
    farms_df = load_farms()
    sel_farms = multiselect_all("Farm", farms_df["farm_code"].tolist(), "farm_dm")
    if not sel_farms: st.warning("Chọn ít nhất 1 farm"); st.stop()
    farm_ids = tuple(farms_df[farms_df["farm_code"].isin(sel_farms)]["farm_id"].tolist())

    min_d, max_d = load_date_range(farm_ids, has_dinh_muc=True)
    dr = st.date_input("Thời gian", (min_d, max_d), min_value=min_d, max_value=max_d, key="date_dm")
    if len(dr) != 2: st.stop()
    start_d, end_d = dr

    # Granularity để xem biến động
    granularity = st.selectbox("Xem biến động theo", ["Ngày","Tuần","Tháng","Quý","Năm"], index=2, key="gran_dm")
    gran_map = {"Ngày":"D","Tuần":"W","Tháng":"M","Quý":"Q","Năm":"Y"}
    gran_freq = gran_map[granularity]

    lo_df, doi_df = load_filter_options(farm_ids)
    lo_thuc = lo_df[lo_df["lo_type"]=="Lô thực"]
    sel_los = st.multiselect("Lô thực", sorted(lo_thuc["lo_code"].unique()),
                             default=[], key="lo_dm", help="Để trống = tất cả")
    doi_df["label"] = doi_df["doi_code"] + doi_df["farms"].apply(lambda f: f" ({f})" if "," in f else "")
    doi_labels = dict(zip(doi_df["doi_code"], doi_df["label"]))
    sel_dois = st.multiselect("Đội", doi_df["doi_code"].tolist(),
                              format_func=lambda x: doi_labels.get(x,x),
                              default=[], key="doi_dm", help="Để trống = tất cả")
    include_ht = st.checkbox("Bao gồm công hỗ trợ", value=False, key="ht_dm")

    st.markdown("---")
    drills = [(k,v) for k,v in [("Farm",st.session_state.dm_farm),
                                  ("Đội",st.session_state.dm_doi),
                                  ("Lô",st.session_state.dm_lo)] if v]
    if drills:
        st.markdown(f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;color:{C["text_muted"]}">Drill đang bật</div>',
                    unsafe_allow_html=True)
        for lbl,val in drills:
            drill_badge(lbl, val, f"{lbl}_{val}", clear_all)

# ─────────────────────────────────────────────
# LOAD DATA — không dùng threshold, lấy ti_le thực tế
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_dm(farm_ids, s, e, sel_dois, sel_los, include_ht):
    conds = [f"nk.farm_id IN ({','.join(['%s']*len(farm_ids))})"]
    params = list(farm_ids)
    conds.append("nk.ngay BETWEEN %s AND %s"); params += [str(s), str(e)]
    conds += ["nk.dinh_muc > 0", "nk.klcv IS NOT NULL", "nk.so_cong > 0", "l.lo_type = 'Lô thực'"]
    if sel_dois: conds.append(f"d.doi_code IN ({','.join(['%s']*len(sel_dois))})"); params += list(sel_dois)
    if sel_los:  conds.append(f"l.lo_code IN ({','.join(['%s']*len(sel_los))})"); params += list(sel_los)
    if not include_ht: conds.append("nk.is_ho_tro = FALSE")
    return query(f"""
        SELECT f.farm_code, l.lo_code, d.doi_code,
               cv.ma_cv, cv.ten_cong_viec,
               nk.ngay,
               nk.so_cong, nk.klcv, nk.dinh_muc,
               CASE WHEN nk.so_cong > 0 THEN nk.klcv / nk.so_cong ELSE NULL END as ns_thuc,
               CASE WHEN nk.dinh_muc > 0 AND nk.so_cong > 0
                    THEN ROUND((nk.klcv / nk.so_cong / nk.dinh_muc * 100)::numeric, 1)
                    ELSE NULL END as ti_le
        FROM fact_nhat_ky_san_xuat nk
        JOIN dim_farm f ON f.farm_id = nk.farm_id
        JOIN dim_lo l ON l.lo_id = nk.lo_id
        JOIN dim_doi d ON d.doi_id = nk.doi_id
        JOIN dim_cong_viec cv ON cv.cong_viec_id = nk.cong_viec_id
        WHERE {' AND '.join(conds)}
        ORDER BY nk.ngay
    """, params)

raw = load_dm(farm_ids, start_d, end_d, tuple(sel_dois), tuple(sel_los), include_ht)
if raw.empty: st.error("Không có dữ liệu định mức trong khoảng thời gian này."); st.stop()

for col in ["so_cong","klcv","dinh_muc","ns_thuc","ti_le"]:
    raw[col] = pd.to_numeric(raw[col], errors="coerce")
raw["ngay"] = pd.to_datetime(raw["ngay"])

def apply_drill(df):
    d = df.copy()
    if st.session_state.dm_farm: d = d[d["farm_code"]==st.session_state.dm_farm]
    if st.session_state.dm_doi:  d = d[d["doi_code"] ==st.session_state.dm_doi]
    if st.session_state.dm_lo:   d = d[d["lo_code"]  ==st.session_state.dm_lo]
    return d

df = apply_drill(raw)
if df.empty:
    st.warning("Không có data với filter này."); st.button("✕ Bỏ filter", on_click=clear_all); st.stop()

avg_tl  = df["ti_le"].mean()
med_tl  = df["ti_le"].median()
n_total = len(df)

# ─────────────────────────────────────────────
# HEADER + KPI
# ─────────────────────────────────────────────
page_header("📊", "Định Mức — Tỉ lệ hoàn thành công việc",
            f"{start_d.strftime('%d/%m/%Y')} → {end_d.strftime('%d/%m/%Y')}")

kpi_row([
    dict(label="Số lượt ghi nhận", value=f"{n_total:,}", icon="📝", color=C["blue"]),
    dict(label="Tỉ lệ HT trung bình", value=f"{avg_tl:.1f}%", icon="📈",
         color=C["green"] if avg_tl >= 80 else (C["amber"] if avg_tl >= 60 else C["red"])),
    dict(label="Tỉ lệ HT trung vị",   value=f"{med_tl:.1f}%", icon="📊", color=C["purple"],
         footnote="Ít bị ảnh hưởng bởi outlier"),
    dict(label="Trên 100% (vượt DM)",  value=f"{(df['ti_le']>=100).sum():,}", icon="🏆", color=C["green"],
         delta=f"{(df['ti_le']>=100).mean()*100:.1f}% tổng", delta_positive=True),
])

# ─────────────────────────────────────────────
# BIẾN ĐỘNG THEO THỜI GIAN
# ─────────────────────────────────────────────
section_header(f"Biến động tỉ lệ hoàn thành theo {granularity.lower()}",
               "median ít outlier hơn mean khi có dữ liệu bất thường")

df_t = df.set_index("ngay").resample(gran_freq)["ti_le"].agg(
    trung_binh="mean", trung_vi="median", so_luot="count"
).reset_index()
df_t["trung_binh"] = df_t["trung_binh"].round(1)
df_t["trung_vi"]   = df_t["trung_vi"].round(1)

# Format nhãn trục x theo granularity
if gran_freq in ["D","W"]:
    df_t["nhãn"] = df_t["ngay"].dt.strftime("%d/%m")
elif gran_freq == "M":
    df_t["nhãn"] = df_t["ngay"].dt.strftime("%m/%Y")
elif gran_freq == "Q":
    df_t["nhãn"] = "Q" + df_t["ngay"].dt.quarter.astype(str) + "/" + df_t["ngay"].dt.year.astype(str)
else:
    df_t["nhãn"] = df_t["ngay"].dt.year.astype(str)

fig_time = go.Figure()
fig_time.add_scatter(
    x=df_t["nhãn"], y=df_t["trung_binh"], name="Trung bình",
    mode="lines+markers",
    line=dict(color=C["green"], width=2.5),
    marker=dict(size=7, color=C["green"]),
    fill="tozeroy", fillcolor="rgba(63,185,80,0.08)",
    hovertemplate="<b>%{x}</b><br>Trung bình: %{y:.1f}%<extra></extra>",
)
fig_time.add_scatter(
    x=df_t["nhãn"], y=df_t["trung_vi"], name="Trung vị",
    mode="lines+markers",
    line=dict(color=C["amber"], width=1.5, dash="dot"),
    marker=dict(size=5, color=C["amber"]),
    hovertemplate="<b>%{x}</b><br>Trung vị: %{y:.1f}%<extra></extra>",
)
fig_time.add_hline(y=100, line_dash="dash", line_color=C["border2"],
                   annotation_text="100% (đạt định mức)", annotation_font_size=10,
                   annotation_font_color=C["text_muted"])
fig_time.add_hline(y=80, line_dash="dot", line_color=C["blue"],
                   annotation_text="80%", annotation_font_size=10,
                   annotation_font_color=C["blue"])
fig_time.update_layout(yaxis_ticksuffix="%", yaxis_range=[0, max(df_t["trung_binh"].max()*1.2, 120)])
apply_plotly_style(fig_time, 320)
st.plotly_chart(fig_time, use_container_width=True, key="time_chart")

# ─────────────────────────────────────────────
# THEO FARM — bar trung bình tỉ lệ HT, click drill
# ─────────────────────────────────────────────
section_header("Trung bình tỉ lệ hoàn thành theo Farm", "click để drill")

bf = raw.groupby("farm_code")["ti_le"].agg(trung_binh="mean", so_luot="count").reset_index()
bf["trung_binh"] = bf["trung_binh"].round(1)
active_f = st.session_state.dm_farm

fig_f = go.Figure(go.Bar(
    x=bf["farm_code"], y=bf["trung_binh"],
    marker_color=[C["amber"] if r==active_f
                  else (CLR_DAT if bf.loc[i,"trung_binh"]>=80 else CLR_KHONG)
                  for i,r in enumerate(bf["farm_code"])],
    marker_line_color=[C["text"] if r==active_f else "rgba(0,0,0,0)" for r in bf["farm_code"]],
    marker_line_width=[2 if r==active_f else 0 for r in bf["farm_code"]],
    text=[f"{v:.1f}%<br>({n:,} lượt)" for v,n in zip(bf["trung_binh"], bf["so_luot"])],
    textposition="outside", textfont=dict(color=C["text_sub"], size=11),
    hovertemplate="<b>%{x}</b><br>Trung bình: %{y:.1f}%<extra></extra>",
))
fig_f.add_hline(y=100, line_dash="dash", line_color=C["border2"])
fig_f.add_hline(y=80, line_dash="dot", line_color=C["blue"])
fig_f.update_layout(yaxis_ticksuffix="%", yaxis_range=[0, max(bf["trung_binh"].max()*1.3, 120)])
apply_plotly_style(fig_f, 260)
ev_f = st.plotly_chart(fig_f, use_container_width=True, key="chart_f",
                       on_select="rerun", selection_mode="points")
if ev_f and ev_f.selection and ev_f.selection.get("points"):
    c = ev_f.selection.get("points")[0].get("x")
    if c and c != st.session_state.dm_farm:
        st.session_state.dm_farm = c
        st.session_state.dm_doi  = None
        st.session_state.dm_lo   = None

# ─────────────────────────────────────────────
# THEO ĐỘI (gộp xuyên farm) + THEO LÔ — bên nhau
# ─────────────────────────────────────────────
section_header("Theo Đội & Theo Lô", "click để drill · gộp xuyên farm")
col1, col2 = st.columns(2)

with col1:
    bd = df.groupby("doi_code")["ti_le"].agg(trung_binh="mean", so_luot="count").reset_index()
    bd["trung_binh"] = bd["trung_binh"].round(1)
    bd = bd[bd["so_luot"]>=3].sort_values("trung_binh", ascending=True).reset_index(drop=True)
    active_d = st.session_state.dm_doi

    fig_d = go.Figure(go.Bar(
        y=bd["doi_code"], x=bd["trung_binh"], orientation="h",
        marker_color=[C["amber"] if d==active_d
                      else (CLR_DAT if bd.loc[i,"trung_binh"]>=80 else CLR_KHONG)
                      for i,d in enumerate(bd["doi_code"])],
        marker_line_color=[C["text"] if d==active_d else "rgba(0,0,0,0)" for d in bd["doi_code"]],
        marker_line_width=[2 if d==active_d else 0 for d in bd["doi_code"]],
        text=[f"{v:.1f}%" for v in bd["trung_binh"]],
        textposition="outside", textfont=dict(color=C["text_sub"], size=10),
        hovertemplate="<b>%{y}</b><br>Trung bình: %{x:.1f}%<br>(%{customdata:,} lượt)<extra></extra>",
        customdata=bd["so_luot"],
    ))
    fig_d.add_vline(x=100, line_dash="dash", line_color=C["border2"])
    fig_d.add_vline(x=80, line_dash="dot", line_color=C["blue"])
    fig_d.update_layout(xaxis_ticksuffix="%", xaxis_range=[0, max(bd["trung_binh"].max()*1.25, 125)],
                        title=dict(text="Theo Đội", font=dict(size=12, color=C["text_muted"])))
    apply_plotly_style(fig_d, 400)
    ev_d = st.plotly_chart(fig_d, use_container_width=True, key="chart_d",
                           on_select="rerun", selection_mode="points")
    if ev_d and ev_d.selection and ev_d.selection.get("points"):
        c = ev_d.selection.get("points")[0].get("y")
        if c and c != st.session_state.dm_doi:
            st.session_state.dm_doi  = c
            st.session_state.dm_farm = None
            st.session_state.dm_lo   = None

with col2:
    bl = df.groupby(["farm_code","lo_code"])["ti_le"].agg(trung_binh="mean", so_luot="count").reset_index()
    bl["trung_binh"] = bl["trung_binh"].round(1)
    bl["label"] = bl["farm_code"].str.replace("Farm ","F") + " · " + bl["lo_code"]
    bl = bl[bl["so_luot"]>=3].sort_values("trung_binh", ascending=True).reset_index(drop=True)
    active_lo = st.session_state.dm_lo

    fig_l = go.Figure(go.Bar(
        y=bl["label"], x=bl["trung_binh"], orientation="h",
        marker_color=[C["amber"] if bl.loc[i,"lo_code"]==active_lo
                      else (CLR_DAT if bl.loc[i,"trung_binh"]>=80 else
                            (CLR_WARN if bl.loc[i,"trung_binh"]>=60 else CLR_KHONG))
                      for i in range(len(bl))],
        text=[f"{v:.1f}%" for v in bl["trung_binh"]],
        textposition="outside", textfont=dict(color=C["text_sub"], size=9),
        hovertemplate="<b>%{y}</b><br>Trung bình: %{x:.1f}%<br>(%{customdata:,} lượt)<extra></extra>",
        customdata=bl["so_luot"],
    ))
    fig_l.add_vline(x=100, line_dash="dash", line_color=C["border2"])
    fig_l.add_vline(x=80, line_dash="dot", line_color=C["blue"])
    fig_l.update_layout(xaxis_ticksuffix="%", xaxis_range=[0, max(bl["trung_binh"].max()*1.25, 125)],
                        title=dict(text="Theo Lô (click để drill)",
                                   font=dict(size=12, color=C["text_muted"])))
    apply_plotly_style(fig_l, max(400, len(bl)*20))
    ev_l = st.plotly_chart(fig_l, use_container_width=True, key="chart_l",
                           on_select="rerun", selection_mode="points")
    if ev_l and ev_l.selection and ev_l.selection.get("points"):
        lbl = ev_l.selection.get("points")[0].get("y","")
        if " · " in lbl:
            lo_code = lbl.split(" · ",1)[1]
            if lo_code != st.session_state.dm_lo:
                st.session_state.dm_lo   = lo_code
                st.session_state.dm_farm = None
                st.session_state.dm_doi  = None

# ─────────────────────────────────────────────
# THEO CÔNG VIỆC — heatmap tỉ lệ HT theo công việc x tháng
# ─────────────────────────────────────────────
section_header("Tỉ lệ hoàn thành theo Công việc & Thời gian",
               "màu xanh = đạt cao, đỏ = thấp · hover để xem chi tiết")

df["thang_str"] = df["ngay"].dt.to_period("M").astype(str)
cv_list = df.groupby("ten_cong_viec")["ti_le"].mean().sort_values(ascending=False).head(20).index.tolist()
df_cv = df[df["ten_cong_viec"].isin(cv_list)]
pivot = df_cv.groupby(["ten_cong_viec","thang_str"])["ti_le"].mean().reset_index()
pivot["ti_le"] = pivot["ti_le"].round(1)
pv = pivot.pivot(index="ten_cong_viec", columns="thang_str", values="ti_le")
pv = pv.reindex(cv_list)

fig_hm = go.Figure(go.Heatmap(
    z=pv.values,
    x=pv.columns.tolist(),
    y=pv.index.tolist(),
    colorscale=[[0,"#F85149"],[0.5,"#F0A800"],[1,"#3FB950"]],
    zmin=0, zmax=150,
    hovertemplate="<b>%{y}</b><br>%{x}<br>Tỉ lệ HT: %{z:.1f}%<extra></extra>",
    colorbar=dict(title="%", ticksuffix="%", len=0.8,
                  tickfont=dict(color=C["text_muted"]),
                  titlefont=dict(color=C["text_muted"])),
    xgap=2, ygap=2,
))
fig_hm.update_layout(
    xaxis=dict(tickfont=dict(color=C["text_muted"], size=10)),
    yaxis=dict(tickfont=dict(color=C["text_muted"], size=10)),
)
apply_plotly_style(fig_hm, max(380, len(cv_list)*24))
st.plotly_chart(fig_hm, use_container_width=True, key="heatmap_cv")

# ─────────────────────────────────────────────
# BẢNG CHI TIẾT THEO CÔNG VIỆC
# ─────────────────────────────────────────────
with st.expander("📋 Bảng tổng hợp theo Công việc"):
    by_cv = df.groupby(["ma_cv","ten_cong_viec"]).agg(
        so_luot=("ti_le","count"),
        avg_tl=("ti_le","mean"),
        min_tl=("ti_le","min"),
        max_tl=("ti_le","max"),
        med_tl=("ti_le","median"),
        tong_cong=("so_cong","sum"),
    ).reset_index()
    by_cv = by_cv.sort_values("avg_tl", ascending=True).reset_index(drop=True)
    for col in ["avg_tl","min_tl","max_tl","med_tl"]:
        by_cv[col] = by_cv[col].round(1)
    by_cv["tong_cong"] = by_cv["tong_cong"].round(1)

    disp = by_cv.rename(columns={
        "ma_cv":"Mã", "ten_cong_viec":"Công việc",
        "so_luot":"Lượt", "avg_tl":"TB %", "min_tl":"Min %",
        "max_tl":"Max %", "med_tl":"Trung vị %", "tong_cong":"Tổng công"
    })

    def color_row(row):
        v = row["TB %"]
        bg = C["green_pale"] if v >= 80 else (C["amber_pale"] if v >= 60 else C["red_pale"])
        return [f"background-color:{bg}"] * len(row)

    st.dataframe(disp.style.apply(color_row, axis=1),
                 use_container_width=True, hide_index=True)