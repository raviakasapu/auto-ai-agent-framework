"""
Policy Presets for Framework v2.

Presets provide common policy configurations for quick adoption.
"""

from .default import (
    DefaultCompletionDetector,
    DefaultTerminationPolicy,
    DefaultLoopPreventionPolicy,
    DefaultHITLPolicy,
    DefaultCheckpointPolicy,
    DefaultFollowUpPolicy,
)


PRESETS = {
    "simple": {
        "completion": DefaultCompletionDetector(
            indicators=["completed", "success", "done", "finished", "task complete"],
            check_response_validation=True,
            check_operation_types=["display_message", "model_ops", "display_table"],
            check_history_depth=10
        ),
        "termination": DefaultTerminationPolicy(
            max_iterations=10,
            check_completion=True,
            terminal_tools=[],
            on_max_iterations="error"
        ),
        "loop_prevention": DefaultLoopPreventionPolicy(
            enabled=True,
            action_window=5,
            observation_window=5,
            repetition_threshold=3,
            check_completion_in_loop=True,
            on_stagnation="error"
        ),
        "hitl": DefaultHITLPolicy(enabled=False),
        "checkpoint": DefaultCheckpointPolicy(enabled=False),
    },
    
    "manager_with_followups": {
        "completion": DefaultCompletionDetector(
            indicators=["completed", "success", "done"],
            check_response_validation=True
        ),
        "follow_up": DefaultFollowUpPolicy(
            enabled=True,
            max_phases=5,
            check_completion=True,
            stop_on_completion=True
        ),
        "loop_prevention": DefaultLoopPreventionPolicy(
            enabled=True
        ),
    },
    
    "with_hitl": {
        "completion": DefaultCompletionDetector(
            indicators=["completed", "success", "done"],
            check_response_validation=True
        ),
        "termination": DefaultTerminationPolicy(
            max_iterations=15,
            check_completion=True
        ),
        "loop_prevention": DefaultLoopPreventionPolicy(
            enabled=True,
            repetition_threshold=3
        ),
        "hitl": DefaultHITLPolicy(
            enabled=True,
            scope="writes"
        ),
        "checkpoint": DefaultCheckpointPolicy(enabled=False),
    },
    
    "with_checkpoints": {
        "completion": DefaultCompletionDetector(
            indicators=["completed", "success", "done"]
        ),
        "termination": DefaultTerminationPolicy(
            max_iterations=20,
            check_completion=True
        ),
        "loop_prevention": DefaultLoopPreventionPolicy(
            enabled=True
        ),
        "hitl": DefaultHITLPolicy(enabled=False),
        "checkpoint": DefaultCheckpointPolicy(
            enabled=True,
            checkpoint_after_iterations=5,
            checkpoint_on_operations=["display_table"]
        ),
    },
}


def get_preset(preset_name: str) -> dict:
    """Get a preset policy configuration."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    return PRESETS[preset_name].copy()


def list_presets() -> list[str]:
    """List available preset names."""
    return list(PRESETS.keys())

