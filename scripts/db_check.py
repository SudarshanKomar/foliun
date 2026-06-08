import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from foliun.config import get_settings

engine = create_engine(get_settings().database_url)
with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).scalar())
