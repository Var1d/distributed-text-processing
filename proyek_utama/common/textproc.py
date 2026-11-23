"""Logika pemrosesan teks (dipakai Master utk merge, Worker, dan baseline)."""
import hashlib
import json
import re
import unicodedata
from collections import Counter

TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
SENT_RE = re.compile(r"[.!?]+")
STOPWORDS = set("""a an the and or but if of to in on at by for with from as is are was were be been
it its this that these those he she they we you i not no so do does did have has had""".split())

def process_document(text, bigrams=False):
    text = unicodedata.normalize("NFKC", text)
    tokens = [t.casefold() for t in TOKEN_RE.findall(text)]
    words = [t for t in tokens if t not in STOPWORDS]
    uni = Counter(words)
    bi = Counter()
    if bigrams:
        bi = Counter(zip(words, words[1:]))
        bi = Counter({f"{a} {b}": c for (a, b), c in bi.items() if c >= 2})
    return {
        "chars": len(text), "tokens": len(tokens),
        "sentences": len(SENT_RE.findall(text)),
        "ttr": (len(set(tokens)) / len(tokens)) if tokens else 0.0,  # lexical diversity
        "uni": uni, "bi": bi,
    }

def new_result():
    return {"docs": 0, "chars": 0, "tokens": 0, "sentences": 0, "ttr_sum": 0.0,
            "uni": Counter(), "bi": Counter()}

def merge_into(acc, part):
    for k in ("docs", "chars", "tokens", "sentences", "ttr_sum"):
        acc[k] += part[k]
    acc["uni"].update(part["uni"]); acc["bi"].update(part["bi"])
    return acc

def process_batch(args):
    """args = (list[(name, text)], bigrams). Dipanggil di proses anak."""
    docs, bigrams = args
    acc = new_result()
    for _name, text in docs:
        d = process_document(text, bigrams)
        acc["docs"] += 1; acc["ttr_sum"] += d["ttr"]
        for k in ("chars", "tokens", "sentences"):
            acc[k] += d[k]
        acc["uni"].update(d["uni"]); acc["bi"].update(d["bi"])
    return acc

def to_wire(r):
    return {**r, "uni": dict(r["uni"]), "bi": dict(r["bi"])}

def from_wire(r):
    return {**r, "uni": Counter(r["uni"]), "bi": Counter(r["bi"])}


def counter_digest(counter):
    """Canonical digest for full word/bigram counts without bloating result JSON."""
    payload = json.dumps(sorted(counter.items()), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
