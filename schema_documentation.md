# Tài Liệu Schema Supabase — Farm Dashboard

Database Supabase (`uavsanujwcmwtsucrjlo`) gồm **2 schema độc lập** phục vụ 2 ứng dụng khác nhau, được liên kết qua `base_lots.dim_lo_id`.

---

## PHẦN 1: HỆ THỐNG CHI PHÍ (App Dashboard)

Schema chuẩn hóa, FK ràng buộc chặt. Dữ liệu được bơm từ Google Sheets qua Python ETL hàng ngày.

### Bảng Dimension

| Bảng | Rows | PK | Mô tả |
|---|---|---|---|
| `dim_farm` | 3 | `farm_id` | 3 trang trại: Farm 126, Farm 157, Farm 195 |
| `dim_lo` | 90 | `lo_id` | Lô đất vật lý. `lo_type`: Lô thực / Lô ảo / Farm / Liên Farm |
| `dim_doi` | 42 | `doi_id` | Đội. Unique constraint `(farm_id, doi_code)` |
| `dim_cong_viec` | 552 | `cong_viec_id` | Mã công việc. Unique `ma_cv` |
| `dim_vat_tu` | 546 | `vat_tu_id` | Vật tư xuất kho |
| `dim_lo_doi` | 62 | `lo_doi_id` | Bridge table lô ↔ đội (many-to-many) |

### Bảng Fact

| Bảng | Rows | Mô tả |
|---|---|---|
| `fact_nhat_ky_san_xuat` | 17,317 | Nhật ký công: `so_cong`, `klcv`, `don_gia`, `thanh_tien`. 0% null trên tất cả FK |
| `fact_vat_tu` | 10,992 | Nhật ký vật tư: `so_luong`, `don_gia`, `thanh_tien`. 430 rows (~4%) `cong_viec_id` là NULL (do thiếu mã CV từ nguồn) |
| `fact_dtbd` | 2 | Đầu tư ban đầu / khấu hao (Farm 195 only) |
| `fact_195_tong` | 247 | OBT pre-computed cho Farm 195 Dashboard. Truncate+reload mỗi lần ETL |

### Log / Audit

| Bảng | Rows | Mô tả |
|---|---|---|
| `log_outliers_thanh_tien` | 52 | Ghi lại các `thanh_tien` bất thường bị điều chỉnh |

### View

| View | Mô tả |
|---|---|
| `v_chi_phi_chi_tiet` | OBT JOIN sẵn cho Streamlit đọc. Dùng `SECURITY DEFINER` |

---

## PHẦN 2: HỆ THỐNG NÔNG HỌC (App Nhập Tình Trạng Vườn)

Schema linh hoạt, dùng text (`farm`, `lot_id`) thay vì integer FK. Hiện chỉ dùng cho **Farm 157**, chỉ các lô trồng mới gần đây.

### Master Data

| Bảng | Rows | Mô tả |
|---|---|---|
| `base_lots` | 23 | Master lô trồng. `lot_id` = `{lo}_{ddmmyyyy}` (VD: `3A_11102025`). **`dim_lo_id` là cầu nối sang schema Chi phí.** |
| `seasons` | 24 | Mùa vụ. Cột `lo` lưu `lot_id` (không phải tên lô đơn giản) |

### Lifecycle Logs

| Bảng | Rows | Mô tả |
|---|---|---|
| `stage_logs` | 24 | Giai đoạn cây: trồng, chích bắp, buộc bao. `mau_day` để tracking batch |
| `harvest_logs` | 6 | Thu hoạch: `so_luong`, `mau_day`, `hinh_thuc_thu_hoach` |
| `destruction_logs` | 2 | Tiêu hủy cây: `ly_do`, `giai_doan`, `mau_day` |
| `bsr_logs` | 0 | Chỉ số BSR — chưa có dữ liệu |
| `tree_inventory_logs` | 0 | Kiểm đếm cây — chưa có dữ liệu |

### Biometrics Logs

