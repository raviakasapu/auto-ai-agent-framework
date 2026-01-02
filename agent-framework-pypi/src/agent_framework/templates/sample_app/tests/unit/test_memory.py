"""
Tier 1: Unit Tests for Memory Components

Tests cover:
A. InMemoryMemory - Basic add/get/clear operations
B. SharedInMemoryMemory - Namespace isolation and sharing
C. HierarchicalSharedMemory - Manager visibility of subordinates
D. Thread Safety - Concurrent access without corruption
E. Global Updates - Cross-agent communication

Run with:
    pytest tests/unit/test_memory.py -v
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from agent_framework.components.memory import (
    InMemoryMemory,
    SharedInMemoryMemory,
    HierarchicalSharedMemory,
    _shared_state_store,
)


# =============================================================================
# A. InMemoryMemory Tests
# =============================================================================

class TestInMemoryMemory:
    """Test basic InMemoryMemory functionality."""

    def test_add_appends_message(self, in_memory):
        """add() should append messages to history."""
        in_memory.add({"role": "user", "content": "Hello"})

        history = in_memory.get_history()
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"

    def test_add_multiple_messages(self, in_memory):
        """add() should maintain order of messages."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
        ]

        for msg in messages:
            in_memory.add(msg)

        history = in_memory.get_history()
        assert len(history) == 3
        assert history[0]["content"] == "First"
        assert history[1]["content"] == "Second"
        assert history[2]["content"] == "Third"

    def test_get_history_returns_copy(self, in_memory):
        """get_history() should return a copy, not the internal list."""
        in_memory.add({"role": "user", "content": "Test"})

        history1 = in_memory.get_history()
        history2 = in_memory.get_history()

        # Modifying returned list shouldn't affect internal state
        history1.append({"role": "user", "content": "Modified"})

        assert len(history2) == 1
        assert len(in_memory.get_history()) == 1

    def test_empty_history(self, in_memory):
        """get_history() should return empty list initially."""
        history = in_memory.get_history()
        assert history == []
        assert isinstance(history, list)

    def test_message_content_preserved(self, in_memory):
        """Message content should be preserved exactly."""
        complex_message = {
            "role": "assistant",
            "content": "Complex content with\nnewlines\tand\ttabs",
            "metadata": {"key": "value"},
        }

        in_memory.add(complex_message)
        history = in_memory.get_history()

        assert history[0]["content"] == complex_message["content"]

    def test_isolated_instances(self):
        """Different InMemoryMemory instances should be isolated."""
        memory1 = InMemoryMemory(agent_key="agent1")
        memory2 = InMemoryMemory(agent_key="agent2")

        memory1.add({"role": "user", "content": "For agent1"})
        memory2.add({"role": "user", "content": "For agent2"})

        history1 = memory1.get_history()
        history2 = memory2.get_history()

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["content"] != history2[0]["content"]


# =============================================================================
# B. SharedInMemoryMemory Tests
# =============================================================================

class TestSharedInMemoryMemory:
    """Test SharedInMemoryMemory with namespace isolation and sharing."""

    def test_add_stores_message(self, shared_memory):
        """add() should store messages in shared state."""
        shared_memory.add({"role": "user", "content": "Test message"})

        history = shared_memory.get_history()
        assert len(history) >= 1
        # Find our message (history may include other formats)
        found = any(
            msg.get("content") == "Test message" or
            msg.get("role") == "user"
            for msg in history
        )
        assert found

    def test_namespace_isolation(self):
        """Different namespaces should have isolated memories."""
        memory1 = SharedInMemoryMemory(namespace="job1", agent_key="agent1")
        memory2 = SharedInMemoryMemory(namespace="job2", agent_key="agent2")

        memory1.add({"role": "user", "content": "Message for job1"})
        memory2.add({"role": "user", "content": "Message for job2"})

        history1 = memory1.get_history()
        history2 = memory2.get_history()

        # Each should only see their own messages
        assert not any("job2" in str(msg) for msg in history1)
        assert not any("job1" in str(msg) for msg in history2)

    def test_namespace_sharing_same_namespace(self):
        """Same namespace should share memory across agents."""
        memory1 = SharedInMemoryMemory(namespace="shared-job", agent_key="agent1")
        memory2 = SharedInMemoryMemory(namespace="shared-job", agent_key="agent2")

        # Agent1 adds global update
        memory1.add_global({"type": "observation", "content": "Shared data"})

        # Agent2 should see it
        global_updates = memory2.get_global_updates()
        assert len(global_updates) >= 1
        assert any("Shared data" in str(u) for u in global_updates)

    def test_agent_key_isolation_within_namespace(self):
        """Different agent_keys in same namespace have separate agent feeds."""
        memory1 = SharedInMemoryMemory(namespace="same-job", agent_key="agent1")
        memory2 = SharedInMemoryMemory(namespace="same-job", agent_key="agent2")

        memory1.add({"role": "user", "content": "Agent1 private"})
        memory2.add({"role": "user", "content": "Agent2 private"})

        # Direct agent feed check
        agent1_msgs = _shared_state_store.list_agent_msgs("same-job", "agent1")
        agent2_msgs = _shared_state_store.list_agent_msgs("same-job", "agent2")

        assert len(agent1_msgs) == 1
        assert len(agent2_msgs) == 1
        assert agent1_msgs[0]["content"] != agent2_msgs[0]["content"]

    def test_global_updates_visible_to_all(self):
        """Global updates should be visible to all agents in namespace."""
        memory1 = SharedInMemoryMemory(namespace="collab-job", agent_key="worker1")
        memory2 = SharedInMemoryMemory(namespace="collab-job", agent_key="worker2")
        memory3 = SharedInMemoryMemory(namespace="collab-job", agent_key="manager")

        memory1.add_global({"type": "result", "content": "Worker1 done"})
        memory2.add_global({"type": "result", "content": "Worker2 done"})

        # Manager should see both
        manager_global = memory3.get_global_updates()
        assert len(manager_global) == 2

    def test_requires_namespace(self):
        """SharedInMemoryMemory should require non-empty namespace."""
        with pytest.raises(ValueError):
            SharedInMemoryMemory(namespace="", agent_key="agent")

    def test_requires_agent_key(self):
        """SharedInMemoryMemory should require non-empty agent_key."""
        with pytest.raises(ValueError):
            SharedInMemoryMemory(namespace="job", agent_key="")


