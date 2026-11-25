"""Create a reproducible text corpus for benchmarks.

Use ``--source gutenberg`` for public-domain books (cite Project Gutenberg in
the report), or ``--source synthetic`` for a deterministic generated workload.
The output directory must not already contain .txt files, so stale documents
cannot silently contaminate a benchmark.
"""
import argparse
import os
import random
import re
import urllib.request

BOOKS = [1342, 11, 84, 1661, 2701, 98, 174, 345, 2600, 1400, 76, 74, 1260,
         768, 135, 1184, 996, 2554, 5200, 1232, 158, 161, 215, 244, 521]


def gutenberg():
    texts = []
    for book_id in BOOKS:
        url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "uas-kpst"})
            raw = urllib.request.urlopen(request, timeout=30).read().decode("utf-8", "ignore")
            match = re.search(r"\*\*\* ?START OF.*?\*\*\*(.*?)\*\*\* ?END OF", raw, re.S)
            text = match.group(1) if match else raw
            if text.strip():
                texts.append(text.strip())
                print(f"ok {url}")
        except Exception as exc:
            print(f"gagal {url}: {exc}")
    if not texts:
        raise SystemExit("Tidak ada buku yang berhasil diunduh; coba lagi atau gunakan --source synthetic")
    return "\n\n".join(texts)


def write_synthetic(path, target_bytes, rng):
    vocab = [f"kata{i}" for i in range(5000)]
    weights = [1 / (i + 1) for i in range(len(vocab))]
    written = 0
    with open(path, "w", encoding="utf-8") as stream:
        while written < target_bytes:
            sentence = " ".join(rng.choices(vocab, weights, k=12)) + ".\n"
            stream.write(sentence)
            written += len(sentence.encode("utf-8"))


def write_gutenberg(path, text, target_bytes, offset):
    payload = text.encode("utf-8")
    if not payload:
        raise SystemExit("Teks sumber Gutenberg kosong")
    rotated = payload[offset % len(payload):] + payload[:offset % len(payload)]
    repeated = (rotated * (target_bytes // len(rotated) + 1))[:target_bytes]
    with open(path, "wb") as stream:
        stream.write(repeated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["gutenberg", "synthetic"], default="gutenberg")
    parser.add_argument("--out", default="data/corpus")
    parser.add_argument("--docs", type=int, default=1800)
    parser.add_argument("--doc-kb", type=int, default=200, help="ukuran target tiap dokumen (KB)")
    parser.add_argument("--seed", type=int, default=42, help="seed untuk korpus sintetis")
    args = parser.parse_args()
    if args.docs < 1 or args.doc_kb < 1:
        parser.error("--docs dan --doc-kb harus >= 1")

    os.makedirs(args.out, exist_ok=True)
    existing = [name for name in os.listdir(args.out) if name.lower().endswith(".txt")]
    if existing:
        raise SystemExit(f"Folder {args.out} sudah berisi .txt; pilih folder output kosong")

    text = gutenberg() if args.source == "gutenberg" else None
    target_bytes = args.doc_kb * 1024
    rng = random.Random(args.seed)
    for index in range(args.docs):
        path = os.path.join(args.out, f"doc_{index:05d}.txt")
        if text is None:
            write_synthetic(path, target_bytes, rng)
        else:
            write_gutenberg(path, text, target_bytes, index * target_bytes)
    print(f"{args.docs} dokumen -> {args.out} (target ~{args.docs * args.doc_kb / 1024:.2f} MiB)")
