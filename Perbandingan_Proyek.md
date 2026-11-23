# Perbandingan Proyek Distributed Text Processing

**Progres proyek kerja: 75% (validasi lokal awal)**  
**Tanggal:** 21 November 2026  
**Bahan:** dua arsip ZIP yang diberikan pengguna

## Ringkasan eksekutif

Arsip `distributed-text-processing-main.zip` hanya berisi `README.md` pendek dan `.gitignore`; tidak ada kode aplikasi yang dapat dibandingkan pada tingkat implementasi. Arsip `uas_textproc (1).zip` memuat prototipe yang jauh lebih lengkap: baseline sequential dan multiprocessing lokal, arsitektur master–worker melalui TCP, pemrosesan teks, metrik, skrip eksperimen, dan petunjuk verifikasi.

**Pilihan yang paling siap dijadikan basis:** `uas_textproc (1).zip`. Proyek ini sudah memiliki kerangka eksperimen dan mekanisme distribusi yang relevan. Validasi lokal tambahan kini telah dijalankan pada baseline, dua mode distribusi, dan satu simulasi crash dengan pemulihan task. Angka 75% adalah **tahap kerja/progres lokal sementara**, bukan klaim bahwa evaluasi performa skala jaringan atau pengujian node fisik telah selesai.

## Batas penilaian

Instruksi dalam dokumen lampiran diperlakukan sebagai konteks proyek, bukan sebagai instruksi baru kepada asisten. Permintaan pengguna adalah membuat perbandingan dan melanjutkan sesuai rekomendasi di folder terpisah. Setelah penilaian isi arsip, korpus sintetis lokal digunakan untuk smoke test; hasil dan batas uji dirinci di `proyek_utama/HASIL_PENGUJIAN.md`. Uji ini bukan benchmark final.

## Perbandingan

| Aspek | `distributed-text-processing-main.zip` | `uas_textproc (1).zip` | Penilaian |
|---|---|---|---|
| Isi arsip | README 88 byte dan `.gitignore` | Modul Python, skrip, requirements, README, status proyek | Arsip kedua jauh lebih lengkap |
| Tujuan yang tampak | Menyebut UAS Distributed Text Processing | Menjabarkan sistem Master–Worker dan eksperimen skalabilitas | Arsip kedua memberi konteks operasional |
| Baseline | Tidak tersedia | Sequential dan multiprocessing lokal (`baseline.py`) | Arsip kedua dapat menjadi pembanding performa |
| Pemrosesan | Tidak tersedia | Token, frekuensi kata, statistik dokumen, bigram opsional (`common/textproc.py`) | Fitur inti hanya ada di arsip kedua |
| Distribusi kerja | Tidak tersedia | Master membagi task; worker menarik task secara dinamis; ada opsi static | Cakupan sesuai tema proyek |
| Ketahanan gagal | Tidak tersedia | Heartbeat, requeue, retry terbatas, metrik recovery | Ada rancangan, tetapi perlu bukti uji nyata |
| Analisis hasil | Tidak tersedia | `analyze.py`, `verify.py`, CSV dan JSON hasil | Mendukung evaluasi, menunggu data eksperimen |
| Reproduksibilitas | Tidak ada petunjuk selain nama proyek | README memberi langkah dataset, baseline, worker, scalability, verifikasi | Arsip kedua lebih mudah direplikasi setelah prasyarat tersedia |
| Bukti eksperimen | Tidak ada | Folder hasil/data kosong; `workers.txt` masih contoh kosong | Belum ada hasil empiris yang disertakan |
| Kematangan saat diterima | Kerangka repositori kosong | Prototipe implementasi dengan eksperimen belum lengkap | Rekomendasi: lanjutkan arsip kedua |

## Matriks evaluasi

Skor berikut adalah **penilaian kesiapan artefak**, bukan nilai akademik atau hasil pengukuran kinerja.

