# Laporan UAS — Distributed Text Processing System

> Spesifikasi program mengikuti prompt proyek. Ketentuan resmi mata kuliah dari PDF UJIAN AKHIR SEMESTER.pdf: kelompok 3 mahasiswa; minimal 10 node fisik (1 Master + 9 Worker); laporan BAB I–V; video MP4 maksimal 5 menit yang menunjukkan sistem pada 10 node. Pengukuran fisik dan video belum dilakukan.

## BAB I Pendahuluan

### Latar Belakang
Kumpulan dokumen teks dapat dibagi menjadi task independen. Arsitektur Master–Worker memungkinkan task diproses paralel dan hasil frekuensi kata digabungkan.

### Tujuan
Membangun DTPS untuk tokenisasi, analisis dokumen, multiprocessing di Worker, distribusi TCP, load balancing, fault tolerance dan evaluasi performa.

## BAB II Studi Pustaka

Tokenisasi membentuk token kata; frekuensi menghitung kemunculannya. Multiprocessing menjalankan pekerjaan pada proses terpisah. Dalam Master–Worker, Master membagi pekerjaan dan Worker meminta task melalui TCP berframing JSON. Heartbeat memantau Worker; retry dan requeue memulihkan task. Speedup = T_sequential / T_parallel; efficiency = speedup / P; throughput = unit / waktu.

## BAB III Metodologi

Kelompok terdiri dari 3 mahasiswa sesuai PDF. Topologi target adalah satu Master dan sembilan Worker pada sepuluh node melalui kabel atau Wi-Fi. Saat uji fisik, catat IP, port, OS, jumlah core, RAM, jaringan dan konfigurasi proses tiap Worker.

Dokumen UTF-8 dibagi menjadi task, dianalisis dan diagregasi. Eksperimen di lingkungan ini menggunakan file sampel berukuran 733 byte, 93 kata, satu dokumen. Benchmark skala memakai chunk 10 kata untuk menghasilkan 10 task independen. Semua Worker pada eksperimen ini adalah proses pada satu host; hasilnya simulasi lokal, bukan uji 10 node fisik.

P pada local parallel adalah dua proses. P pada distributed = jumlah Worker × processes_per_worker; pada uji ini processes_per_worker=1. CPU adalah sampel utilisasi host selama workload; RSS adalah memori puncak proses benchmark, bukan agregat Worker. CPU sequential tidak tersampel karena durasinya terlalu singkat.

## BAB IV Hasil dan Pembahasan

Hasil berikut berasal dari pengukuran aktual pada 20 November 2026. Dataset sangat kecil sehingga tabel membuktikan integrasi alur, bukan kinerja corpus besar.

### Sequential dan local multiprocessing

| Eksperimen | Waktu (detik) | Speedup | Efficiency | CPU host (%) | RSS puncak (MiB) |
|---|---:|---:|---:|---:|---:|
| Sequential | 0.000334 | 1.000000 | 1.000000 | tidak tersampel | 21.91 |
| Local multiprocessing (P=2) | 0.152101 | 0.002196 | 0.001098 | 11.60 | 22.60 |

Biaya membuat process pool jauh melebihi pekerjaan pada sampel sekecil ini. Angka ini tidak digunakan untuk menyimpulkan performa pada dokumen besar.

### Scalability TCP (simulasi satu host, 10 task)

| Worker | Worker yang mendapat task | Waktu (detik) | Speedup | Efficiency | CPU (%) | RSS puncak (MiB) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 0.875039 | 0.001168 | 0.001168 | 12.26 | 18.56 |
| 2 | 2 | 1.328476 | 0.000064 | 0.000032 | 15.61 | 18.61 |
| 4 | 4 | 1.309962 | 0.000067 | 0.000017 | 13.25 | 18.63 |
| 6 | 6 | 1.266751 | 0.000081 | 0.000014 | 15.06 | 18.64 |
| 9 | 9 | 1.257255 | 0.000175 | 0.000019 | 24.84 | 18.65 |

Semua Worker yang diminta menerima sekurangnya satu task pada run ini. Sepuluh task dari satu dokumen kecil tetap terlalu sedikit untuk mengukur scaling yang stabil. Seluruh pengujian adalah proses lokal.

### Static vs dynamic (simulasi lokal, 2 Worker, 10 task)

| Strategi | Waktu (detik) | Worker yang dipakai | Pembagian task |
|---|---:|---:|---|
| Static round-robin | 1.310044 | 2 | 5 / 5 |
| Dynamic load-aware | 1.320152 | 2 | 5 / 5 |

Perbedaan satu run ini kecil dan dipengaruhi noise sistem. Tidak cukup bukti untuk menyatakan satu strategi lebih cepat.

### Uji tiga Worker dan shutdown

Uji integrasi terpisah menjalankan tiga Worker dengan 10 task. Task terbagi 4 / 3 / 3; Master mengirim sinyal SHUTDOWN, ketiga Worker keluar normal, dan tidak terjadi loop reconnect. Ini juga simulasi proses lokal.

### Fault tolerance

Simulasi state antrean menghasilkan status REQUEUED, attempt berubah menjadi 2, dan transisi state terukur sekitar 0.0000043 detik. Ini hanya mengukur perubahan state lokal, bukan waktu deteksi heartbeat atau recovery jaringan nyata.

JSON mentah tersimpan di `results/raw/`, metrik sequential/local di `results/metrics/`, grafik di `results/charts/`, dan hasil simulasi fault di `results/raw/fault-recovery.json`.

**Belum diuji:** corpus besar, jaringan antar-komputer, dan satu Master bersama sembilan Worker fisik. Hasil fisik dan analisisnya harus ditambahkan setelah eksperimen nyata; simulasi lokal tidak dapat menggantikannya.

## BAB V Kesimpulan

Implementasi menjalankan pemrosesan sequential, local multiprocessing, distribusi TCP, scheduler static/dynamic dan retry task. Uji multi-Worker membuktikan pembagian task serta shutdown graceful. Sampel kecil belum memadai untuk klaim performa atau scalability.

### Saran
Gunakan corpus besar dengan beban task bervariasi, ulangi setiap eksperimen, uji pada 10 node fisik, simulasi Worker benar-benar mati, lalu rekam waktu deteksi/recovery dan utilisasi tiap node.

## Pembagian tugas

Tiga mahasiswa: (1) Master, protokol dan antrean; (2) Worker, multiprocessing dan pemulihan; (3) benchmark, visualisasi, eksperimen jaringan dan laporan. Sesuaikan dengan kontribusi aktual.

## Lampiran demonstrasi

PDF UAS meminta video MP4 maksimal lima menit yang membuktikan sistem pada sepuluh node fisik. Rekam topologi, konfigurasi, Master, sembilan Worker, distribusi dan agregasi task, lalu satu kegagalan dan pemulihan. Video ini masih perlu direkam saat uji fisik.

## Sumber dan aset pendukung

- Ketentuan mata kuliah dan tema: PDF UJIAN AKHIR SEMESTER.pdf di workspace.
- Rumus speedup, efficiency dan throughput: prompt spesifikasi proyek dari pengguna.
- Dataset contoh: `data/sample/sample.txt`, dibuat khusus untuk demo, bukan dataset eksternal.
- Dataset sintetis: dibuat oleh `scripts/generate_dataset.py` dari daftar kata di source code.
- Hasil benchmark dan grafik: diukur/dihasilkan langsung oleh eksperimen dan disimpan di `results/`.
