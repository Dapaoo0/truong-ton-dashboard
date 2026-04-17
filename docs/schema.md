# Database Schema

## Bảng `fact_nhat_ky_san_xuat`
Bảng lưu trữ thông tin thực tế công việc hàng ngày của nông trường.
- `farm_id` (INT): Khóa ngoại liên kết tới `dim_farm`.
- `ngay` (DATE): Ngày ghi nhận.
- `doi_id` (INT): Khóa ngoại liên kết tới `dim_doi`.
- `lo_id` (INT): Khóa ngoại liên kết tới `dim_lo`.
- `cong_viec_id` (INT): Khóa ngoại liên kết tới `dim_cong_viec`.
- `so_cong` (NUMERIC): Số công thực tế.
- `klcv` (NUMERIC): Khối lượng công việc đã làm.
- `dinh_muc` (NUMERIC): Định mức khối lượng công việc trên 1 công.
- `ti_le_display` (NUMERIC): Tỉ lệ hoàn thành định mức (klcv / so_cong / dinh_muc * 100).
- `don_gia` (NUMERIC): Đơn giá trả cho công việc.
- `thanh_tien` (NUMERIC): Thành tiền (thường là so_cong * don_gia).
- `is_ho_tro` (BOOLEAN): Đánh dấu loại công hỗ trợ.
- `is_estimated` (BOOLEAN, default FALSE): Đánh dấu dữ liệu được ước lượng (imputed). Dùng khi fill data trống bằng phương pháp seasonal adjustment.

## Bảng `dim_lo`
- `lo_id` (INT): Khóa chính
- `lo_code` (VARCHAR): Mã lô
- `farm_id` (INT): FK tới farm
- `lo_type` (VARCHAR): Lô thực / Lô ảo

## Bảng `dim_doi`, `dim_farm`, `dim_cong_viec`
Chứa thông tin danh mục tương ứng để map dữ liệu từ tên gọi trên Google Sheets.
