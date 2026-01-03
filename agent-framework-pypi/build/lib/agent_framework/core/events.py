from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base import BaseEventSubscriber
from ..logging import get_logger
from pprint import pformat
import logging


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[BaseEventSubscriber] = []

    def subscribe(self, subscriber: BaseEventSubscriber) -> None:
        self._subscribers.append(subscriber)

    def publish(self, event_name: str, data: Dict[str, Any]) -> None:
        for sub in list(self._subscribers):
            try:
                sub.handle_event(event_name, data)
            except Exception as exc:  # Keep observability from breaking the flow
                print(f"[EventBus] Subscriber error on {event_name}: {exc}")


class LoggingSubscriber(BaseEventSubscriber):
    def __init__(
        self,
        level: str | None = None,
        include_data: bool = True,
        max_payload_chars: int = 2000,
        event_levels: Optional[Dict[str, str]] = None,
    ) -> None:
        self.logger = get_logger(level)
        self.include_data = include_data
        self.max_payload_chars = max_payload_chars
        self.event_level_map = {
            "error": logging.ERROR,
            "agent_end": logging.INFO,
            "manager_end": logging.INFO,
            "agent_start": logging.INFO,
            "manager_start": logging.INFO,
            "action_planned": logging.DEBUG,
            "delegation_planned": logging.DEBUG,
            "delegation_chosen": logging.DEBUG,
            "action_executed": logging.DEBUG,
        }
        if event_levels:
            for name, lvl in event_levels.items():
                try:
                    self.event_level_map[name] = getattr(logging, lvl.upper())
                except AttributeError:
                    continue

    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        level = self.event_level_map.get(event_name, self.logger.level)
        if not self.logger.isEnabledFor(level):
            return
        message = f"event={event_name}"
        if self.include_data and data:
            payload = pformat(data, compact=True, width=120)
            if len(payload) > self.max_payload_chars:
                payload = payload[: self.max_payload_chars] + "...(truncated)"
            message += f" data={payload}"
        self.logger.log(level, message)
