# UAS KPST — Tema 9: Distributed Text Processing (Master–Worker)

Python 3.9+, stdlib + `psutil` untuk metrik CPU/memori. Jalankan `pip install -r requirements.txt` di semua node.

## Arsitektur
- **Master** (`master.py`): memecah korpus menjadi task (N dokumen/task), melayani Worker via TCP, merge hasil, deteksi gagal, tulis metrik.
- **Worker** (`worker.py`): meminta task (pull), memproses dengan `multiprocessing.Pool` di semua core, kirim hasil + heartbeat.
- **Dynamic load balancing**: pull-based — worker cepat otomatis mendapat lebih banyak task. Pembanding: `--balancing static` (round-robin tetap, tanpa work stealing).
- **Fault tolerance**: heartbeat timeout / koneksi putus → task in-flight di-requeue (maks. `--max-attempts`) dengan lease per percobaan agar hasil terlambat ditolak. Recovery time dicatat.
- **Static saat worker gagal**: task yang terdampak dipindah secara eksplisit ke antrean worker sehat dan dicatat sebagai `static_failovers`; mode ini tidak diam-diam mengambil task dari antrean dinamis.
- **Beban kerja**: tokenisasi, frekuensi kata (stopword dibuang), statistik dokumen (token, kalimat, lexical diversity), bigram opsional (`--bigrams`).

## Persiapan data (Master)
    python tools/prepare_dataset.py --source gutenberg --docs 1800 --doc-kb 200 --copies 3 --out data/corpus
Sumber data: Project Gutenberg (https://www.gutenberg.org) — cantumkan di laporan. Atur `--docs/--copies` agar baseline sequential ≥ 60–120 detik.

## Menjalankan
    # 1. Sequential & Local parallel (satu komputer)
    python baseline.py --mode sequential --label seq
    python baseline.py --mode local --procs 2 --label local_2   # ulangi 4, 8, ...
    # 2. Distributed (Master dulu, lalu 9 Worker)
    python master.py --host <IP_MASTER_PRIVATE> --min-workers 9 --chunk 10 --label dist_9w
    python worker.py --master <IP_MASTER>                        # di tiap node worker
    # 3. Scalability: --min-workers 1,2,4,6,9 dengan label dist_1w, dist_2w, ...
    # 4. Load balancing: jalankan sekali --balancing static dan sekali dynamic; buat 1-2 worker lambat dengan --slow 3 (atau --cores 1)
    # 5. Fault tolerance: worker.py --crash-after 2 (crash keras), atau cabut kabel/`kill -STOP <pid>` utk uji heartbeat timeout
    MASTER_IP=10.0.0.10 MASTER_BIND=10.0.0.10 bash scripts/run_scalability.sh scripts/workers.txt dynamic   # IP private master
    python verify.py results/seq.json results/dist_dynamic_9w_r1.json   # hasil harus identik dengan baseline
    python analyze.py     # tabel Speedup/Efficiency dari results/summary.csv
Output: `results/summary.csv` dan `results/<label>.json` (ID dataset, distribusi task per worker, digest seluruh frekuensi kata/bigram, dan metrik failure/recovery). `verify.py` memeriksa seluruh digest agregat, bukan hanya daftar kata teratas. `analyze.py` mengelompokkan berdasarkan isi dataset dan opsi bigram, lalu memakai median ulangan.

## Catatan
- Batasi port 5000 ke alamat private dan subnet worker di firewall; jangan ekspos ke internet. Master menerima pesan maksimum 64 MiB dan worker memakai timeout koneksi.
- Baseline memasukkan waktu baca korpus. Waktu distributed dimulai setelah worker siap dan memasukkan pembacaan task serta transfer jaringan. Hash dataset dihitung sebelum waktu ukur. Jelaskan batas ini dalam laporan.
- Ulangi konfigurasi setidaknya tiga kali. Bandingkan median hanya untuk ID dataset dan opsi bigram yang sama.
- Efficiency = Speedup / jumlah unit (proses atau worker).
