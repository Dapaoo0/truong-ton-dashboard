# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Added ETL sync for Dinh Muc

## 2026-04-18
### Fixed
- **ETL: Override doi_name cho team sheets** — Khi đọc từ GSheet của đội (BVTV, Cơ Giới, etc.), force `doi_id` theo tên đội thay vì cột "Đội Thực Hiện" trong GSheet. Fix lỗi BVTV data bị gán nhầm cho NT1/NT2.

### Added
- **Cột `is_estimated`** — Thêm cột boolean vào `fact_nhat_ky_san_xuat` để đánh dấu dữ liệu ước lượng.
- **Imputation BVTV Farm 126** — Fill 298 records cho tháng 01-02/2026 bằng phương pháp clone tháng 12/2025 + seasonal adjustment ratio từ Farm 157 BVTV (T01: ×0.82, T02: ×0.69).
- **ETL: VT outlier filter** — Thêm rule skip records vật tư có `thanh_tien > 100 triệu VND/record` (nguyên nhân: nhập sai đơn giá PRIAXOR, Streptomicin, Mancozeb). Tháng 10/2025 giảm từ 8.64 tỷ → 858 triệu VND.
