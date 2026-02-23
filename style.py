import streamlit as st
import plotly.graph_objects as go

C = {
    "bg":          "#0D1117",
    "surface":     "#161B22",
    "surface2":    "#21262D",
    "surface3":    "#30363D",
    "border":      "#30363D",
    "border2":     "#484F58",
    "text":        "#E6EDF3",
    "text_sub":    "#C9D1D9",
    "text_muted":  "#8B949E",
    "green":       "#3FB950",
    "green_dark":  "#238636",
    "green_pale":  "#0D2818",
    "amber":       "#F0A800",
    "amber_pale":  "#271D00",
    "blue":        "#58A6FF",
    "blue_pale":   "#0D2045",
    "red":         "#F85149",
    "red_pale":    "#2D0E0E",
    "purple":      "#BC8CFF",
}

BAR_CONG   = C["green"]
BAR_VAT_TU = C["amber"]
CLR_DAT    = C["green"]
CLR_KHONG  = C["red"]
CLR_WARN   = C["amber"]

PLOTLY_LAYOUT = dict(
    font=dict(family="DM Sans, sans-serif", size=12, color=C["text_sub"]),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor=C["surface3"], zerolinecolor=C["border2"],
               linecolor=C["border"], tickfont=dict(color=C["text_muted"], size=11)),
    yaxis=dict(gridcolor=C["surface3"], zerolinecolor=C["border2"],
               linecolor=C["border"], tickfont=dict(color=C["text_muted"], size=11)),
    hoverlabel=dict(bgcolor=C["surface2"], bordercolor=C["border2"],
                    font=dict(color=C["text"], size=12)),
    margin=dict(t=44, b=48, l=8, r=8),
    legend=dict(orientation="h", y=-0.12, x=0, bgcolor="rgba(0,0,0,0)",
                borderwidth=0, font=dict(color=C["text_sub"], size=11)),
    colorway=[C["green"], C["amber"], C["blue"], C["purple"], C["red"], "#79C0FF"],
)

def apply_plotly_style(fig, height=360):
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig

