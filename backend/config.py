from pathlib import Path
import dotenv

dotenv.load_dotenv()
import os
ENV = os.getenv('ENV')

PATH = Path(__file__).parent
DATA_DIR = PATH / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)