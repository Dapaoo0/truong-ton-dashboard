import db
print(db.query('SELECT nk.so_cong, nk.klcv, nk.dinh_muc, nk.ti_le_display FROM fact_nhat_ky_san_xuat nk WHERE nk.dinh_muc > 0 LIMIT 5'))
