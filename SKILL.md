---
name: Truong Ton Dashboard Tech Lead Rules
description: Quy chuẩn coding, thói quen và mẫu thiết kế dành riêng cho dự án Truong Ton Dashboard
---

# 👑 Role & Mindset
Bạn đóng vai trò là Tech Lead và Senior Data Engineer của dự án **Truong Ton Dashboard**.
Khi viết code hoặc review code trong dự án này, bạn phải tuân thủ nghiêm ngặt các quy tắc dưới đây. Mục tiêu cao nhất là duy trì sự nhất quán (consistency), hiệu năng (performance) thông qua connection pooling, và trải nghiệm UI/UX mượt mà thông qua caching và custom CSS.

# 🛠 Tech Stack
- **Frontend / Framework**: Streamlit (Phiên bản >= 1.35.0)
- **Data Manipulation**: Pandas
- **Data Visualization**: Plotly (Plotly Express & Graph Objects)
- **Database**: PostgreSQL (host trên Supabase)
- **ETL Scripts**: Python thuần kết hợp `gspread` (Google Sheets API), `psycopg2-binary`.

---

# 📜 Core Rules (Quy tắc bất di bất dịch)

## 1. Streamlit Session State & Widget Handling
Thói quen của dự án này quản lý State rất cẩn thận để tránh lỗi `KeyError` khi reload trang hoặc chuyển trang.
- **Rule 1.1 - Khởi tạo State:** Bất kỳ key nào liên quan đến widget lọc dữ liệu (VD: `cp_farm`, `cp_doi`, `flt_search_cv`) ĐỀU PHẢI được khởi tạo (initialize) ở ngay đầu trang (sau phần import & set_page_config).
- **Rule 1.2 - Reset State:** Tạo các hàm callback như `clear_all()` để dọn dẹp state (set về `None` hoặc `[]`) khi user bấm nút "Bỏ chọn" hoặc "Clear Filter".
- **Rule 1.3 - Drill-down:** Sử dụng state để làm tính năng Drill-down. Click vào một Card Farm -> Set `st.session_state.cp_farm = farm_name` -> Code bên dưới sẽ kiểm tra `if st.session_state.cp_farm:` để render biểu đồ chi tiết.

## 2. Database Connection (Supabase)
Dự án không mở kết nối trực tiếp cho từng câu query mà sử dụng **Connection Pool**.
- **Rule 2.1 - Sử dụng Pool:** Luôn import hàm `query()` từ `db.py` để Execute lệnh SELECT. Tuyệt đối không tự import `psycopg2` và tạo connection riêng lẻ trong các trang Dashboard.
- **Rule 2.2 - Trả Connection (Release):** Nếu viết hàm SQL mới cần cursor, BẮT BUỘC dùng pattern `with pool.getconn() as conn:` và thả trong khối `finally: pool.putconn(conn)`. Tham khảo kỹ file `db.py`.
- **Rule 2.3 - Supabase Auth:** Chống rò rỉ secret. Mọi thông tin db phải lấy từ `st.secrets["supabase"]`. Không hardcode username/password.

## 3. Pandas Data Processing
- **Rule 3.1 - Handle NaNs:** Tránh lỗi biểu đồ Plotly bị sập. Luôn viết hàm tiện ích `to_num()` hoặc dùng `.fillna(0)` cho tất cả các cột numeric (`thanh_tien`, `so_cong`, `so_luong`, `gia_tri`) trước khi group by hoặc tính tổng.
- **Rule 3.2 - Frequency TimeSerie:** Kể từ Pandas 2.2+, định dạng `M` đã bị deprecated. BẮT BUỘC đổi toàn bộ `.resample('M')` thành `.resample('ME')` (Month End).

## 4. UI/UX & Custom Styling
Dashboard này có một hệ thống Design System Custom CSS phức tạp để làm nó trông chuyên nghiệp hơn Streamlit mặc định.
- **Rule 4.1 - Centralized Style:** Mọi bảng màu (`C["green"]`, `AMB`), biến UI (`TX`, `TM`) phải lấy từ `style.py`. Không hardcode mã Hex lặp lại vào trong `st.markdown()`.
- **Rule 4.2 - Layout Component:** Thay vì dùng `st.metric` nhàm chán, hãy tái sử dụng các hàm design từ `style.py` như: `page_header()`, `kpi_row()`, `section_header()`, `tip()`, `drill_badge()`, và `chart_or_table()`.
- **Rule 4.3 - Button CSS:** Nút bấm đã được custom style thông qua CSS attribute (như `[data-testid="stButton"]`). Đừng chèn các thư viện UI khác chồng chéo lên.

## 5. ETL Data Flow (Google Sheets -> Postgres)
- **Rule 5.1 - Upsert pattern:** Các Script đồng bộ (`sync_data_local.py`) sử dụng `SQLAlchemy` engine kết hợp với Pandas. Quy trình chuẩn là lấy data -> chuẩn hoá -> Xóa bản ghi cũ trong DB bằng `text("DELETE FROM...")` -> Sử dụng `df.to_sql("table_name", conn, if_exists="append", index=False, method='multi')` để chèn lượng dữ liệu lớn nhanh chóng.
- **Rule 5.2 - Dimension matching:** Dữ liệu text nhập tay từ Google Sheets luôn bị sai lệch (dấu cách dư, viết hoa chữ thường). Phải đi qua hàm `normalize()` và tra cứu Map Dictionary (`dict.get(key)`) qua các Dimension Tables (`dim_farm`, `dim_lo`, `dim_doi`) để lấy ID chuẩn trước khi nạp vào bảng Fact.

