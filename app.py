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

TX  = C["text"];    TM = C["text_muted"]; TS = C["text_sub"]
SF  = C["surface"]; SF2 = C["surface2"];  BD = C["border"]
GRN = C["green"];   AMB = C["amber"];     BLU = C["blue"]; RED = C["red"]
PUR = C["purple"];  GP  = C["green_pale"]

# ════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════
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

# ════════════════════════════════════════════
# NAVIGATION CARDS
# ════════════════════════════════════════════
_, col2, _ = st.columns([1, 3, 1])
with col2:
    c1, c2 = st.columns(2)
    _card = (
        f'border-radius:10px;padding:28px 20px;text-align:center;'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px'
    )
    with c1:
        st.markdown(
            f'<a href="/Chi_Phi" target="_self" style="text-decoration:none">'
            f'<div style="background:{SF};border:1px solid {BD};border-top:3px solid {GRN};{_card}">'
            f'<div style="font-size:38px">💰</div>'
            f'<div style="font-size:15px;font-weight:600;color:{TX}">Chi Phí</div>'
            f'<div style="font-size:12px;color:{TM}">Chi phí công nhân &amp; vật tư<br>theo farm · đội · lô</div>'
            f'</div></a>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f'<a href="/Dinh_Muc" target="_self" style="text-decoration:none">'
            f'<div style="background:{SF};border:1px solid {BD};border-top:3px solid {BLU};{_card}">'
            f'<div style="font-size:38px">📊</div>'
            f'<div style="font-size:15px;font-weight:600;color:{TX}">Định Mức</div>'
            f'<div style="font-size:12px;color:{TM}">Tỉ lệ hoàn thành công việc<br>biến động theo thời gian</div>'
            f'</div></a>',
            unsafe_allow_html=True
        )

