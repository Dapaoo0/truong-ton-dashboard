# Codebase Summary

Dự án này là một Farm Dashboard để quản lý chi phí, công việc, định mức và vật tư của nông trường. Hệ thống gồm hai phần chính: Pipeline ETL và Frontend Streamlit.

## 1. ETL Pipeline (`etl_sync.py`)
File python thực thi quá trình tải, chuyển đổi và lưu trữ dữ liệu từ nhiều nguồn Google Sheets vào database Supabase.
- Chức năng: 
  - Kéo data theo Farm (`--farm`).
  - Reload toàn bộ data (`--full-reload`).
  - Làm sạch (clean) và chuẩn hóa dữ liệu, loại bỏ lô ảo, gán các khóa ngoại (`lo_id`, `doi_id`, `cong_viec_id`) dựa trên Natural Keys.
  - Tự động tính toán `ti_le_display` cho các tác vụ cần theo dõi hiệu suất.
  
## 2. Streamlit Dashboard (`Home.py` và `pages/`)
Giao diện trực quan cho người dùng tương tác, lọc dữ liệu và xem biểu đồ.
- **Home**: Tổng quan.
- **`pages/1_Chi_Phi.py`**: Tab quản lý biến động chi phí, sử dụng data từ bảng `fact_nhat_ky_san_xuat` và `fact_vat_tu`.
- **`pages/2_Dinh_Muc.py`**: Hiển thị tỉ lệ hoàn thành công việc và đạt định mức. Phụ thuộc lớn vào các cột `dinh_muc` và `ti_le_display` của database.
- Cấu hình chung và giao diện được đặt trong `style.py` và module truy xuất DB nằm trong `db.py`.
