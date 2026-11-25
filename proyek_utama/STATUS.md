# Status Proyek UAS

Status ini membedakan fitur yang tersedia dari eksperimen yang masih harus dilakukan pada node fisik. Kode dan panduan sudah disiapkan untuk matriks pengujian UAS; hasil akhir multi-node belum boleh diklaim sebelum benar-benar dijalankan.

| Kebutuhan | Status artefak | Bukti/pekerjaan berikutnya |
|---|---|---|
| Task decomposition | Diimplementasikan | Master membagi file menjadi task berdasarkan `--chunk` |
| Parallel processing | Diimplementasikan | Worker memakai `multiprocessing.Pool`; ukur konfigurasi core pada perangkat |
| Distributed processing | Diimplementasikan | TCP Master–Worker; jalankan pada jaringan dan perangkat terpisah |
| Dynamic load balancing | Diimplementasikan | Bandingkan dynamic dengan static pada workload sama |
| Fault tolerance | Diimplementasikan | Heartbeat, timeout, retry/requeue, dan lease; rekam run crash nyata |
| Sequential dan local parallel | Tersedia | Ulangi pada dataset final yang sama dengan eksperimen distributed |
| Scalability 1/2/4/6/9 worker | Belum dibuktikan multi-node | Jalankan tepat sejumlah worker fisik, tiga ulangan tiap konfigurasi |
| Dataset benchmark | Generator deterministik tersedia | Gunakan ukuran cukup besar; cantumkan asal/sifat dataset di laporan |
| CPU/memory di Linux/Android | Fallback `/proc` ditambahkan | Pastikan hasil CSV tidak kosong pada perangkat demonstrasi |
| Laporan dan video | Belum selesai | Analisis hasil aktual; video demonstrasi 10 node fisik maksimal 5 menit |

Jalankan langkah dan perintah pada `README.md`. Uji kecil 3 dokumen hanya untuk smoke test dan tidak dipakai sebagai bukti performa.
