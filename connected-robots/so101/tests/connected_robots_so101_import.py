import importlib.util
from pathlib import Path


def load_bridge():
    source = Path(__file__).parents[1] / "follower_bridge.py"
    spec = importlib.util.spec_from_file_location("so101_follower_bridge", source)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module
