import threading
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult


class TokenUsageCallbackHandler(BaseCallbackHandler):

    def __init__(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self._lock = threading.Lock()
        return

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:

        try:
            generation = response.generations[0][0]
        except IndexError:
            return

        message = getattr(generation, "message", None)
        usage_metadata = message.usage_metadata if isinstance(message, AIMessage) else None

        if usage_metadata:
            prompt_tokens = usage_metadata["input_tokens"]
            completion_tokens = usage_metadata["output_tokens"]
            total_tokens = usage_metadata["total_tokens"]
        else:
            token_usage = (response.llm_output or {}).get("token_usage")
            if not token_usage:
                return
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
            total_tokens = token_usage.get("total_tokens", 0)

        with self._lock:
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.total_tokens += total_tokens
        return
