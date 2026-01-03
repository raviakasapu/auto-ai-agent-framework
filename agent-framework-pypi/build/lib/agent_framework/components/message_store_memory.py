"""
Memory implementation that reads from a message store.

This allows implementations to prepare message stores in their preferred format
and the framework reads messages directly from the store.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base import BaseMemory, BaseMessageStore


class MessageStoreMemory(BaseMemory):
    """Memory implementation that reads from an external message store.
    
    The implementation prepares the message store and passes a location reference.
    The framework reads messages directly from the store.
    """
    
    def __init__(
        self,
        message_store: BaseMessageStore,
        location: str,
        agent_key: str,
    ) -> None:
        """Initialize memory backed by a message store.
        
        Args:
            message_store: The message store implementation to read from
            location: Location reference (e.g., job_id, namespace, or store path)
            agent_key: Identifier for this agent (e.g., "orchestrator", "worker-1")
        """
        if not message_store or not location or not agent_key:
            raise ValueError("message_store, location, and agent_key are required")
        self._message_store = message_store
        self._location = location
        self._agent_key = agent_key
    
    def add(self, message: Dict[str, Any]) -> None:
        """Add a message to the store.
        
        Note: This is a no-op for message store memory. Implementations should
        write directly to their store. The framework will read messages via get_history().
        
        For backward compatibility, this method exists but does nothing.
        If you need runtime message storage, use SharedInMemoryMemory instead.
        """
        # No-op: Implementation manages the store
        # Framework reads via get_history() which calls the store
        pass
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get history by reading from the message store.
        
        Returns messages in the order expected by the framework:
        1. Conversation messages (user_message, assistant_message)
        2. Agent execution traces (task, action, observation, etc.)
        3. Global messages (global_observation, synthesis, etc.)
        """
        history = []
        
        # Get conversation messages
        conversation = self._message_store.get_conversation_messages(self._location)
        history.extend(conversation)
        
        # Get agent-specific execution traces
        agent_msgs = self._message_store.get_agent_messages(
            self._location,
            self._agent_key
        )
        history.extend(agent_msgs)
        
        # Get global messages
        global_msgs = self._message_store.get_global_messages(self._location)
        history.extend(global_msgs)
        
        return history


class HierarchicalMessageStoreMemory(MessageStoreMemory):
    """Memory for managers that can see subordinate agent messages."""
    
    def __init__(
        self,
        message_store: BaseMessageStore,
        location: str,
        agent_key: str,
        subordinates: Optional[List[str]] = None,
    ) -> None:
        """Initialize hierarchical memory backed by a message store.
        
        Args:
            message_store: The message store implementation to read from
            location: Location reference (e.g., job_id, namespace, or store path)
            agent_key: Identifier for this manager agent
            subordinates: List of subordinate agent keys this manager can see
        """
        super().__init__(message_store, location, agent_key)
        self._subordinates = subordinates or []
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get history including subordinate agent messages."""
        history = []
        
        # Get conversation messages
        conversation = self._message_store.get_conversation_messages(self._location)
        history.extend(conversation)
        
        # Get manager's own messages
        manager_msgs = self._message_store.get_agent_messages(
            self._location,
            self._agent_key
        )
        history.extend(manager_msgs)
        
        # Get subordinate messages
        if self._subordinates:
            team_msgs = self._message_store.get_team_messages(
                self._location,
                self._subordinates
            )
            history.extend(team_msgs)
        
        # Get global messages
        global_msgs = self._message_store.get_global_messages(self._location)
        history.extend(global_msgs)
        
        return history

