"""Unit tests for memory.context_manager module."""
import pytest

from memory.context_manager import ContextBudget, ContextManager


# ── ContextBudget ─────────────────────────────────────────────────────────


def test_context_budget__available__initial():
    b = ContextBudget(max_tokens=1000, reserved_tokens=100)
    assert b.available == 900


def test_context_budget__available__never_negative():
    b = ContextBudget(max_tokens=100, reserved_tokens=50, used_tokens=200)
    assert b.available == 0


def test_context_budget__consume__decreases_available():
    b = ContextBudget(max_tokens=1000, reserved_tokens=0)
    b.consume(300)
    assert b.used_tokens == 300
    assert b.available == 700


def test_context_budget__utilization__zero_initially():
    b = ContextBudget(max_tokens=1000)
    assert b.utilization == 0.0


def test_context_budget__utilization__after_consume():
    b = ContextBudget(max_tokens=1000)
    b.consume(500)
    assert b.utilization == pytest.approx(0.5)


def test_context_budget__utilization__zero_max():
    b = ContextBudget(max_tokens=0)
    assert b.utilization == 1.0


# ── ContextManager ────────────────────────────────────────────────────────


def test_context_manager__add_episode__within_budget():
    cm = ContextManager(max_tokens=10000)
    assert cm.add_episode({"content": "hello"}, estimated_tokens=50) is True
    assert len(cm._episodes) == 1


def test_context_manager__add_episode__exceeds_budget():
    cm = ContextManager(max_tokens=200)
    cm.budget.reserved_tokens = 100
    assert cm.add_episode({"content": "large"}, estimated_tokens=200) is False
    assert len(cm._episodes) == 0


def test_context_manager__get_context_episodes__sorted_by_importance():
    cm = ContextManager(max_tokens=100000)
    cm.add_episode({"content": "low", "importance": 0.1}, 10)
    cm.add_episode({"content": "high", "importance": 0.9}, 10)
    cm.add_episode({"content": "mid", "importance": 0.5}, 10)
    episodes = cm.get_context_episodes()
    importances = [e["importance"] for e in episodes]
    assert importances == sorted(importances, reverse=True)


def test_context_manager__should_summarize__below_threshold():
    cm = ContextManager(max_tokens=1000)
    cm.budget.consume(100)
    assert cm.should_summarize() is False


def test_context_manager__should_summarize__above_threshold():
    cm = ContextManager(max_tokens=1000)
    cm.budget.consume(850)
    assert cm.should_summarize() is True


def test_context_manager__summarize_old_context__too_few_episodes():
    cm = ContextManager(max_tokens=100000)
    for i in range(3):
        cm.add_episode({"content": f"ep{i}", "event_type": "test"}, 100)
    assert cm.summarize_old_context() == ""
    assert len(cm._episodes) == 3


def test_context_manager__summarize_old_context__halves_episodes():
    cm = ContextManager(max_tokens=100000)
    for i in range(10):
        cm.add_episode({"content": f"episode {i}", "event_type": "test"}, 100)
    assert cm.budget.used_tokens == 1000

    summary = cm.summarize_old_context()
    assert "Previous context summary" in summary
    assert len(cm._episodes) == 5
    assert cm.budget.used_tokens == 500


def test_context_manager__summarize_old_context__frees_tokens():
    cm = ContextManager(max_tokens=100000)
    for i in range(6):
        cm.add_episode({"content": f"ep{i}", "event_type": "action"}, 100)
    before = cm.budget.used_tokens
    cm.summarize_old_context()
    assert cm.budget.used_tokens < before
