"""
Policy System for Framework v2

Policies control framework behavior in a configurable, pluggable way.
All behavior that was previously hardcoded is now policy-driven.
"""

from .base import (
    CompletionDetector,
    TerminationPolicy,
    LoopPreventionPolicy,
    HITLPolicy,
    CheckpointPolicy,
    FollowUpPolicy,
    HistoryFilter,
)

from .default import (
    DefaultCompletionDetector,
    DefaultTerminationPolicy,
    DefaultLoopPreventionPolicy,
    DefaultHITLPolicy,
    DefaultCheckpointPolicy,
    DefaultFollowUpPolicy,
)

from .history_filters import (
    OrchestratorHistoryFilter,
    ManagerHistoryFilter,
    WorkerHistoryFilter,
    DefaultHistoryFilter,
)

__all__ = [
    # Base classes
    "CompletionDetector",
    "TerminationPolicy",
    "LoopPreventionPolicy",
    "HITLPolicy",
    "CheckpointPolicy",
    "FollowUpPolicy",
    "HistoryFilter",
    # Default implementations
    "DefaultCompletionDetector",
    "DefaultTerminationPolicy",
    "DefaultLoopPreventionPolicy",
    "DefaultHITLPolicy",
    "DefaultCheckpointPolicy",
    "DefaultFollowUpPolicy",
    # History filters
    "OrchestratorHistoryFilter",
    "ManagerHistoryFilter",
    "WorkerHistoryFilter",
    "DefaultHistoryFilter",
]

