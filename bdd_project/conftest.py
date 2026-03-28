"""
Root conftest.py for BDD project.
"""

import pytest

# Load common steps and fixtures
pytest_plugins = ["bdd_project.steps.common.shared_steps"]
