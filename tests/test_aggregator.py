import pytest

from master.aggregator import Aggregator
from common.models import TaskResult


def create_result(task_id, worker_id="WORKER-01", success=True, result=None):
    return TaskResult(
        task_id=task_id,
        worker_id=worker_id,
        success=success,
        result=result or {},
        error=None,
        processing_time=0.5,
    )


def test_add_successful_result():
    aggregator = Aggregator()

    result = create_result("TASK-01")

    assert aggregator.add_result(result) is True
    assert aggregator.get_result_count() == 1


def test_failed_result_not_added():
    aggregator = Aggregator()

    result = create_result("TASK-01", success=False)

    assert aggregator.add_result(result) is False
    assert aggregator.get_result_count() == 0


def test_duplicate_task_result_rejected():
    aggregator = Aggregator()

    result = create_result("TASK-01")

    assert aggregator.add_result(result) is True
    assert aggregator.add_result(result) is False

    assert aggregator.get_result_count() == 1


def test_invalid_result_type():
    aggregator = Aggregator()

    with pytest.raises(TypeError):
        aggregator.add_result({"task_id": "TASK-01"})


def test_get_result():
    aggregator = Aggregator()

    result = create_result("TASK-01")
    aggregator.add_result(result)

    stored = aggregator.get_result("TASK-01")

    assert stored is not None
    assert stored.task_id == "TASK-01"


def test_get_missing_result():
    aggregator = Aggregator()

    assert aggregator.get_result("TASK-99") is None


def test_get_all_results():
    aggregator = Aggregator()

    aggregator.add_result(create_result("TASK-01"))
    aggregator.add_result(create_result("TASK-02"))

    results = aggregator.get_all_results()

    assert len(results) == 2


def test_aggregate_word_frequencies():
    aggregator = Aggregator()

    aggregator.add_result(
        create_result("TASK-01", result={"word_frequency": {"python": 5, "java": 3}})
    )

    aggregator.add_result(
        create_result(
            "TASK-02",
            worker_id="WORKER-02",
            result={"word_frequency": {"python": 2, "java": 4}},
        )
    )

    frequencies = aggregator.aggregate_word_frequencies()

    assert frequencies == {"python": 7, "java": 7}


def test_get_summary():
    aggregator = Aggregator()

    aggregator.add_result(
        create_result(
            "TASK-01",
            result={
                "document_id": "DOC-001",
                "word_frequency": {"python": 5, "java": 3},
            },
        )
    )

    aggregator.add_result(
        create_result(
            "TASK-02",
            worker_id="WORKER-02",
            result={
                "document_id": "DOC-002",
                "word_frequency": {"python": 2, "programming": 4},
            },
        )
    )

    summary = aggregator.get_summary()

    assert summary["total_tasks"] == 2
    assert summary["total_documents"] == 2
    assert summary["total_words"] == 14
    assert summary["unique_words"] == 3

    assert summary["word_frequency"] == {"python": 7, "java": 3, "programming": 4}


def test_invalid_word_frequency():
    aggregator = Aggregator()

    aggregator.add_result(
        create_result("TASK-01", result={"word_frequency": {"python": -5}})
    )

    with pytest.raises(ValueError):
        aggregator.aggregate_word_frequencies()
