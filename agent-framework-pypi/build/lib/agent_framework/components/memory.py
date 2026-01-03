from __future__ import annotations

from typing import Any, Dict, List, Optional
from collections import defaultdict
import threading

from ..base import BaseMemory


class SharedStateStore:
    """Process-wide, thread-safe store for hierarchical, namespaced agent memory."""

    def __init__(self) -> None:
        self._global_feeds: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._agent_feeds: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        # Conversation history: stores turn-level user/assistant pairs
        self._conversation_feeds: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = threading.RLock()

    def append_global_update(self, namespace: str, update: Dict[str, Any]) -> None:
        with self._lock:
            self._global_feeds[namespace].append(dict(update))

    def append_agent_msg(self, namespace: str, agent_key: str, msg: Dict[str, Any]) -> None:
        with self._lock:
            self._agent_feeds[namespace][agent_key].append(dict(msg))
    
    def append_conversation_turn(self, namespace: str, role: str, content: str) -> None:
        """Add a conversation turn (user or assistant message) to the conversation feed."""
        with self._lock:
            import time
            turn = {
                "role": role,  # "user" or "assistant"
                "content": content,
                "timestamp": time.time()
            }
            self._conversation_feeds[namespace].append(turn)
            
            # Debug logging with context verification
            turn_num = len(self._conversation_feeds[namespace])
            
            # Verify context matches namespace
            from ..services.request_context import get_from_context
            context_job_id = get_from_context("JOB_ID") or get_from_context("job_id")
            
            if context_job_id and context_job_id != namespace:
                print(f"⚠️  [SharedStateStore] WARNING: Context mismatch!")
                print(f"    Namespace: {namespace}")
                print(f"    Context JOB_ID: {context_job_id}")
                print(f"    This indicates a potential async context propagation issue!")
            
            print(f"[SharedStateStore] 💬 Turn {turn_num} ({role}) added to namespace '{namespace}': {content[:100]}{'...' if len(content) > 100 else ''}")
    
    def list_conversation(self, namespace: str) -> List[Dict[str, Any]]:
        """Get the full conversation history for a namespace."""
        with self._lock:
            return list(self._conversation_feeds.get(namespace, []))

    def list_global_updates(self, namespace: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._global_feeds.get(namespace, []))

    def list_agent_msgs(self, namespace: str, agent_key: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._agent_feeds.get(namespace, {}).get(agent_key, []))

    def list_team_msgs(self, namespace: str, agent_keys: List[str]) -> List[Dict[str, Any]]:
        msgs = []
        with self._lock:
            for key in agent_keys:
                msgs.extend(self.list_agent_msgs(namespace, key))
        # Simple merge; for true chronological order, a timestamp sort would be needed
        return msgs


# Singleton instance
_shared_state_store = SharedStateStore()


class InMemoryMemory(BaseMemory):
    """Basic, single-agent, in-memory message history."""

    def __init__(self, agent_key: str = "default") -> None:
        self._agent_key = agent_key
        # Use a unique namespace per instance to isolate memory
        import uuid
        self._namespace = f"inmemory_{uuid.uuid4().hex}"

    def add(self, message: Dict[str, Any]) -> None:
        _shared_state_store.append_agent_msg(self._namespace, self._agent_key, message)

    def get_history(self) -> List[Dict[str, Any]]:
        return _shared_state_store.list_agent_msgs(self._namespace, self._agent_key)


class SharedInMemoryMemory(BaseMemory):
    """Shared, namespaced, in-memory message history for multi-agent collaboration."""

    def __init__(self, namespace: str, agent_key: str) -> None:
        if not namespace or not agent_key:
            raise ValueError("SharedInMemoryMemory requires a non-empty namespace and agent_key")
        self._namespace = namespace
        self._agent_key = agent_key

    def add(self, message: Dict[str, Any]) -> None:
        # By default, workers add to their private agent stream
        _shared_state_store.append_agent_msg(self._namespace, self._agent_key, message)

    def add_global(self, update: Dict[str, Any]) -> None:
        """Broadcast an update to all agents sharing this namespace.

        Useful for passing observations/results between workers in multi-step flows.
        """
        _shared_state_store.append_global_update(self._namespace, dict(update))

    def get_global_updates(self) -> List[Dict[str, Any]]:
        """Get all global updates in this namespace."""
        return _shared_state_store.list_global_updates(self._namespace)

    def get_history(self) -> List[Dict[str, Any]]:
        # Include conversation history at the start for context
        conversation = _shared_state_store.list_conversation(self._namespace)
        # Convert conversation format to memory format for planner compatibility
        conversation_msgs = []
        for turn in conversation:
            if turn["role"] == "user":
                conversation_msgs.append({"type": "user_message", "content": turn["content"]})
            elif turn["role"] == "assistant":
                conversation_msgs.append({"type": "assistant_message", "content": turn["content"]})
        
        # Workers see: conversation history + their own private notes + global updates
        agent_msgs = _shared_state_store.list_agent_msgs(self._namespace, self._agent_key)
        global_updates = _shared_state_store.list_global_updates(self._namespace)
        
        # Merge: conversation first, then agent execution traces, then global updates
        return conversation_msgs + agent_msgs + global_updates


class HierarchicalSharedMemory(SharedInMemoryMemory):
    """Manager-specific memory viewer that sees subordinate and global history."""

    def __init__(
        self,
        namespace: str,
        agent_key: str,
        subordinates: Optional[List[str]] = None,
    ) -> None:
        super().__init__(namespace, agent_key)
        self._subordinates = subordinates or []

    def get_history(self) -> List[Dict[str, Any]]:
        # Manager sees its own notes, all subordinate notes, and global updates
        manager_msgs = _shared_state_store.list_agent_msgs(self._namespace, self._agent_key)
        team_msgs = _shared_state_store.list_team_msgs(self._namespace, self._subordinates)
        global_updates = _shared_state_store.list_global_updates(self._namespace)
        # Simple merge
        return manager_msgs + team_msgs + global_updates
