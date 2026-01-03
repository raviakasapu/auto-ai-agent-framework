from __future__ import annotations

from typing import Any, Dict, List, Union

from ..base import BasePromptManager


class StaticPromptManager(BasePromptManager):
    def __init__(self, template: str | None = None) -> None:
        self.template = template or "Task: {task}\nHistory count: {history_len}"

    def generate_prompt(self, **kwargs) -> Union[str, List[Dict]]:
        task = kwargs.get("task", "")
        history = kwargs.get("history", [])
        return self.template.format(task=task, history_len=len(history))

