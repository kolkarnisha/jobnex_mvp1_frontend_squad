import os
from pathlib import Path
import mysql.connector

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


def get_connection():
     return mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="Njz@221027",
            database="jobnex",
        )