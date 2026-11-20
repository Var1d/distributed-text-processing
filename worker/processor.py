import time

from common.models import Task, TaskResult

from processing.document_analysis import analyze_document
from processing.frequency import get_most_common

from worker.parallel import parallel_count_words


def process_task(task: Task, worker_id: str, processes: int = 1) -> TaskResult:
    """
    Memproses satu Task dan menghasilkan TaskResult.
    """

    start_time = time.perf_counter()

    try:
        if processes > 1:
            frequencies = parallel_count_words(task.content, processes)

            total_words = sum(frequencies.values())

            result = {
                "document_id": task.document_id,
                "total_words": total_words,
                "unique_words": len(frequencies),
                "word_frequency": frequencies,
                "most_common": [
                    [word, count] for word, count in get_most_common(frequencies, 10)
                ],
            }

        else:
            result = analyze_document(task.document_id, task.content)

        processing_time = time.perf_counter() - start_time

        return TaskResult(
            task_id=task.task_id,
            worker_id=worker_id,
            success=True,
            result=result,
            error=None,
            processing_time=processing_time,
            attempt=task.attempt,
        )

    except Exception as error:
        processing_time = time.perf_counter() - start_time

        return TaskResult(
            task_id=task.task_id,
            worker_id=worker_id,
            success=False,
            result={},
            error=str(error),
            processing_time=processing_time,
            attempt=task.attempt,
        )
