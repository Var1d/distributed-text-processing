# Distributed Text Processing — Paket Proyek UAS

- `proyek_utama/`: source code tema Distributed Text Processing dan panduan eksperimen sesuai ketentuan UAS.
- `proyek_utama/README.md`: pembuatan dataset, perintah baseline/distributed, scalability, balancing, fault tolerance, dan interpretasi metrik.
- `proyek_utama/STATUS.md`: pemetaan kebutuhan tugas ke fitur dan pengujian yang belum dilakukan.
- `proyek_utama/HASIL_PENGUJIAN.md`: catatan eksperimen lokal terdahulu; bukan klaim hasil uji 10 node.
- `Perbandingan_Proyek.md` dan `Matriks_Evaluasi.csv`: bahan evaluasi proyek.

Pengujian dengan beberapa worker di satu komputer hanya membuktikan alur fungsi. Pemenuhan ketentuan jumlah node dan kesimpulan performa memerlukan pengukuran pada 1 master + 9 worker fisik.