def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    section.main, .main .block-container {{
        background-color: {C["bg"]} !important;
        color: {C["text"]} !important;
        font-family: 'DM Sans', sans-serif !important;
    }}
    [data-testid="stSidebar"] {{
        background-color: {C["surface"]} !important;
        border-right: 1px solid {C["border"]} !important;
    }}
    [data-testid="stSidebar"] * {{ color: {C["text_sub"]} !important; }}
    [data-testid="stSidebar"] label {{
        color: {C["text_muted"]} !important;
        font-size: 12px !important; font-weight: 500 !important;
    }}
    h1 {{
        color: {C["text"]} !important; font-weight: 600 !important;
        font-size: 24px !important; letter-spacing: -0.02em !important;
    }}
    p, li, span {{ color: {C["text_sub"]} !important; }}

    /* ── Multiselect scroll panel ── */
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
        background-color: {C["surface2"]} !important;
        border-color: {C["border"]} !important;
        border-radius: 6px !important;
        max-height: 80px !important;
        overflow-y: auto !important;
    }}
    [data-baseweb="tag"] {{
        background-color: {C["surface3"]} !important;
        border-color: {C["border2"]} !important;
        border-radius: 4px !important;
    }}
    [data-baseweb="tag"] span {{ color: {C["text"]} !important; font-size: 11px !important; }}

    /* ── Inputs ── */
    [data-baseweb="input"] input, [data-testid="stDateInput"] input {{
        background-color: {C["surface2"]} !important;
        color: {C["text"]} !important;
        border-color: {C["border"]} !important;
        border-radius: 6px !important;
    }}
    [data-testid="stCheckbox"] label span {{ color: {C["text_sub"]} !important; font-size: 12px !important; }}
    [data-testid="stSlider"] div[data-baseweb="slider"] div {{ background-color: {C["green"]} !important; }}

    /* ── Button ── */
    [data-testid="stButton"] > button {{
        background-color: {C["surface2"]} !important; color: {C["text_sub"]} !important;
        border: 1px solid {C["border2"]} !important; border-radius: 6px !important;
        font-size: 12px !important; font-weight: 500 !important;
    }}
    [data-testid="stButton"] > button:hover {{
        background-color: {C["surface3"]} !important; color: {C["text"]} !important;
    }}

    /* ── Expander ── */
    [data-testid="stExpander"] {{
        background-color: {C["surface"]} !important;
        border: 1px solid {C["border"]} !important; border-radius: 8px !important;
    }}
    [data-testid="stExpander"] summary span {{ color: {C["text_sub"]} !important; font-size: 13px !important; }}

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {{
        border-radius: 8px !important; border: 1px solid {C["border"]} !important;
    }}

    [data-testid="stAlert"] {{
        background-color: {C["surface2"]} !important; border-radius: 6px !important;
        border: none !important; color: {C["text_sub"]} !important;
    }}
    hr {{ border-color: {C["border"]} !important; margin: 16px 0 !important; }}
    [data-testid="metric-container"] {{ display: none; }}
    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: {C["bg"]}; }}
    ::-webkit-scrollbar-thumb {{ background: {C["surface3"]}; border-radius: 99px; }}
    </style>
    """, unsafe_allow_html=True)


def page_header(icon, title, subtitle=""):
    sub = f'<div style="font-size:13px;color:{C["text_muted"]};margin-top:3px">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:14px;padding:16px 0;'
        f'border-bottom:1px solid {C["border"]};margin-bottom:20px">'
        f'<div style="font-size:26px">{icon}</div>'
        f'<div><div style="font-size:21px;font-weight:600;color:{C["text"]};letter-spacing:-0.02em">{title}</div>{sub}</div>'
        f'</div>',
        unsafe_allow_html=True)


def kpi_card(label, value, delta="", delta_positive=True, icon="", color=None, footnote=""):
    color  = color or C["green"]
    dc     = C["green"] if delta_positive else C["red"]
    tm, tx, sf, bd = C["text_muted"], C["text"], C["surface"], C["border"]
    parts = [
        f'<div style="background:{sf};border:1px solid {bd};border-top:2px solid {color};'
        f'border-radius:8px;padding:16px 18px;height:100%">',
        f'<div style="font-size:18px;margin-bottom:6px">{icon}</div>' if icon else "",
        f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.1em;color:{tm}">{label}</div>',
        f'<div style="font-size:22px;font-weight:600;color:{tx};'
        f"font-family:'DM Mono',monospace;letter-spacing:-0.01em;margin-top:5px;line-height:1\">{value}</div>",
        f'<div style="font-size:11px;color:{dc};font-weight:500;margin-top:3px">{delta}</div>' if delta else "",
        f'<div style="font-size:10px;color:{tm};margin-top:6px">{footnote}</div>' if footnote else "",
        '</div>',
    ]
    st.markdown("".join(parts), unsafe_allow_html=True)


def kpi_row(items):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            kpi_card(**item)
    st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)


def progress_bar(pct, threshold, label=""):
    color = CLR_DAT if pct >= threshold else (CLR_WARN if pct >= threshold * 0.8 else CLR_KHONG)
    lbl = f'<div style="font-size:11px;color:{C["text_muted"]};margin-bottom:5px">{label}</div>' if label else ""
    st.markdown(
        lbl +
        f'<div style="background:{C["surface2"]};border-radius:99px;height:20px;'
        f'overflow:hidden;border:1px solid {C["border"]}">'
        f'<div style="background:{color};width:{min(pct,100):.1f}%;height:100%;'
        f"display:flex;align-items:center;padding:0 10px;color:#fff;font-size:11px;"
        f"font-weight:600;font-family:'DM Mono',monospace\">{pct:.1f}%</div></div>"
        f'<div style="margin-bottom:16px"></div>',
        unsafe_allow_html=True)


def section_header(title, description=""):
    desc = f'<span style="color:{C["text_muted"]};font-size:11px;margin-left:8px">{description}</span>' if description else ""
    st.markdown(
        f'<div style="margin:24px 0 12px 0;padding-bottom:8px;border-bottom:1px solid {C["border"]}">'
        f'<span style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.1em;color:{C["text_sub"]}">{title}</span>{desc}</div>',
        unsafe_allow_html=True)


def tip(text):
    st.markdown(
        f'<div style="background:{C["blue_pale"]};border:1px solid {C["blue"]}33;'
        f'border-radius:6px;padding:8px 12px;font-size:12px;color:{C["blue"]};margin-bottom:12px">'
        f'💡 {text}</div>',
        unsafe_allow_html=True)


def drill_badge(label, value, key_suffix, on_clear):
    st.markdown(
        f'<div style="background:{C["green_pale"]};border:1px solid {C["green_dark"]};'
        f'border-radius:6px;padding:7px 12px;margin:4px 0;font-size:12px">'
        f'<span style="color:{C["text_muted"]}">{label}:</span>'
        f'<span style="color:{C["green"]};font-weight:600;margin-left:4px">{value}</span></div>',
        unsafe_allow_html=True)
    st.button("✕ Bỏ lọc", on_click=on_clear, key=f"clear_{key_suffix}")