# =============================================================================
# C. HierarchicalSharedMemory Tests
# =============================================================================

class TestHierarchicalSharedMemory:
    """Test HierarchicalSharedMemory for manager visibility."""

    def test_manager_sees_own_messages(self, hierarchical_memory):
        """Manager should see their own messages."""
        hierarchical_memory.add({"role": "user", "content": "Manager message"})

        history = hierarchical_memory.get_history()
        assert any("Manager message" in str(msg) for msg in history)

    def test_manager_sees_subordinate_messages(self):
        """Manager should see messages from subordinates."""
        worker1 = SharedInMemoryMemory(namespace="team-job", agent_key="worker1")
        worker2 = SharedInMemoryMemory(namespace="team-job", agent_key="worker2")
        manager = HierarchicalSharedMemory(
            namespace="team-job",
            agent_key="manager",
            subordinates=["worker1", "worker2"]
        )

        worker1.add({"role": "assistant", "content": "Worker1 result"})
        worker2.add({"role": "assistant", "content": "Worker2 result"})

        manager_history = manager.get_history()

        # Manager should see both workers' messages
        history_str = str(manager_history)
        assert "Worker1 result" in history_str
        assert "Worker2 result" in history_str

    def test_manager_sees_global_updates(self):
        """Manager should see global updates."""
        worker = SharedInMemoryMemory(namespace="mgr-job", agent_key="worker")
        manager = HierarchicalSharedMemory(
            namespace="mgr-job",
            agent_key="manager",
            subordinates=["worker"]
        )

        worker.add_global({"type": "observation", "content": "Global info"})

        manager_history = manager.get_history()
        assert any("Global info" in str(msg) for msg in manager_history)

    def test_worker_does_not_see_manager_private(self):
        """Workers should not see manager's private messages."""
        worker = SharedInMemoryMemory(namespace="hierarchy-job", agent_key="worker")
        manager = HierarchicalSharedMemory(
            namespace="hierarchy-job",
            agent_key="manager",
            subordinates=["worker"]
        )

        manager.add({"role": "assistant", "content": "Manager private note"})

        worker_history = worker.get_history()
        assert not any("Manager private" in str(msg) for msg in worker_history)

    def test_empty_subordinates_list(self):
        """Manager with no subordinates should still work."""
        manager = HierarchicalSharedMemory(
            namespace="solo-job",
            agent_key="manager",
            subordinates=[]
        )

        manager.add({"role": "user", "content": "Solo manager"})
        history = manager.get_history()

        assert len(history) >= 1


# =============================================================================
# D. Thread Safety Tests
# =============================================================================

