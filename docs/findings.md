# Findings

- Streamlit UI có thể bị crash khi lấy dữ liệu rỗng (ví dụ: `min_d`, `max_d` trả về `NaT` khi không có dữ liệu `dinh_muc`). Luôn luôn phải sử dụng các guard condition (`if pd.isna()`) trước khi pass giá trị vào widget.
- Các lệnh INSERT vào Supabase với `psycopg2.extras.execute_values` rất hiệu quả, nhưng luôn phải cấu hình `ON CONFLICT DO NOTHING` dựa trên natural keys.
- Các dữ liệu liên quan đến Định Mức ở Team GSheets thường nằm ở cột "định mức", và phải được đẩy vào cột `dinh_muc` của `fact_nhat_ky_san_xuat`.
- **BVTV doi_name mismatch**: GSheet của đội BVTV ghi cột "Đội Thực Hiện" là nơi đội đi làm (NT1, NT2, Farm 157...) chứ không phải tên đội BVTV. Cần override `doi_name` khi đọc từ team sheets. Tương tự có thể xảy ra với Đội Cơ Giới, Đội Điện Nước.
- **Data imputation**: Khi fill data trống, dùng phương pháp clone tháng gần nhất + seasonal ratio từ farm tương tự. Đánh dấu bằng `is_estimated = TRUE`. Script `fill_bvtv_gaps.py` có thể chạy lại an toàn (idempotent — xóa estimated cũ trước khi insert mới).
- **Lô "11" trùng lặp (Farm 157)**: Lô "11" (lo_id=46, area_ha=5.14) là tổng của 11A (2.51 ha) + 11B (2.40 ha). Vì cả 11A và 11B đều đã tồn tại riêng trong `dim_lo`, lô "11" đã được đặt `is_active = false` (2026-05-05). Giữ lại vì có 415 dòng dữ liệu lịch sử trong `fact_nhat_ky_san_xuat`. Khi query diện tích Farm 157, cần lọc `is_active = true` để tránh tính trùng.
