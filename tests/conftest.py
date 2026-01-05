"""Shared pytest fixtures and configuration."""

import os

import pytest


@pytest.fixture
def mock_tmux_env(monkeypatch):
    """Set up a mock TMUX environment variable."""
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")
    return os.environ["TMUX"]


@pytest.fixture
def no_tmux_env(monkeypatch):
    """Remove TMUX environment variable."""
    monkeypatch.delenv("TMUX", raising=False)
