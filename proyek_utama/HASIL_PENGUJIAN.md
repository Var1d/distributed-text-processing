# Hasil Pengujian dan Upgrade Lokal

Tanggal: 21 November 2026. Sistem uji: Windows, Python 3.11.9, `psutil` 7.2.2. Seluruh worker dijalankan di satu komputer; hasil berikut menguji correctness dan alur recovery, bukan skalabilitas jaringan.

## Upgrade yang diterapkan

- Lease ID per percobaan task; master menolak hasil dari lease atau pemilik yang sudah tidak aktif.
- Mode static menjaga antrean awal dan mencatat pengalihan task setelah worker gagal melalui `static_failovers`.
- Protokol membatasi ukuran pesan sampai 64 MiB; master memvalidasi metadata, heartbeat, dan bentuk hasil task.
- Master berhenti dengan exit code 2 bila jumlah worker minimum tidak tercapai sebelum `--startup-timeout`.
- Verifikasi membandingkan ID dataset, opsi bigram, karakter, token, kalimat, digest seluruh unigram/bigram, daftar kata teratas, dan lexical diversity.
- Dataset diberi fingerprint konten. `analyze.py` menghitung median per ID dataset, opsi bigram, mode, dan jumlah unit.
- Tokenizer menggunakan Unicode normalization NFKC dan `casefold`.
- Skrip skalabilitas memeriksa file host, parameter, dan jumlah host sebelum meluncurkan master.
- Baseline memasukkan pembacaan korpus dalam waktu ukur; output CSV baru memuat ID dataset dan task gagal.

## Korpus dan pengukuran

- `data/corpus`: sintetis deterministik, 40 dokumen, 0,32 MB, 43.463 token; dataset ID `9fdd2e58bacb326f`.
- `data/corpus_fault`: sintetis deterministik, 16 dokumen, 1,02 MB, 139.007 token; dataset ID `1ea54a72afea3df4`.
- Baseline dan master memakai korpus serta opsi bigram yang sama saat dibandingkan. Hash konten dihitung sebelum waktu ukur.
- Waktu baseline mencakup pembacaan korpus. Waktu distributed dimulai setelah worker siap dan mencakup pembacaan task serta transfer jaringan.

## Median tiga ulangan pada workload 40 dokumen

| Mode | Worker/proses | Median waktu (s) | Speedup | Efficiency |
|---|---:|---:|---:|---:|
| Sequential | 1 | 0,028 | 1,00 | 1,00 |
| Local multiprocessing | 2 | 0,227 | 0,12 | 0,06 |
| Distributed dynamic | 2 worker / 4 core | 0,125 | 0,22 | 0,11 |
| Distributed static | 2 worker / 4 core | 0,231 | 0,12 | 0,06 |

Korpus ini sengaja kecil, sehingga overhead lebih besar daripada manfaat paralelisme. Angka tersebut tidak boleh dipakai sebagai kesimpulan kinerja untuk korpus final.

## Uji correctness dan fault tolerance

- Dynamic: 3/3 run lulus verifikasi penuh terhadap baseline.
- Static: 3/3 run lulus verifikasi penuh terhadap baseline.
- Bigram aktif: baseline dan distributed lulus verifikasi digest bigram.
- Unicode: variasi `CAFÉ` dan bentuk gabungan `café` dinormalisasi dan dihitung sebagai token yang sama.
- Fault injection mode static: `w1` crash, task in-flight di-requeue, satu static failover dicatat, recovery 0,342 detik, 0 task gagal; hasil akhir cocok dengan baseline.
- Uji lease langsung: lease lama ditolak dan lease pemilik aktif diterima.
- Uji protokol: framing TCP lolos round-trip dan header yang melebihi batas ditolak.
- Uji startup: master keluar dengan kode 2 setelah batas tunggu worker habis.
- Skrip SSH: `bash -n` lulus; daftar host kosong berhenti sebelum memulai eksperimen.
- `python -m compileall` untuk modul aplikasi lulus.

Metrik CPU pada workload singkat tercatat 0,0%; belum cukup representatif untuk analisis CPU. Ulangan lebih lama pada dataset final diperlukan.

## Artefak hasil

- `results/summary.csv` — seluruh run dengan fingerprint dataset, mode, durasi, retry, failure, dan static failover.
- `results/seq_r*.json`, `results/local_2_r*.json`, `results/upgrade_dynamic_2w_r*.json`, `results/upgrade_static_2w_r*.json` — tiga run setiap mode.
- `results/upgrade_static_recovery_r1.json` dan `.log` — bukti crash/recovery.
- `results/upgrade_bigrams_seq.json`, `results/upgrade_bigrams_dist.json` — hasil verifikasi bigram.
- `results/static_crash_worker.log`, `results/static_recovery_worker.log` — log kedua worker pada fault injection.

## Pekerjaan yang masih diperlukan

1. Gunakan dataset final yang diminta pengajar dan dokumentasikan sumber/lisensi.
2. Jalankan ulangan pada node terpisah untuk 1, 2, 4, 6, dan 9 worker.
3. Jalankan fault injection dan slow-worker pada jaringan/node berbeda; ukur CPU/memori pada beban yang cukup lama.
4. Lengkapi laporan akademik dan kesimpulan berdasarkan eksperimen multi-node tersebut.
