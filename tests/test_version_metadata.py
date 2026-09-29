from importlib.metadata import version

from mailo_cli import __version__
from mailo_cli.api import app


def test_release_version_is_consistent():
    assert __version__ == "0.5.0"
    assert app.version == __version__
    assert version("mailo-legal-ai-engine") == __version__