# ════════════════════════════════════════════
# HƯỚNG DẪN SỬ DỤNG
# ════════════════════════════════════════════
st.markdown('<div style="margin-top:40px"></div>', unsafe_allow_html=True)
_, col2, _ = st.columns([1, 3, 1])
with col2:

    # ── Các biến style dùng chung ──
    BOX   = f'background:{SF};border:1px solid {BD};border-radius:10px;padding:32px 36px'
    TTL   = (f'font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;'
             f'color:{TM};margin-bottom:28px')
    PG_H  = (f'font-size:15px;font-weight:700;color:{TX};margin-bottom:6px')
    PG_S  = (f'font-size:12px;color:{TM};margin-bottom:20px;line-height:1.6')
    DIVID = f'border:none;border-top:1px solid {BD};margin:0 0 20px 0'

    ROW   = f'display:flex;gap:14px;align-items:flex-start;margin-bottom:18px'
    ICON  = (f'min-width:32px;height:32px;border-radius:8px;display:flex;align-items:center;'
             f'justify-content:center;font-size:15px;flex-shrink:0')
    BODY  = f'padding-top:2px'
    BH    = f'font-size:12px;font-weight:600;color:{TX};margin-bottom:3px'
    BD_   = f'font-size:12px;color:{TS};line-height:1.75'

    NOTE  = (f'background:{SF2};border-left:3px solid {BLU};border-radius:0 6px 6px 0;'
             f'padding:12px 16px;margin-top:4px;margin-bottom:18px;font-size:12px;'
             f'color:{TS};line-height:1.75')
    WARN  = (f'background:{C["amber_pale"]};border-left:3px solid {AMB};border-radius:0 6px 6px 0;'
             f'padding:12px 16px;margin-top:4px;margin-bottom:18px;font-size:12px;'
             f'color:{TS};line-height:1.75')

    TAG_G = (f'display:inline-block;background:{GP};color:{GRN};border-radius:4px;'
             f'font-size:10px;font-weight:700;padding:2px 7px;margin-right:4px;white-space:nowrap;'
             f'vertical-align:middle')
    TAG_A = (f'display:inline-block;background:{C["amber_pale"]};color:{AMB};border-radius:4px;'
             f'font-size:10px;font-weight:700;padding:2px 7px;margin-right:4px;white-space:nowrap;'
             f'vertical-align:middle')
    TAG_B = (f'display:inline-block;background:{SF2};color:{TM};border-radius:4px;'
             f'font-size:10px;font-weight:700;padding:2px 7px;margin-right:4px;white-space:nowrap;'
             f'vertical-align:middle')
    TAG_R = (f'display:inline-block;background:{C["red_pale"]};color:{RED};border-radius:4px;'
             f'font-size:10px;font-weight:700;padding:2px 7px;margin-right:4px;white-space:nowrap;'
             f'vertical-align:middle')

    FOOT  = (f'margin-top:28px;padding-top:16px;border-top:1px solid {BD};'
             f'font-size:11px;color:{TM};text-align:center;line-height:2.2')

    def row(icon, icon_bg, heading, detail):
        return (
            f'<div style="{ROW}">'
            f'<div style="{ICON};background:{icon_bg}">{icon}</div>'
            f'<div style="{BODY}">'
            f'<div style="{BH}">{heading}</div>'
            f'<div style="{BD_}">{detail}</div>'
            f'</div></div>'
        )

    # ════════════════════════════════
    # BUILD HTML
    # ════════════════════════════════
    html = f'<div style="{BOX}">'
    html += f'<div style="{TTL}">📖 Hướng dẫn sử dụng</div>'
    html += f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:40px">'

    # ══════════════════════════
    # CỘT TRÁI — TRANG CHI PHÍ
    # ══════════════════════════
    L = ''
    L += f'<div style="{PG_H}">💰 Trang Chi Phí</div>'
    L += f'<div style="{PG_S}">Theo dõi toàn bộ chi phí công nhân và vật tư. Có thể lọc và phóng to vào từng farm, đội hoặc lô cụ thể để xem chi tiết.</div>'
    L += f'<hr style="{DIVID}">'

    L += row("🔍", f"{GRN}18",
        "Bộ lọc ở thanh bên trái",
        f'Trước tiên chọn <span style="{TAG_G}">Farm</span> và khoảng <span style="{TAG_G}">Thời gian</span> muốn xem. '
        f'Có thể lọc thêm theo <span style="{TAG_G}">Loại lô</span>, <span style="{TAG_G}">Lô</span> hoặc <span style="{TAG_G}">Đội</span> cụ thể. '
        f'Toàn bộ biểu đồ và số liệu trên trang sẽ tự cập nhật ngay khi thay đổi bộ lọc.'
    )

    L += row("🏡", f"{GRN}18",
        "Card Farm — xem và chọn farm",
        f'Mỗi farm hiển thị thành một ô riêng gồm tổng chi phí, phần trăm chi phí Công và phần trăm chi phí Vật tư. '
        f'Bấm nút <span style="{TAG_G}">📊 Drill vào Farm</span> bên dưới ô để xem thêm biểu đồ chi tiết của farm đó: '
        f'xu hướng chi phí từng tháng và top đội tốn nhiều chi phí nhất. '
        f'Khi đang chọn, ô sẽ đổi sang màu vàng và hiện chữ <span style="{TAG_A}">ĐANG CHỌN</span>. '
        f'Bấm lại nút để bỏ chọn.'
    )

    L += row("🔵", f"{BLU}18",
        "Bubble Chart — phân tích chi phí theo Lô",
        f'Đây là biểu đồ bong bóng, mỗi bong bóng đại diện cho một lô. '
        f'Ba thông tin được hiển thị cùng lúc: vị trí <b style="color:{TX}">nằm ngang</b> thể hiện chi phí Công, '
        f'vị trí <b style="color:{TX}">nằm dọc</b> thể hiện chi phí Vật tư, '
        f'và <b style="color:{TX}">kích thước bong bóng</b> thể hiện tổng chi phí. '
        f'Bong bóng nằm ở góc trên phải là lô vừa tốn nhiều công vừa tốn nhiều vật tư. '
        f'Hover vào bong bóng để xem con số cụ thể. '
        f'<b style="color:{TX}">Click vào bong bóng</b> để drill vào lô đó, '
        f'biểu đồ xu hướng tháng và công đoạn sẽ hiện ra bên dưới.'
    )

    L += row("👥", f"{GRN}18",
        "Biểu đồ Đội — Chính chủ và Hỗ trợ",
        f'Biểu đồ thanh ngang thể hiện tổng chi phí Công của từng đội, '
        f'được chia thành 2 phần: <span style="{TAG_G}">Chính chủ</span> là công do chính đội đó thực hiện, '
        f'và <span style="{TAG_R}">Hỗ trợ</span> là công được điều từ đội khác sang hỗ trợ. '
        f'Các thanh được sắp xếp từ thấp đến cao để dễ so sánh. '
        f'<b style="color:{TX}">Click vào thanh</b> để drill vào đội đó và xem chi phí theo từng farm và xu hướng theo tháng.'
    )

    L += row("🌀", f"{BLU}18",
        "Sunburst Chart — cơ cấu chi phí theo tầng",
        f'Hai biểu đồ vòng tròn ở cuối trang thể hiện cơ cấu chi tiết. '
        f'Biểu đồ bên trái là chi phí Công theo tầng Farm → Đội → Công đoạn. '
        f'Biểu đồ bên phải là chi phí Vật tư theo tầng Farm → Lô → Loại vật tư. '
        f'Mảnh to hơn đồng nghĩa với chi phí lớn hơn. '
        f'<b style="color:{TX}">Click vào mảnh bất kỳ</b> để phóng to tầng đó và xem chi tiết hơn. '
        f'Click vào phần tâm (vòng tròn nhỏ ở giữa) để quay trở lại tầng trên.'
    )

    L += (
        f'<div style="{NOTE}">'
        f'<b style="color:{TX}">Cách bỏ filter drill:</b> Sau khi click drill, '
        f'thanh bên trái sẽ hiện một badge màu vàng ghi tên mục đang được phóng to. '
        f'Bấm dấu <b style="color:{AMB}">✕</b> trên badge đó để xóa filter và quay về xem toàn bộ dữ liệu. '
        f'Có thể kết hợp drill nhiều cấp cùng lúc, ví dụ chọn Farm 126 và Đội BVTV '
        f'để chỉ xem chi phí của đội BVTV hoạt động tại Farm 126.'
        f'</div>'
    )

    L += '</div>'

    # ═══════════════════════════════
    # CỘT PHẢI — TRANG ĐỊNH MỨC
    # ═══════════════════════════════
    R = ''
    R += f'<div style="{PG_H}">📊 Trang Định Mức</div>'
    R += f'<div style="{PG_S}">Theo dõi mức độ hoàn thành công việc so với kế hoạch định mức đã đặt ra. Phát hiện công việc hoặc đội nào đang thực hiện dưới mức kỳ vọng.</div>'
    R += f'<hr style="{DIVID}">'

    R += row("📐", f"{BLU}18",
        "Định mức là gì và cách tính tỉ lệ hoàn thành",
        f'Định mức là số lượng công việc kỳ vọng hoàn thành trên mỗi công lao động trong một ngày. '
        f'Ví dụ: định mức thu hoạch chuối là 500 kg mỗi công. '
        f'Nếu một công nhân thực tế thu được 450 kg thì tỉ lệ hoàn thành = 450 ÷ 500 × 100% = 90%. '
        f'<b style="color:{GRN}">Trên 100%</b> là vượt định mức (tốt). '
        f'<b style="color:{RED}">Dưới 80%</b> là cần chú ý.'
    )

    R += row("📅", f"{BLU}18",
        "Chọn độ chi tiết thời gian ở thanh bên trái",
        f'Mục <b style="color:{TX}">Xem biến động theo</b> cho phép chọn '
        f'<span style="{TAG_B}">Ngày</span> <span style="{TAG_B}">Tuần</span> '
        f'<span style="{TAG_B}">Tháng</span> <span style="{TAG_B}">Quý</span> <span style="{TAG_B}">Năm</span>. '
        f'Chọn Ngày để thấy biến động chi tiết từng ngày. '
        f'Chọn Tháng hoặc Quý để thấy xu hướng dài hạn và dễ so sánh các kỳ với nhau.'
    )

    R += row("📈", f"{BLU}18",
        "Đọc biểu đồ đường xu hướng",
        f'Biểu đồ đường hiển thị 2 chỉ số theo thời gian: '
        f'đường <b style="color:{GRN}">xanh</b> là trung bình, đường <b style="color:{AMB}">cam</b> là trung vị. '
        f'Nên dùng <b style="color:{AMB}">trung vị</b> để đánh giá vì nó không bị kéo lệch bởi '
        f'những ngày bất thường như ngày nghỉ hay ngày sự cố. '
        f'Hai đường tham chiếu nằm ngang tại 80% và 100% giúp nhận biết nhanh kỳ nào đạt hay không đạt.'
    )

    R += row("📊", f"{BLU}18",
        "Drill theo Farm, Đội và Lô",
        f'Ba biểu đồ thanh ngang thể hiện tỉ lệ hoàn thành trung bình của từng Farm, Đội và Lô. '
        f'Màu sắc thể hiện mức độ: <b style="color:{GRN}">xanh</b> trên 80%, '
        f'<b style="color:{AMB}">vàng</b> từ 60 đến 80%, <b style="color:{RED}">đỏ</b> dưới 60%. '
        f'Thanh nào ngắn và màu đỏ là nơi cần ưu tiên xem xét. '
        f'<b style="color:{TX}">Click vào thanh</b> để lọc toàn bộ trang chỉ hiển thị dữ liệu của mục đó.'
    )

    R += row("🗓️", f"{BLU}18",
        "Heatmap công việc theo tháng",
        f'Bảng màu thể hiện tỉ lệ hoàn thành của 20 công việc có nhiều dữ liệu nhất, '
        f'theo từng tháng. Mỗi ô là giao của một loại công việc và một tháng cụ thể. '
        f'<b style="color:{GRN}">Màu xanh đậm</b> là hoàn thành tốt (gần hoặc vượt 100%). '
        f'<b style="color:{AMB}">Màu vàng</b> là trung bình. '
        f'<b style="color:{RED}">Màu đỏ</b> là thấp hơn kỳ vọng. '
        f'Hover vào ô bất kỳ để xem con số tỉ lệ chính xác.'
    )

    R += (
        f'<div style="{NOTE}">'
        f'<b style="color:{TX}">Bảng tổng hợp công việc:</b> Bấm vào mục '
        f'"📋 Bảng tổng hợp theo Công việc" ở cuối trang để mở bảng chi tiết. '
        f'Bảng liệt kê toàn bộ công việc sắp xếp từ tỉ lệ hoàn thành thấp nhất, '
        f'kèm theo trung bình, trung vị, min và max trong kỳ đang xem. '
        f'Đây là nơi nhanh nhất để tìm ra công việc nào đang có vấn đề.'
        f'</div>'
    )

    R += '</div>'

    # Ghép lại
    html += L + R
    html += '</div>'  # end grid

    # Footer
    html += (
        f'<div style="{FOOT}">'
        f'Dữ liệu tự động làm mới mỗi 5 phút &nbsp;·&nbsp; '
        f'<span style="color:{GRN}">●</span>&nbsp;Farm 126 &nbsp;'
        f'<span style="color:{BLU}">●</span>&nbsp;Farm 157 &nbsp;'
        f'<span style="color:{PUR}">●</span>&nbsp;Farm 195 &nbsp;·&nbsp; '
        f'Đơn vị tiền tệ: VND'
        f'</div>'
    )

    html += '</div>'  # end BOX

    st.markdown(html, unsafe_allow_html=True)