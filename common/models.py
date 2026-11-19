from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class Task:
    """Representasi satu pekerjaan yang diberikan Master kepada Worker."""

    task_id: str
    document_id: str
    content: str
    attempt: int = 1
    max_attempts: int = 3
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "document_id": self.document_id,
            "content": self.content,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class WorkerInfo:
    """Informasi kemampuan dan kondisi sebuah Worker."""

    worker_id: str
    hostname: str
    cpu_cores: int
    total_memory_mb: float
    cpu_percent: float = 0.0
    available_slots: int = 1
    active_tasks: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    status: str = "IDLE"

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "hostname": self.hostname,
            "cpu_cores": self.cpu_cores,
            "total_memory_mb": self.total_memory_mb,
            "cpu_percent": self.cpu_percent,
            "available_slots": self.available_slots,
            "active_tasks": self.active_tasks,
            "last_heartbeat": self.last_heartbeat,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class TaskResult:
    """Hasil pemrosesan task dari Worker."""

    task_id: str
    worker_id: str
    success: bool
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    processing_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "processing_time": self.processing_time,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
