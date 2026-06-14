import logging
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent

INDUSTRY = os.getenv("INDUSTRY", "manufacturing")
LEARNER_SCHEMA = os.getenv("LEARNER_SCHEMA", "learner_03")
DB_URL = os.getenv("DB_URL", "")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = PROJECT_ROOT / "sql"

RAW_DATA_PATH = RAW_DATA_DIR / "raw-data.csv"
PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / "processed-data.csv"

MAX_NULL_PERCENT = float(os.getenv("MAX_NULL_PERCENT", "50.0"))
MAX_DUPLICATE_PERCENT = float(os.getenv("MAX_DUPLICATE_PERCENT", "5.0"))

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR.mkdir(parents=True, exist_ok=True)


def build_logger(name: str = "manufacturing_etl") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


logger = build_logger()
engine = None

if DB_URL:
    try:
        from sqlalchemy import create_engine

        engine = create_engine(DB_URL, pool_pre_ping=True)
    except Exception as exc:
        logger.warning("Database engine was not created: %s", exc)
