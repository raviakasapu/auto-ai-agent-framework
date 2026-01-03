from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union, Type, Optional
from pydantic import BaseModel, Field


# Simple structured payloads used by planners and the agent loop
@dataclass
class Action:
    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)


class FinalResponse(BaseModel):
    """
    Represents a final, structured response to the user or application.
    
    This is returned when the agent has completed its task and needs to communicate
    the result in a machine-readable format for frontend consumption.
    """
    operation: str = Field(
        ..., 
        description="The high-level operation the frontend should perform (e.g., 'display_message', 'update_file_tree', 'display_table', 'model_ops')."
    )
    payload: Dict[str, Any] = Field(
        ..., 
        description="A JSON object containing the data needed to execute the operation."
    )
    human_readable_summary: str = Field(
        ..., 
        description="A natural language summary of the result for display in a chat log."
    )


class BasePlanner(ABC):
    @abstractmethod
    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, List[Action], FinalResponse]:
        """
        Plan the next step(s) for the agent.
        
        Returns:
            - Action: Single action to execute sequentially
            - List[Action]: Multiple actions to execute in parallel
            - FinalResponse: Task is complete, return final answer
        """
        raise NotImplementedError


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def args_schema(self) -> Type[BaseModel]:
        """Pydantic model that defines the tool's input schema."""
        raise NotImplementedError

    @property
    @abstractmethod
    def output_schema(self) -> Optional[Type[BaseModel]]:
        """Optional Pydantic model defining the tool's structured output schema."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        raise NotImplementedError


class BaseMemory(ABC):
    @abstractmethod
    async def add(self, message: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_history(self) -> List[Dict[str, Any]]:
        raise NotImplementedError


class BasePromptManager(ABC):
    @abstractmethod
    def generate_prompt(self, **kwargs) -> Union[str, List[Dict[str, Any]]]:
        raise NotImplementedError


class BaseInferenceGateway(ABC):
    @abstractmethod
    def invoke(self, prompt: Union[str, List[Dict[str, Any]]]) -> str:
        raise NotImplementedError


class BaseEventSubscriber(ABC):
    @abstractmethod
    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError


class BaseProgressHandler(ABC):
    @abstractmethod
    async def on_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Async progress callback used by applications to receive real-time updates."""
        raise NotImplementedError


class BaseJobStore(ABC):
    """Abstract interface for job persistence.
    
    Implementations can provide their own job store (file-based, database, etc.)
    or pass None to disable job persistence entirely.
    """
    
    @abstractmethod
    def create_job(self, job_id: str) -> Any:
        """Create a new job entry."""
        raise NotImplementedError
    
    @abstractmethod
    def update_orchestrator_plan(self, job_id: str, plan: Dict[str, Any]) -> None:
        """Update the orchestrator plan for a job."""
        raise NotImplementedError
    
    @abstractmethod
    def update_manager_plan(self, job_id: str, manager: str, plan: Dict[str, Any]) -> None:
        """Update a manager's plan for a job."""
        raise NotImplementedError
    
    @abstractmethod
    def save_pending_action(
        self,
        job_id: str,
        *,
        worker: str,
        tool: str,
        args: Dict[str, Any],
        manager: Optional[str] = None,
        resume_token: Optional[str] = None,
    ) -> None:
        """Save a pending action requiring approval."""
        raise NotImplementedError


class BaseMessageStore(ABC):
    """Abstract interface for message storage.
    
    Implementations prepare and manage message stores. The framework reads messages
    directly from the store using the location reference provided.
    
    The store must return messages in the framework's expected format:
    - Each message is a dict with at minimum "type" and "content" fields
    - Type must be one of the constants from agent_framework.constants
    - See MESSAGE_STORE_FORMAT.md for complete format specification
    """
    
    @abstractmethod
    def get_conversation_messages(
        self,
        location: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation messages (user_message, assistant_message) for a location.
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            limit: Optional limit on number of messages to return
            
        Returns:
            List of message dicts in framework format, ordered chronologically
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_agent_messages(
        self,
        location: str,
        agent_key: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get execution trace messages for a specific agent.
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            agent_key: Identifier for the agent (e.g., "orchestrator", "worker-1")
            limit: Optional limit on number of messages to return
            
        Returns:
            List of message dicts in framework format (task, action, observation, etc.)
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_global_messages(
        self,
        location: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get global/broadcast messages (global_observation, synthesis, etc.).
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            limit: Optional limit on number of messages to return
            
        Returns:
            List of global message dicts in framework format
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_team_messages(
        self,
        location: str,
        agent_keys: List[str],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from multiple agents (for managers viewing subordinates).
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            agent_keys: List of agent identifiers
            limit: Optional limit on number of messages to return per agent
            
        Returns:
            List of message dicts from all specified agents, ordered chronologically
        """
        raise NotImplementedError
