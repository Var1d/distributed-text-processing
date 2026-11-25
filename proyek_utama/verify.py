"""Bandingkan keluaran baseline dan distributed secara lengkap."""
import json
import math
import sys


def main(left_path, right_path):
    with open(left_path, encoding="utf-8") as f:
        left = json.load(f)
    with open(right_path, encoding="utf-8") as f:
        right = json.load(f)

    fields = ("dataset_id", "bigrams", "docs", "chars", "tokens", "sentences",
              "uni_digest", "bi_digest", "top20_words")
    missing = [key for key in fields if key not in left or key not in right]
    if missing:
        raise SystemExit("Hasil lama/tidak lengkap; jalankan ulang baseline dan distributed. Hilang: "
                         + ", ".join(missing))

    ok = True
    for key in fields:
        same = left[key] == right[key]
        ok &= same
        print(f"{key:14s} -> {'SAMA' if same else 'BEDA'}")
    if "avg_ttr" in left and "avg_ttr" in right:
        same = math.isclose(left["avg_ttr"], right["avg_ttr"], rel_tol=1e-12, abs_tol=1e-12)
        ok &= same
        print(f"{'avg_ttr':14s} -> {'SAMA' if same else 'BEDA'}")
    print("HASIL VALID" if ok else "HASIL TIDAK SAMA!")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Pemakaian: python verify.py BASELINE.json DISTRIBUTED.json")
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
