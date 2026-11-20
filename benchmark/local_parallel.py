from concurrent.futures import ProcessPoolExecutor
from time import perf_counter
from processing.document_analysis import analyze_document


def _analyze(item):
    return analyze_document(*item)


def run_local_parallel(documents, processes=None):
    if not documents:
        return {"results": [], "execution_time_seconds": 0.0, "documents": 0, "bytes": 0}
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=processes) as pool:
        results = list(pool.map(_analyze, documents))
    return {"results": results, "execution_time_seconds": perf_counter() - start,
            "documents": len(documents), "bytes": sum(len(t.encode("utf-8")) for _, t in documents),
            "processes": processes}
