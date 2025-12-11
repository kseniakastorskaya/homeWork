import subprocess
import tempfile
import sys
from pathlib import Path

TOOL = Path("config_tool.py")


def test_import():
    __import__("config_tool")


def test_assemble_examples():
    examples = [
        "examples/webserver.cfg",
        "examples/database.cfg",
        "examples/experiment.cfg",
    ]
    for ex in examples:
        out = tempfile.NamedTemporaryFile(suffix=".yml", delete=False)
        r = subprocess.run(
            [sys.executable, str(TOOL), "assemble", ex, out.name, "--test"],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