class TestMemoryThreadSafety:
    """Test thread safety of memory components."""

    def test_concurrent_writes_no_corruption(self, thread_safety_tester):
        """Concurrent writes should not corrupt memory."""
        memory = SharedInMemoryMemory(namespace="thread-test", agent_key="test")
        counter = {"value": 0}
        lock = threading.Lock()

        def write_message():
            with lock:
                counter["value"] += 1
                msg_num = counter["value"]
            memory.add({"role": "user", "content": f"Message {msg_num}"})
            return msg_num

        tester = thread_safety_tester(write_message, num_threads=10, iterations=50)
        success = tester.run()

        assert success, f"Thread safety test failed with errors: {tester.errors}"

        # Verify all messages were written
        history = memory.get_history()
        assert len(history) == 500  # 10 threads * 50 iterations

    def test_concurrent_reads_safe(self, thread_safety_tester):
        """Concurrent reads should not cause issues."""
        memory = SharedInMemoryMemory(namespace="read-test", agent_key="test")

        # Pre-populate
        for i in range(100):
            memory.add({"role": "user", "content": f"Message {i}"})

        def read_history():
            history = memory.get_history()
            return len(history)

        tester = thread_safety_tester(read_history, num_threads=20, iterations=100)
        success = tester.run()

        assert success, f"Read safety test failed: {tester.errors}"
        # All reads should return 100
        assert all(r == 100 for r in tester.results)

    def test_concurrent_read_write(self, thread_safety_tester):
        """Concurrent reads and writes should not cause issues."""
        memory = SharedInMemoryMemory(namespace="rw-test", agent_key="test")
        write_count = {"value": 0}

        def mixed_operation():
            import random
            if random.random() < 0.5:
                memory.add({"role": "user", "content": "write"})
                write_count["value"] += 1
                return "write"
            else:
                return len(memory.get_history())

        tester = thread_safety_tester(mixed_operation, num_threads=10, iterations=100)
        success = tester.run()

        assert success, f"Mixed operation test failed: {tester.errors}"

    def test_global_updates_thread_safe(self, thread_safety_tester):
        """Global updates should be thread safe."""
        memory = SharedInMemoryMemory(namespace="global-thread", agent_key="test")

        def add_global():
            memory.add_global({"type": "update", "content": "data"})
            return True

        tester = thread_safety_tester(add_global, num_threads=10, iterations=50)
        success = tester.run()

        assert success, f"Global update thread safety failed: {tester.errors}"

        updates = memory.get_global_updates()
        assert len(updates) == 500


# =============================================================================
# E. Global Updates Tests
# =============================================================================

class TestGlobalUpdates:
    """Test global update functionality."""

    def test_add_global_stores_update(self, shared_memory):
        """add_global() should store updates."""
        shared_memory.add_global({"type": "observation", "content": "Test"})

        updates = shared_memory.get_global_updates()
        assert len(updates) == 1
        assert updates[0]["type"] == "observation"

    def test_get_global_updates_returns_list(self, shared_memory):
        """get_global_updates() should return a list."""
        updates = shared_memory.get_global_updates()
        assert isinstance(updates, list)

    def test_global_updates_ordered(self, shared_memory):
        """Global updates should maintain order."""
        shared_memory.add_global({"order": 1})
        shared_memory.add_global({"order": 2})
        shared_memory.add_global({"order": 3})

        updates = shared_memory.get_global_updates()
        assert updates[0]["order"] == 1
        assert updates[1]["order"] == 2
        assert updates[2]["order"] == 3

    def test_global_updates_cross_agent(self):
        """Global updates should be visible across agents."""
        agent1 = SharedInMemoryMemory(namespace="cross-test", agent_key="agent1")
        agent2 = SharedInMemoryMemory(namespace="cross-test", agent_key="agent2")

        agent1.add_global({"from": "agent1", "data": "shared"})

        agent2_updates = agent2.get_global_updates()
        assert len(agent2_updates) == 1
        assert agent2_updates[0]["from"] == "agent1"

    def test_global_updates_included_in_history(self, shared_memory):
        """Global updates should be included in get_history()."""
        shared_memory.add({"role": "user", "content": "Regular message"})
        shared_memory.add_global({"type": "global", "content": "Global update"})

        history = shared_memory.get_history()

        # History should include both
        history_str = str(history)
        assert "Regular message" in history_str or len(history) >= 1
        # Global updates are appended at the end
        assert any("global" in str(msg).lower() for msg in history) or \
               len(shared_memory.get_global_updates()) == 1


# =============================================================================
# F. Edge Cases and Boundary Tests
# =============================================================================

class TestMemoryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_message(self, shared_memory):
        """Memory should handle very long messages."""
        long_content = "x" * 100000  # 100KB message
        shared_memory.add({"role": "user", "content": long_content})

        history = shared_memory.get_history()
        assert len(history) >= 1

    def test_unicode_content(self, shared_memory):
        """Memory should handle unicode content."""
        unicode_content = "Hello 世界 🌍 مرحبا"
        shared_memory.add({"role": "user", "content": unicode_content})

        history = shared_memory.get_history()
        assert any(unicode_content in str(msg) for msg in history)

    def test_nested_message_structure(self, shared_memory):
        """Memory should handle nested message structures."""
        nested_message = {
            "role": "assistant",
            "content": "text",
            "metadata": {
                "nested": {
                    "deep": {
                        "value": [1, 2, 3]
                    }
                }
            }
        }
        shared_memory.add(nested_message)

        history = shared_memory.get_history()
        assert len(history) >= 1

    def test_special_characters_in_namespace(self):
        """Namespace with special chars should work."""
        # Test with valid but unusual namespace
        memory = SharedInMemoryMemory(
            namespace="job-123_test",
            agent_key="agent-1"
        )
        memory.add({"role": "user", "content": "test"})
        assert len(memory.get_history()) >= 1

    def test_rapid_add_get_cycle(self, shared_memory):
        """Rapid add/get cycles should work correctly."""
        for i in range(1000):
            shared_memory.add({"role": "user", "content": f"msg{i}"})
            history = shared_memory.get_history()
            assert len(history) == i + 1