| Bảng | Rows | Mô tả |
|---|---|---|
| `size_measure_logs` | 7 | Đo caliper trái định kỳ |
| `soil_ph_logs` | 3 | Đo pH đất |
| `fusarium_logs` | 0 | Báo cáo nấm Fusarium. RLS đã bật (policy: Allow all) |

### Tiện ích

| Bảng | Rows | Mô tả |
|---|---|---|
| `access_logs` | 117 | Log lượt truy cập App theo farm/team |

---

## LIÊN KẾT GIỮA 2 SCHEMA

### Điểm nối: `base_lots.dim_lo_id → dim_lo.lo_id`

```
dim_farm ──── dim_lo ◄──── base_lots ──── stage_logs
                               │           harvest_logs
              fact_nhat_ky     │           seasons
              fact_vat_tu  ────┘ (qua dim_lo_id)
```

- `base_lots.lo` = tên lô đơn giản (`3A`) — khớp với `dim_lo.lo_code`
- `base_lots.lot_id` = mã lô unique (`3A_11102025`) — dùng trong toàn bộ bảng App
- **Quan hệ 1:N:** 1 lô đất có thể có nhiều đợt trồng (nhiều `base_lots`)
- **Trigger `trg_base_lots_auto_map`:** Khi App INSERT lô mới, tự động điền `dim_lo_id`

### Lưu ý

- Chỉ Farm 157 dùng App. Farm 126 và Farm 195 chưa có dữ liệu App.
- 23 lô Farm 157 trong `dim_lo` (lô cũ) không có entry trong `base_lots` — expected.
- `seasons.lo` lưu `lot_id` → cần JOIN qua `base_lots` khi link sang `dim_lo`.

---

## INDEXES

### fact_nhat_ky_san_xuat
`idx_nk_farm`, `idx_nk_farm_ngay`, `idx_nk_lo`, `idx_nk_doi`, `idx_nk_cv`, `idx_nk_ngay`, `uq_nk_natural_key` (unique dedup)

### fact_vat_tu
`idx_vt_farm`, `idx_vt_farm_ngay`, `idx_vt_lo`, `idx_vt_cv`, `idx_vt_vat_tu`, `idx_vt_ngay`, `uq_vt_natural_key` (unique dedup)

### fact_195_tong
`idx_195_tong_ngay`, `idx_195_tong_loai_du_lieu`, `idx_195_tong_loai_chi_phi`, `idx_195_tong_hang_muc_cong`, `idx_195_tong_farm_id`

### App tables
`idx_base_lots_dim_lo_id`, `idx_stage_logs_farm_lot`, `idx_harvest_logs_farm_lot`, `idx_destruction_logs_farm_lot`, `idx_bsr_logs_farm_lot`

---

## CHANGELOG

| Ngày | Thay đổi |
|---|---|
| 2026-03-26 | Chuẩn hóa tên đội `dim_doi`: `Thu Hoạch`→`Đội Thu Hoạch`, `Cơ Giới`→`Đội Cơ Giới`, `Điện Nước`→`Đội Điện Nước` (cả Farm 126 & 157) |
| 2026-03-26 | Merge entries trùng `BVTV`→`Đội BVTV` (164 records), `Đội Điên/Điện Nước`→`Đội Điện Nước` (55 records), `XDG`→`XĐG` (1 record). Xóa 10 dim_doi entries rỗng |
| 2026-03-26 | Thêm `dim_lo_id` (nullable FK) vào `base_lots`. 23/23 lô active mapped ✅ |
| 2026-03-26 | Tạo trigger `trg_base_lots_auto_map` |
| 2026-03-26 | Tạo 6 indexes thiếu trên FK columns của App tables |
| 2026-03-26 | Xóa 8 indexes không dùng (`dim_doi`, `dim_vat_tu`, `fact_dtbd`, `fact_195_tong`) |
| 2026-03-26 | Fix `search_path` cho `fn_auto_map_dim_lo` và `update_lot_inventory` |