# Status Proyek — Tahap Kerja 75% (Validasi Lokal)

Status sementara pada salinan kerja; bukan klaim bahwa eksperimen akhir UAS sudah tuntas. Detail dan bukti ada di `HASIL_PENGUJIAN.md`.

| Komponen | Status |
|---|---|
| Master–Worker, protokol, pemrosesan teks | Upgrade lease, validasi pesan, batas ukuran, dan Unicode diterapkan; pemeriksaan lokal lulus |
| Dynamic/static load balancing | Tiga ulangan tiap mode; hasil cocok dengan baseline |
| Fault tolerance | Crash pada mode static diuji; task pulih, satu failover dicatat, nol task gagal |
| Validasi output | Digest penuh unigram/bigram dan metadata workload dibandingkan |
| Analisis benchmark | Fingerprint dataset dan median ulangan digunakan |
| Pengukuran CPU/memori | `psutil` terpasang lokal; workload kecil belum memberi sampel CPU representatif |
| Dataset final | Belum; yang dipakai korpus sintetis untuk uji lokal |
| Node fisik terpisah dan ulangan skala 1/2/4/6/9 | Belum |
| BAB IV, kesimpulan, video/bukti | Belum |

## Batas tahap ini

Worker berada di satu komputer dan korpusnya kecil. Hasil mengonfirmasi correctness, protokol, startup timeout, serta recovery lokal, bukan performa multi-node. Tahap final perlu dataset sesuai tugas, host worker yang terkonfigurasi, dan ulangan pada node terpisah.
