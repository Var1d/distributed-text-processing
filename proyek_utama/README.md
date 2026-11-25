# UAS KPST — Tema 9: Distributed Text Processing (Master–Worker)

Python 3.9+. Aplikasi menghitung token/frekuensi kata, statistik dokumen, dan bigram opsional.

## Arsitektur dan fitur

- **Master** memecah korpus menjadi task, membagikannya melalui TCP, menggabungkan hasil, memantau worker, dan menyimpan metrik.
- **Worker** menarik task dan memproses dokumen menggunakan `multiprocessing.Pool` pada beberapa core.
- **Baseline** membaca korpus per batch agar pemakaian RAM tidak tumbuh sebesar seluruh korpus sekaligus; pemakaian core default dibatasi agar perangkat tidak membuat proses berlebihan.
- **Dynamic balancing** memakai antrean pull-based; worker yang selesai lebih cepat dapat mengambil task berikutnya. Mode `static` membandingkan pembagian round-robin.
- **Fault tolerance** memakai heartbeat, timeout, retry/requeue, batas jumlah percobaan, dan lease agar hasil task lama ditolak.
- Worker mencoba koneksi awal hingga 10 kali dengan jeda bertambah jika master belum siap; opsi dapat diatur dengan `--connect-retries` dan `--retry-delay`.
- Hasil JSON mencakup digest agregat untuk memverifikasi kesamaan dengan baseline. CSV mencatat durasi, throughput, penggunaan CPU/memori, recovery, retry, dan kegagalan.

## Siapkan dataset

Untuk uji awal yang dapat diulang tanpa internet, buat korpus sintetis di folder baru:

```bash
python tools/prepare_dataset.py --source synthetic --docs 180 --doc-kb 64 --seed 42 --out data/corpus_uas
```

Korpus ini sekitar 11 MiB dan menghasilkan cukup task untuk memeriksa pembagian kerja. Untuk benchmark akhir, perbesar korpus sampai waktu sequential sekitar 60–120 detik bila kapasitas perangkat dan penyimpanan memungkinkan. Gunakan dataset identik pada semua mode. Jelaskan bahwa dataset sintetis dibuat oleh proyek; jangan menyebutnya data Project Gutenberg.

Alternatif sumber publik:

```bash
python tools/prepare_dataset.py --source gutenberg --docs 1800 --doc-kb 200 --out data/corpus_uas
```

Cantumkan Project Gutenberg dan periksa ketentuan penggunaan setiap buku. Jika unduhan gagal, gunakan korpus lokal yang sumber dan izinnya dapat dijelaskan. Folder output harus kosong atau baru; skrip menolak folder yang sudah berisi `.txt` agar data lama tidak tercampur.

## Jalankan eksperimen UAS

Jalankan perintah dari folder `proyek_utama`. Pada master, pilih IP privat dengan `ipconfig` (Windows) atau `ip addr` (Linux). Pastikan TCP port 5000 dapat diakses hanya pada jaringan privat yang digunakan.

```bash
# Sequential baseline dan local multiprocessing; gunakan korpus dan opsi yang sama
python baseline.py --data data/corpus_uas --mode sequential --label seq_r1
python baseline.py --data data/corpus_uas --mode local --procs 2 --label local_2_r1

# Master menunggu 9 worker; jalankan di komputer master
python master.py --data data/corpus_uas --host 0.0.0.0 --min-workers 9 --chunk 10 --label dist_9w_r1

# Jalankan pada tiap komputer worker (total 9 node fisik)
python worker.py --master IP_MASTER --cores 2

# Setelah run selesai, verifikasi hasil dan ringkas metrik
python verify.py results/seq_r1.json results/dist_9w_r1.json
python analyze.py
```

Untuk uji scalability, jalankan ulang distributed dengan tepat `N` worker untuk `N` = 1, 2, 4, 6, dan 9. Ulangi setiap konfigurasi setidaknya tiga kali dengan label unik (`r1`, `r2`, `r3`). Untuk membandingkan load balancing, gunakan worker dan dataset yang sama pada mode dynamic dan static, misalnya tambahkan `--balancing static` pada master. Untuk fault tolerance, jalankan salah satu worker dengan `--crash-after 2`, dan biarkan worker lain tetap aktif untuk mengambil task yang di-requeue. Bila bigram diaktifkan, tambahkan `--bigrams` pada baseline dan master.

Worker mencoba ulang koneksi awal bila master belum siap. Jika seluruh percobaan gagal, pesan akhir mengarahkan pemeriksaan IP, jaringan, status master, dan firewall. Retry ini tidak dapat melewati isolasi klien pada Wi-Fi.

Ketentuan UAS meminta minimal **10 node fisik: 1 master dan 9 worker**. Dua worker pada satu komputer hanya menguji fungsi sistem, bukan memenuhi jumlah node. Android/Termux dapat digunakan sebagai salah satu worker. Tanpa `psutil`, worker mencoba membaca CPU/memori dari `/proc`; bila OS tidak menyediakan nilainya, CSV/analisis akan menampilkan kolom kosong. Hasil pengukuran tetap perlu dibahas beserta keterbatasannya dalam laporan.

## Interpretasi metrik

- `execution time`: waktu pemrosesan; bandingkan pada dataset yang sama.
- `speedup`: waktu sequential dibagi waktu konfigurasi.
- `efficiency`: speedup dibagi jumlah unit (proses atau worker).
- `throughput`: dokumen atau MiB per detik.
- `CPU/memory`: rata-rata sampel heartbeat yang diterima master.
- `recovery time`, `retries`, `failed tasks`: dampak simulasi kegagalan worker.
- Kolom `units` pada hasil distributed adalah jumlah worker yang benar-benar memproses task pada run itu.

Jelaskan bahwa overhead jaringan dan startup dapat membuat konfigurasi paralel lebih lambat pada korpus kecil. Jangan menyimpulkan scalability dari run tiga dokumen; gunakan workload final yang lebih besar dan ulangan yang sebanding.
