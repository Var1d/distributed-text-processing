import argparse
from pathlib import Path

WORDS = ("komputasi paralel sistem terdistribusi pemrosesan teks worker master tokenisasi "
         "frekuensi dokumen jaringan dinamis toleransi kegagalan").split()


def generate(output, documents=20, words_per_document=10000):
    if documents < 1 or words_per_document < 1:
        raise ValueError("Jumlah dokumen dan kata harus positif.")
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    for i in range(documents):
        path = root / f"document_{i + 1:04d}.txt"
        with path.open("w", encoding="utf-8") as stream:
            for offset in range(words_per_document):
                stream.write(WORDS[(offset + i) % len(WORDS)])
                stream.write("\n" if offset % 20 == 19 else " ")
    return documents


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Membuat dataset teks sintetis deterministik.")
    parser.add_argument("--output", default="data/generated")
    parser.add_argument("--documents", type=int, default=20)
    parser.add_argument("--words-per-document", type=int, default=10000)
    args = parser.parse_args()
    print(f"File dibuat: {generate(args.output, args.documents, args.words_per_document)}")
