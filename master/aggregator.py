from threading import Lock
from copy import deepcopy
from collections import Counter

from common.models import TaskResult


class Aggregator:
    """
    Mengumpulkan dan menggabungkan hasil pemrosesan dari Workers.

    Fitur:
    - Menyimpan hasil Task yang berhasil.
    - Mencegah hasil Task ID yang sama masuk dua kali.
    - Menggabungkan frekuensi kata.
    - Menghasilkan ringkasan analisis teks.
    """

    def __init__(self):
        self.results = {}
        self.lock = Lock()

    def add_result(self, result: TaskResult) -> bool:
        """
        Menambahkan hasil pemrosesan.

        Mengembalikan:
        True  : hasil berhasil ditambahkan.
        False : hasil gagal atau Task ID sudah pernah diterima.
        """

        if not isinstance(result, TaskResult):
            raise TypeError("Result harus berupa TaskResult.")

        if not result.success:
            return False

        if not result.task_id:
            raise ValueError("Task ID tidak boleh kosong.")

        with self.lock:
            if result.task_id in self.results:
                return False

            self.results[result.task_id] = deepcopy(result)

        return True

    def get_result(self, task_id: str):
        """Mengambil hasil berdasarkan Task ID."""

        with self.lock:
            result = self.results.get(task_id)

            if result is None:
                return None

            return deepcopy(result)

    def get_all_results(self) -> list:
        """Mengambil seluruh hasil yang berhasil dikumpulkan."""

        with self.lock:
            return deepcopy(list(self.results.values()))

    def get_result_count(self) -> int:
        """Menghitung jumlah hasil yang tersimpan."""

        with self.lock:
            return len(self.results)

    def aggregate_word_frequencies(self) -> dict:
        """
        Menggabungkan frekuensi kata dari seluruh hasil Worker.

        Format result yang diharapkan:
        {
            "word_frequency": {
                "python": 5,
                "java": 3
            }
        }
        """

        total_frequency = Counter()

        with self.lock:
            results = deepcopy(list(self.results.values()))

        for task_result in results:
            frequencies = task_result.result.get("word_frequency", {})

            if not isinstance(frequencies, dict):
                raise ValueError("word_frequency harus berupa dictionary.")

            for word, count in frequencies.items():
                if not isinstance(word, str) or not word:
                    raise ValueError("Nama kata tidak valid.")

                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise ValueError(
                        f"Frekuensi kata '{word}' harus " "berupa integer nonnegatif."
                    )

                total_frequency[word] += count

        return dict(total_frequency)

    def get_summary(self) -> dict:
        """Menghasilkan ringkasan keseluruhan hasil pemrosesan."""

        frequencies = self.aggregate_word_frequencies()

        with self.lock:
            results = deepcopy(list(self.results.values()))

        document_ids = {
            result.result.get("document_id")
            for result in results
            if result.result.get("document_id") is not None
        }

        total_words = sum(frequencies.values())

        return {
            "total_tasks": len(results),
            "total_documents": len(document_ids),
            "total_words": total_words,
            "unique_words": len(frequencies),
            "word_frequency": frequencies,
        }
