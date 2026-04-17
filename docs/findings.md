# Findings

- Streamlit UI có thể bị crash khi lấy dữ liệu rỗng (ví dụ: `min_d`, `max_d` trả về `NaT` khi không có dữ liệu `dinh_muc`). Luôn luôn phải sử dụng các guard condition (`if pd.isna()`) trước khi pass giá trị vào widget.
- Các lệnh INSERT vào Supabase với `psycopg2.extras.execute_values` rất hiệu quả, nhưng luôn phải cấu hình `ON CONFLICT DO NOTHING` dựa trên natural keys.
- Các dữ liệu liên quan đến Định Mức ở Team GSheets thường nằm ở cột "định mức", và phải được đẩy vào cột `dinh_muc` của `fact_nhat_ky_san_xuat`.
