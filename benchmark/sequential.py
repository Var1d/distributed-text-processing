from time import perf_counter
from processing.document_analysis import analyze_document


def run_sequential(documents):
    start = perf_counter()
    results = [analyze_document(name, text) for name, text in documents]
    return {"results": results, "execution_time_seconds": perf_counter() - start,
            "documents": len(documents), "bytes": sum(len(t.encode("utf-8")) for _, t in documents)}
