from pathlib import Path

PATH = Path(__file__).parent
DATA_DIR = PATH / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)