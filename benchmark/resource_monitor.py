import threading, time, psutil, os

class ResourceMonitor:
    """Sampling selama workload; CPU adalah rata-rata utilisasi host, RAM RSS proses launcher."""
    def __init__(self, interval=.05):
        self.interval=interval; self.stop_event=threading.Event(); self.samples=[]; self.thread=None
        self.process=psutil.Process(os.getpid()); self.peak_rss_mb=0.0
    def _sample(self):
        while not self.stop_event.wait(self.interval):
            self.samples.append(psutil.cpu_percent(interval=None))
            try: self.peak_rss_mb=max(self.peak_rss_mb,self.process.memory_info().rss/(1024*1024))
            except psutil.Error: pass
    def __enter__(self):
        psutil.cpu_percent(interval=None)
        self.peak_rss_mb=self.process.memory_info().rss/(1024*1024)
        self.thread=threading.Thread(target=self._sample,daemon=True); self.thread.start(); return self
    def __exit__(self,*_):
        self.stop_event.set(); self.thread.join()
    @property
    def cpu_percent(self):
        return sum(self.samples)/len(self.samples) if self.samples else None
