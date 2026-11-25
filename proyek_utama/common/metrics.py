import csv
import hashlib
import os

FIELDS = ["label", "dataset_id", "bigrams", "mode", "units", "total_cores", "docs", "mb", "exec_time_s",
          "throughput_docs_s", "throughput_mb_s", "retries", "avg_recovery_s",
          "avg_cpu_pct", "avg_mem_pct", "imbalance", "failed_tasks", "static_failovers"]


class ResourceSampler:
    """Sample host CPU and memory using psutil or Linux/Android procfs."""

    def __init__(self):
        self._prev_cpu = None
        self._psutil = None
        try:
            import psutil
            self._psutil = psutil
            psutil.cpu_percent(None)  # prime psutil's interval counter
        except ImportError:
            pass

    def sample(self):
        if self._psutil is not None:
            return (self._psutil.cpu_percent(None), self._psutil.virtual_memory().percent)
        cpu = self._linux_cpu_percent()
        mem = self._linux_memory_percent()
        return cpu, mem

    def _linux_cpu_percent(self):
        try:
            with open("/proc/stat", encoding="ascii") as f:
                values = [int(x) for x in f.readline().split()[1:]]
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            # guest/guest_nice are already included in user/nice on Linux.
            total = sum(values[:8])
            current = (total, idle)
            previous, self._prev_cpu = self._prev_cpu, current
            if previous is None or total <= previous[0]:
                return None
            total_delta = total - previous[0]
            idle_delta = idle - previous[1]
            return max(0.0, min(100.0, 100.0 * (total_delta - idle_delta) / total_delta))
        except (OSError, ValueError, IndexError):
            return None

    @staticmethod
    def _linux_memory_percent():
        try:
            values = {}
            with open("/proc/meminfo", encoding="ascii") as f:
                for line in f:
                    key, value = line.split(":", 1)
                    if key in ("MemTotal", "MemAvailable"):
                        values[key] = int(value.strip().split()[0])
            total, available = values["MemTotal"], values["MemAvailable"]
            return 100.0 * (total - available) / total if total else None
        except (OSError, ValueError, KeyError, IndexError):
            return None


def dataset_id(files):
    """Stable content fingerprint; calculate outside the timed processing interval."""
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(os.path.basename(path).encode("utf-8"))
        digest.update(b"\0")
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()[:16]

def append_summary(row, path="results/summary.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
