import streamlit as st
import sys, os
sys.path.append(os.path.dirname(__file__))
from style import inject_css, C

st.set_page_config(
    page_title="Trường Tồn · Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

TX  = C["text"];   TM = C["text_muted"]; TS = C["text_sub"]
SF  = C["surface"]; BD = C["border"]
GRN = C["green"];  AMB = C["amber"];     BLU = C["blue"]; RED = C["red"]

# ─── Header ───────────────────────────────────
st.markdown(
    f'<div style="text-align:center;padding:48px 0 32px">'
    f'<div style="font-size:52px;margin-bottom:16px">🌿</div>'
    f'<div style="font-size:26px;font-weight:700;color:{TX};letter-spacing:-0.01em">'
    f'CÔNG TY CỔ PHẦN SẢN XUẤT &amp; THƯƠNG MẠI TRƯỜNG TỒN</div>'
    f'<div style="font-size:13px;color:{TM};margin-top:10px;letter-spacing:0.08em;text-transform:uppercase">'
    f'Hệ thống theo dõi chi phí &amp; hiệu suất sản xuất</div>'
    f'<div style="width:60px;height:2px;background:{GRN};margin:20px auto 0;border-radius:99px"></div>'
    f'</div>',
    unsafe_allow_html=True
)

# ─── Navigation cards ─────────────────────────
_, col2, _ = st.columns([1, 3, 1])
with col2:
    c1, c2 = st.columns(2)
    card = (f'border-radius:10px;padding:28px 20px;text-align:center;'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px')
    with c1:
        st.markdown(
            f'<a href="/Chi_Phi" target="_self" style="text-decoration:none">'
            f'<div style="background:{SF};border:1px solid {BD};border-top:3px solid {GRN};{card}">'
            f'<div style="font-size:38px">💰</div>'
            f'<div style="font-size:15px;font-weight:600;color:{TX}">Chi Phí</div>'
            f'<div style="font-size:12px;color:{TM}">Chi phí công nhân &amp; vật tư<br>theo farm · đội · lô</div>'
            f'</div></a>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<a href="/Dinh_Muc" target="_self" style="text-decoration:none">'
            f'<div style="background:{SF};border:1px solid {BD};border-top:3px solid {BLU};{card}">'
            f'<div style="font-size:38px">📊</div>'
            f'<div style="font-size:15px;font-weight:600;color:{TX}">Định Mức</div>'
            f'<div style="font-size:12px;color:{TM}">Tỉ lệ hoàn thành công việc<br>biến động theo thời gian</div>'
            f'</div></a>', unsafe_allow_html=True)

# ─── Hướng dẫn sử dụng ───────────────────────
st.markdown('<div style="margin-top:36px"></div>', unsafe_allow_html=True)
_, col2, _ = st.columns([1, 3, 1])
with col2:
    h3  = f'font-size:13px;font-weight:600;color:{TX};margin-bottom:10px'
    txt = f'font-size:12px;color:{TS};line-height:2.0'
    tag_g = f'display:inline-block;background:{C["green_pale"]};color:{GRN};border-radius:4px;font-size:10px;font-weight:600;padding:1px 6px;margin-right:4px'
    tag_b = f'display:inline-block;background:{C["surface2"]};color:{TM};border-radius:4px;font-size:10px;font-weight:600;padding:1px 6px;margin-right:4px'

    st.markdown(
        f'<div style="background:{SF};border:1px solid {BD};border-radius:10px;padding:28px 32px">'

        # Tiêu đề
        f'<div style="font-size:13px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.1em;color:{TM};margin-bottom:20px">📖 Hướng dẫn sử dụng</div>'

        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">'

        # ── Cột trái: Chi Phí ──
        f'<div>'
        f'<div style="{h3}">💰 Trang Chi Phí</div>'
        f'<div style="{txt}">'

        f'<span style="{tag_g}">FARM</span>'
        f'Click vào nút dưới mỗi card farm để drill — biểu đồ xu hướng &amp; top đội hiện ngay bên dưới<br>'

        f'<span style="{tag_g}">LÔ</span>'
        f'Bubble chart: trục X = công, Y = vật tư, size = tổng — click bubble để drill lô đó<br>'

        f'<span style="{tag_g}">ĐỘI</span>'
        f'Stacked bar Chính chủ/Hỗ trợ — click thanh để drill, breakdown xuất hiện bên dưới<br>'

        f'<span style="{tag_b}">SUNBURST</span>'
        f'Click mảnh để zoom sâu (Farm→Đội→Công đoạn) · Click tâm để quay lại<br>'

        f'<span style="{tag_b}">DRILL</span>'
        f'Sidebar hiện badge "Drill đang bật" · Click ✕ để bỏ filter'

        f'</div></div>'

        # ── Cột phải: Định Mức ──
        f'<div>'
        f'<div style="{h3}">📊 Trang Định Mức</div>'
        f'<div style="{txt}">'

        f'<span style="{tag_g}">GRANULARITY</span>'
        f'Chọn Ngày/Tuần/Tháng/Quý/Năm để xem biến động tỉ lệ hoàn thành theo thời gian<br>'

        f'<span style="{tag_g}">ĐƯỜNG</span>'
        f'<b style="color:{GRN}">Trung bình</b> (xanh) và <b style="color:{AMB}">trung vị</b> (cam) — trung vị ít bị outlier hơn<br>'

        f'<span style="{tag_g}">FARM/ĐỘI/LÔ</span>'
        f'Click bar để drill — toàn bộ biểu đồ tự lọc theo mục đã chọn<br>'

        f'<span style="{tag_b}">HEATMAP</span>'
        f'Công việc × Tháng — <b style="color:{GRN}">xanh = đạt cao</b>, <b style="color:{RED}">đỏ = thấp</b><br>'

        f'<span style="{tag_b}">QUY ƯỚC</span>'
        f'100% = đúng định mức · &gt;100% = vượt định mức · Mở bảng cuối trang để xem chi tiết'

        f'</div></div>'
        f'</div>'  # end grid

        # Footer
        f'<div style="margin-top:20px;padding-top:16px;border-top:1px solid {BD};'
        f'font-size:11px;color:{TM};text-align:center">'
        f'Dữ liệu cập nhật mỗi 5 phút &nbsp;·&nbsp; '
        f'<span style="color:{GRN}">●</span> Farm 126 &nbsp;'
        f'<span style="color:{BLU}">●</span> Farm 157 &nbsp;'
        f'<span style="color:{C["purple"]}">●</span> Farm 195 &nbsp;·&nbsp; '
        f'Đơn vị tiền tệ: VND'
        f'</div>'

        f'</div>',
        unsafe_allow_html=True
    )