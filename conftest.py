"""
Root conftest.py — ensures the project root is on sys.path so that
all package imports (core, algos, engine, ui, data) resolve correctly
when pytest is invoked from any working directory.
"""
import sys
import os

# Insert project root at the front of sys.path
sys.path.insert(0, os.path.dirname(__file__))