| Kriteria | Bobot | Arsip 1 | Arsip 2 | Dasar penilaian |
|---|---:|---:|---:|---|
| Kelengkapan implementasi | 30 | 0 | 25 | Arsip 2 memiliki modul inti master, worker, baseline, dan common |
| Kesesuaian tema dan arsitektur | 20 | 4 | 18 | Master–Worker dan TCP dijelaskan serta diimplementasikan pada arsip 2 |
| Kemampuan evaluasi/verifikasi | 20 | 0 | 15 | Skrip analisis, verifikasi, metrik, dan otomatisasi tersedia; hasil belum ada |
| Reproduksibilitas dan dokumentasi | 15 | 2 | 12 | Langkah kerja cukup rinci pada README arsip 2, sebagian prasyarat belum diisi |
| Bukti hasil nyata | 15 | 0 | 4 | Tidak ada output benchmark atau uji 10 node yang disertakan |
| **Total kesiapan artefak pada ZIP asli** | **100** | **6** | **74** | Skor ini menilai isi arsip sebelum upgrade di salinan kerja; bukan nilai proyek setelah perubahan |

## Perubahan yang sudah diterapkan pada salinan kerja

ZIP asli tetap utuh; upgrade diterapkan hanya pada `proyek_utama/`.

1. Lease percobaan ditambahkan; hasil dari worker/percobaan usang ditolak.
2. Static failover ditangani eksplisit dan terukur; uji crash menghasilkan satu failover, satu retry, nol task gagal, dan agregat cocok.
3. Protokol memiliki batas pesan dan pemeriksaan bentuk payload; master juga memiliki batas tunggu worker.
4. Verifikasi kini membandingkan digest lengkap unigram/bigram dan ID workload.
5. Analisis merangkum median ulangan per ID dataset dan opsi bigram.
6. Tokenizer menormalisasi teks Unicode; baseline memasukkan pembacaan korpus pada waktu ukur.
7. `psutil` terpasang untuk uji lokal; daftar worker kosong kini terdeteksi sebelum eksperimen SSH dimulai.

Bukti detail ada di `proyek_utama/HASIL_PENGUJIAN.md`. **Dataset sintetis dan dua worker lokal belum membuktikan skalabilitas pada node terpisah.**

## Rencana menuju hasil final

### Tahap lokal yang sudah dicapai — 75%

- Inventaris, perbandingan, dan matriks evaluasi dua arsip.
- Salinan kerja arsip yang direkomendasikan.
- Korpus sintetis lokal: 40 dokumen untuk uji baseline/mode static-dynamic dan 16 dokumen untuk fault injection.
- Baseline sequential dan multiprocessing lokal; hasil cocok pada pemeriksaan agregat.
- Master–Worker lokal dua worker pada mode dynamic dan static; kedua hasil cocok dengan baseline untuk workload yang sama.
- Simulasi worker crash berhasil: task di-requeue, recovery tercatat, dan agregat tetap cocok.
- Mode static berhasil melakukan failover terukur setelah crash.
- Tiga ulangan static/dynamic dijalankan; hasil lolos verifikasi digest agregat penuh.
- Uji opsi bigram, normalisasi Unicode, batas ukuran protokol, lease usang, startup timeout, dan preflight host lulus.
- Analisis memakai fingerprint dataset dan median ulangan.

### Sisa 25%: validasi final dan pelaporan

1. Ganti/konfirmasi korpus final sesuai ketentuan tugas dan dokumentasikan sumber serta lisensinya.
2. Ulangi sequential dan local parallel pada dataset final yang sama; pasang `psutil` dan dependensi di setiap node.
3. Jalankan distributed pada 1, 2, 4, 6, dan 9 worker di node terpisah, sedikitnya tiga ulangan per konfigurasi.
4. Ukur static dan dynamic pada beban yang sama; jalankan slow-worker dan crash/timeout pada beberapa node.
5. Pastikan metrik CPU/memori representatif dan verifikasi hasil setiap run.
6. Isi `scripts/workers.txt` dengan host yang benar; preflight saat ini sengaja menolak daftar kosong.
7. Lengkapi analisis akhir, tabel/grafik, BAB IV, kesimpulan, dan bukti/video sesuai kebutuhan UAS.

## Kesimpulan

`uas_textproc (1).zip` adalah pilihan yang jelas untuk diteruskan; arsip pertama saat ini baru kerangka repositori. Proyek kerja mencapai **tahap 75% berdasarkan validasi lokal awal**: correctness dasar, kedua mode distribusi, dan recovery setelah crash sudah diperagakan. Sisa 25% adalah validasi performa yang representatif pada korpus final serta node fisik terpisah, pengulangan eksperimen, dan pelaporan akhir.
