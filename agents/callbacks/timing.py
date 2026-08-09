import time
import threading
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


class TimingCallbackHandler(BaseCallbackHandler):

    def __init__(self) -> None:
        self.records: list[dict] = []
        self._start_times: dict[UUID, tuple[str, str, float]] = {}
        self._lock = threading.Lock()
        return

    def on_llm_start(
        self, serialized: dict, prompts: list, *, run_id: UUID, **kwargs: Any
    ) -> None:
        with self._lock:
            self._start_times[run_id] = ("llm", "invoke", time.perf_counter())
        return

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._finish(run_id)
        return

    def on_tool_start(
        self, serialized: dict, input_str: str, *, run_id: UUID, **kwargs: Any
    ) -> None:
        tool_name = (serialized or {}).get("name", "unknown")
        with self._lock:
            self._start_times[run_id] = ("tool", tool_name, time.perf_counter())
        return

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._finish(run_id)
        return

    def _finish(self, run_id: UUID) -> None:

        with self._lock:
            entry = self._start_times.pop(run_id, None)
        if entry is None:
            return

        category, name, start_time = entry
        elapsed_seconds = time.perf_counter() - start_time
        record = {
            "category": category,
            "name": name,
            "elapsed_seconds": elapsed_seconds,
        }
        with self._lock:
            self.records.append(record)
        return
