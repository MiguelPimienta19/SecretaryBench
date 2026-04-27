"""Pytest helper — ensures repo root is on sys.path so tests can import
top-level modules (loader, grader, flow_controller, engine) and the `app`
package directly.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
