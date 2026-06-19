"""Shared pytest fixtures.

Real fixtures land in M3 (pipeline) and M4 (agents). For now this just ensures
the test suite has a conftest so `pytest` collection succeeds against an empty
suite without warning.
"""

from __future__ import annotations