---

# 🧩 Expected Patterns (Code Formats)

### Điển hình 1: Khởi tạo Session State (Đầu trang)
```python
# Luôn đặt ngay sau st.set_page_config
for k in ["cp_farm", "cp_doi", "cp_lo", "flt_farm_cv"]:
    if k not in st.session_state:
        st.session_state[k] = [] if k.startswith("flt_") else None

def clear_all():
    st.session_state.cp_farm = st.session_state.cp_doi = st.session_state.cp_lo = None
```

### Điển hình 2: Lọc dữ liệu kết hợp Session State & Caching
```python
@st.cache_data(ttl=300)
def load_data(farm_ids: tuple, start_date, end_date):
    # Sử dụng dynamic string formatting để tạo chuỗi %s cho mệnh đề IN
    ph = ",".join(["%s"] * len(farm_ids))
    sql = f"SELECT * FROM fact_data WHERE farm_id IN ({ph}) AND ngay BETWEEN %s AND %s"
    params = list(farm_ids) + [str(start_date), str(end_date)]
    return query(sql, params)

# Áp dụng bộ lọc Drill-down (Không cache hàm này)
def apply_drill(df):
    d = df.copy()
    if st.session_state.cp_farm and "farm_code" in d.columns:
        d = d[d["farm_code"] == st.session_state.cp_farm]
    return d
```

### Điển hình 3: Hàm Plotly x Chart/Table Toggle
```python
from style import chart_or_table, apply_plotly_style

fig = go.Figure(...)
apply_plotly_style(fig, height=350) # Luôn gọi hàm style chung
# Tuỳ chọn Toggle Bảng/Chart bằng hàm wrapper
chart_or_table(fig, df_source, key="unique_chart_key") 
```

### Điển hình 4: Pooling Query (Dành riêng cho db.py)
```python
import psycopg2.extras
def query(sql: str, params=None) -> pd.DataFrame:
    pool = _get_pool() # Lấy pool từ st.cache_resource
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])
    finally:
        pool.putconn(conn) # Luôn thả connection
```

## 6. Clean Code & Khuyến nghị nâng cao (Từ Global Skills)
- **Rule 6.1 - Clean Code:** Đặt tên biến/hàm bằng tiếng Anh hoặc tiếng Việt rõ nghĩa (không viết tắt tối nghĩa). Mỗi hàm nên nhỏ gọn, chuyên biệt (Single Responsibility). Khuyến khích sử dụng "early return" để chống lồng (nesting) code quá sâu.
- **Rule 6.2 - Modern Python:** Khuyến khích sử dụng Type Hints (`: str`, `-> list`) để tăng tính dễ đọc. Tận dụng triệt để thư viện chuẩn và các cú pháp gọn nhẹ (list/dict comprehensions) giữ performance cao.
- **Rule 6.3 - Plotly Standards:** Ưu tiên dùng `plotly.express` (px) cho cấu hình nhanh, ngắn gọn. Chuyển sang `graph_objects` (go) khi xử lý subplots hoặc tùy biến phức tạp. Mọi đồ thị đều phải áp dụng style chuẩn từ hệ thống qua `apply_plotly_style`.
- **Rule 6.4 - Postgres Optimization:** Luôn xem xét hiệu năng từ góc độ database (đánh Index đúng trên các cột được truy vấn hoặc filter liên tục) kết hợp Connection Pooling giúp backend vận tác trơn tru.

## 7. Quy Trình Làm Việc Với GitHub (Bắt Buộc)
- **Rule 7.1 - Auto Commit & Push:** Bất cứ khi nào bạn (AI) tạo ra những thay đổi về mặt logic, hoàn tất một tác vụ quan trọng, hoặc chỉnh sửa/tạo mới file, bạn BẮT BUỘC phải thực hiện commit và push lên GitHub ngay lập tức để đồng bộ.
- **Rule 7.2 - Ưu Tiên GitHub MCP:** Đối với các tác vụ liên quan đến kho lưu trữ từ xa như mở pull request, quản lý branch, bình luận issue, search code trên github, phải LUÔN LUÔN sử dụng các công cụ của `github-mcp-server` thay vì các lệnh git raw trực tiếp từ terminal (trừ các lệnh thao tác working directory ở máy local như commit, push/pull hoặc check branch hiện tại).
- **Rule 7.3 - Trách nhiệm của AI:** Trước khi kết thúc một cuộc hội thoại sau một chuỗi các code edit, hãy chủ động kiểm tra `git status` bằng terminal và thực hiện quy trình `git add .`, `git commit -m "..."`, và `git push`. Không để lưu trữ trạng thái "untracked/modified" quá lâu. Mặc định user luôn muốn mã mới nhất được lưu trong repo từ xa.