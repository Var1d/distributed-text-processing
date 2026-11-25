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
    token_count = 0
    unique_tokens = set()
    uni = Counter()
    bi = Counter()
    previous_word = None
    for match in TOKEN_RE.finditer(text):
        token = match.group().casefold()
        token_count += 1
        unique_tokens.add(token)
        if token in STOPWORDS:
            continue
        uni[token] += 1
        if bigrams and previous_word is not None:
            bi[f"{previous_word} {token}"] += 1
        previous_word = token
    if bigrams:
        bi = Counter({pair: count for pair, count in bi.items() if count >= 2})
    return {
        "chars": len(text), "tokens": token_count,
        "sentences": sum(1 for _ in SENT_RE.finditer(text)),
        "ttr": (len(unique_tokens) / token_count) if token_count else 0.0,  # lexical diversity
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
