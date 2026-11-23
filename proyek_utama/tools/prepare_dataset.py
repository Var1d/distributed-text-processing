"""Siapkan korpus teks.
 --source gutenberg : unduh buku domain publik dari Project Gutenberg (https://www.gutenberg.org),
                      lalu dipecah menjadi banyak dokumen. CANTUMKAN sumber ini di laporan.
 --source synthetic : korpus sintetis (Zipf) untuk uji cepat/debug.
"""
import argparse, os, random, re, urllib.request
BOOKS = [1342, 11, 84, 1661, 2701, 98, 174, 345, 2600, 1400, 76, 74, 1260, 768, 135, 1184, 996, 2554, 5200, 1232, 158, 161, 215, 244, 521]

def gutenberg():
    texts = []
    for b in BOOKS:
        url = f"https://www.gutenberg.org/cache/epub/{b}/pg{b}.txt"
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "uas-kpst"}), timeout=30).read().decode("utf-8", "ignore")
            m = re.search(r"\*\*\* ?START OF.*?\*\*\*(.*?)\*\*\* ?END OF", raw, re.S)
            texts.append(m.group(1) if m else raw); print("ok", url)
        except Exception as e:
            print("gagal", url, e)
    return " ".join(texts)

def synthetic(n_words):
    rnd = random.Random(42); vocab = [f"kata{i}" for i in range(5000)]
    w = [1 / (i + 1) for i in range(5000)]
    return " ".join(" ".join(rnd.choices(vocab, w, k=12)) + "." for _ in range(n_words // 12))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["gutenberg", "synthetic"], default="gutenberg")
    p.add_argument("--out", default="data/corpus"); p.add_argument("--docs", type=int, default=1800)
    p.add_argument("--doc-kb", type=int, default=200, help="ukuran target tiap dokumen (KB)")
    p.add_argument("--copies", type=int, default=1, help="ulang korpus utk memperbesar data")
    a = p.parse_args(); os.makedirs(a.out, exist_ok=True)
    text = gutenberg() if a.source == "gutenberg" else synthetic(a.docs * a.doc_kb * 170)
    text = (text + "\n") * a.copies; size = a.doc_kb * 1000
    n = min(a.docs, max(1, len(text) // size))
    for i in range(n):
        open(os.path.join(a.out, f"doc_{i:05d}.txt"), "w", encoding="utf-8").write(text[i * size:(i + 1) * size])
    print(f"{n} dokumen -> {a.out} (target ~{n * a.doc_kb / 1000:.2f} MB)")
