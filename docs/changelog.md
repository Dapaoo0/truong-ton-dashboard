# Changelog

All notable changes to this project will be documented in this file.

## 2026-04-20
### Fixed
- **DB: Xóa outlier NK 335 công** — Xóa 1 record bất thường: NT1, Farm 157, 23/03/2026, "Chẻ + Cắm Tiêu Định Vị" lô B5, 335 công = 83.75 triệu (P99 toàn farm chỉ 10.5 công).
- **DB: Chuyển base_lot lô "11" → "11A"** — Đợt trồng 22/01/2026 (2,737 cây) gắn đúng vào lô 11A (lo_id=77).

### Added
- **Cột `dien_tich_trong`** — Thêm cột `NUMERIC(8,2)` vào `base_lots` lưu diện tích trồng thực tế (ha) cho 18 đợt trồng Farm 157.
- **ETL: NK outlier filter** — Thêm rule skip records công có `thanh_tien > 20 triệu VND/record` (nguyên nhân: nhập sai số công). Áp dụng song song với VT outlier filter (100 triệu).

## [Unreleased]
- Added ETL sync for Dinh Muc

## 2026-04-18
### Fixed
- **ETL: Override doi_name cho team sheets** — Khi đọc từ GSheet của đội (BVTV, Cơ Giới, etc.), force `doi_id` theo tên đội thay vì cột "Đội Thực Hiện" trong GSheet. Fix lỗi BVTV data bị gán nhầm cho NT1/NT2.

### Added
- **Cột `is_estimated`** — Thêm cột boolean vào `fact_nhat_ky_san_xuat` để đánh dấu dữ liệu ước lượng.
- **Imputation BVTV Farm 126** — Fill 298 records cho tháng 01-02/2026 bằng phương pháp clone tháng 12/2025 + seasonal adjustment ratio từ Farm 157 BVTV (T01: ×0.82, T02: ×0.69).
- **ETL: VT outlier filter** — Thêm rule skip records vật tư có `thanh_tien > 100 triệu VND/record` (nguyên nhân: nhập sai đơn giá PRIAXOR, Streptomicin, Mancozeb). Tháng 10/2025 giảm từ 8.64 tỷ → 858 triệu VND.
