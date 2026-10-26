from contextlib import contextmanager
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "market.db"

@contextmanager
def connect(path=DB):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def initialize(path=DB):
    with connect(path) as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS news (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL, source TEXT NOT NULL,
          published_at TEXT, fetched_at TEXT NOT NULL, summary TEXT, topics TEXT, regions TEXT,
          signal TEXT, evidence TEXT);
        CREATE INDEX IF NOT EXISTS idx_news_date ON news(published_at);
        CREATE TABLE IF NOT EXISTS prices (
          date TEXT NOT NULL, value REAL NOT NULL, series TEXT NOT NULL, source TEXT NOT NULL,
          PRIMARY KEY(date, series));
        CREATE TABLE IF NOT EXISTS runs (
          started_at TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL,
          items INTEGER NOT NULL, detail TEXT NOT NULL);
        ''')

def save_news(rows, path=DB):
    with connect(path) as con:
        before = con.total_changes
        con.executemany('''INSERT OR IGNORE INTO news VALUES
        (:id,:title,:url,:source,:published_at,:fetched_at,:summary,:topics,:regions,:signal,:evidence)''', rows)
        return con.total_changes - before

def log_run(now, source, status, items, detail, path=DB):
    with connect(path) as con:
        con.execute("INSERT INTO runs VALUES (?,?,?,?,?)", (now, source, status, items, detail[:500]))
        con.execute("DELETE FROM runs WHERE rowid NOT IN (SELECT rowid FROM runs ORDER BY rowid DESC LIMIT 1000)")

def read_tables(path=DB):
    initialize(path)
    with connect(path) as con:
        return tuple(pd.read_sql_query(q, con) for q in (
            "SELECT * FROM news ORDER BY COALESCE(published_at,fetched_at) DESC",
            "SELECT * FROM prices ORDER BY date",
            "SELECT * FROM runs ORDER BY rowid DESC LIMIT 100"))