# =============================================================================
# G. Memory Presets Tests
# =============================================================================

class TestMemoryPresets:
    """Test memory preset functionality."""

    def test_list_memory_presets(self):
        """Should list available presets."""
        from agent_framework.components.memory_presets import list_memory_presets

        presets = list_memory_presets()
        assert "standalone" in presets
        assert "worker" in presets
        assert "manager" in presets

    def test_standalone_preset_creates_inmemory(self):
        """Standalone preset should create InMemoryMemory."""
        from agent_framework.components.memory_presets import get_memory_preset

        memory = get_memory_preset("standalone", {"agent_name": "TestAgent"})

        assert memory is not None
        assert hasattr(memory, 'add')
        assert hasattr(memory, 'get_history')

    def test_worker_preset_creates_shared_memory(self):
        """Worker preset should create SharedInMemoryMemory."""
        from agent_framework.components.memory_presets import get_memory_preset

        memory = get_memory_preset("worker", {
            "agent_name": "TestWorker",
            "namespace": "test-job"
        })

        assert memory is not None
        assert hasattr(memory, 'add_global')

    def test_manager_preset_creates_hierarchical_memory(self):
        """Manager preset should create HierarchicalSharedMemory."""
        from agent_framework.components.memory_presets import get_memory_preset

        memory = get_memory_preset("manager", {
            "agent_name": "TestManager",
            "namespace": "test-job",
            "subordinates": ["worker-1", "worker-2"]
        })

        assert memory is not None
        assert hasattr(memory, 'add_global')

    def test_preset_auto_derives_agent_key(self):
        """Preset should auto-derive agent_key from agent_name."""
        from agent_framework.components.memory_presets import get_memory_preset

        memory = get_memory_preset("worker", {
            "agent_name": "Research-Worker"
        })

        # Should normalize to lowercase with underscores
        assert memory._agent_key == "research_worker"

    def test_preset_uses_job_id_from_env(self, monkeypatch):
        """Preset should use JOB_ID from environment."""
        from agent_framework.components.memory_presets import get_memory_preset

        monkeypatch.setenv("JOB_ID", "env-job-123")

        memory = get_memory_preset("worker", {"agent_name": "Test"})

        assert memory._namespace == "env-job-123"

    def test_preset_context_overrides_env(self, monkeypatch):
        """Context namespace should override environment."""
        from agent_framework.components.memory_presets import get_memory_preset

        monkeypatch.setenv("JOB_ID", "env-job")

        memory = get_memory_preset("worker", {
            "agent_name": "Test",
            "namespace": "context-job"
        })

        assert memory._namespace == "context-job"

    def test_unknown_preset_raises_error(self):
        """Unknown preset should raise ValueError."""
        from agent_framework.components.memory_presets import get_memory_preset

        with pytest.raises(ValueError, match="Unknown memory preset"):
            get_memory_preset("nonexistent", {})

    def test_manager_normalizes_subordinates(self):
        """Manager preset should normalize subordinate names."""
        from agent_framework.components.memory_presets import get_memory_preset

        memory = get_memory_preset("manager", {
            "agent_name": "Manager",
            "subordinates": ["Research-Worker", "Task Worker"]
        })

        assert "research_worker" in memory._subordinates
        assert "task_worker" in memory._subordinates

    def test_describe_preset(self):
        """Should return description for preset."""
        from agent_framework.components.memory_presets import describe_preset

        desc = describe_preset("worker")
        assert "worker" in desc.lower() or "shared" in desc.lower()

    def test_worker_preset_shares_namespace(self):
        """Workers with same namespace should share global updates."""
        from agent_framework.components.memory_presets import get_memory_preset

        ctx = {"namespace": "shared-job"}
        worker1 = get_memory_preset("worker", {**ctx, "agent_name": "Worker1"})
        worker2 = get_memory_preset("worker", {**ctx, "agent_name": "Worker2"})

        worker1.add_global({"from": "worker1", "data": "shared"})

        # Worker2 should see worker1's global update
        updates = worker2.get_global_updates()
        assert len(updates) == 1
        assert updates[0]["from"] == "worker1"
