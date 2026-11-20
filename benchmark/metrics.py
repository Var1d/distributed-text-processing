"""Rumus metrik eksperimen DTPS; P adalah jumlah proses komputasi yang benar-benar dipakai."""
def calculate_metrics(elapsed_seconds, units, sequential_seconds=None, parallelism=1,
                      cpu_percent=None, memory_mb=None, recovery_seconds=None):
    if elapsed_seconds <= 0 or parallelism < 1 or units < 0:
        raise ValueError("Waktu harus positif, parallelism minimal satu, unit nonnegatif.")
    speedup = sequential_seconds / elapsed_seconds if sequential_seconds is not None and elapsed_seconds else None
    return {
        "execution_time_seconds": elapsed_seconds,
        "speedup": speedup,
        "efficiency": speedup / parallelism if speedup is not None else None,
        "parallelism": parallelism,
        "throughput_units_per_second": units / elapsed_seconds,
        "cpu_utilization_percent": cpu_percent,
        "memory_rss_peak_mb": memory_mb,
        "recovery_time_seconds": recovery_seconds,
    }
