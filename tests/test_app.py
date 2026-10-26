from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from market.storage import ROOT, initialize, read_tables, save_news, connect
from market.collect import parse_feed
from test_pipeline import RSS, NOW

class AppTests(unittest.TestCase):
    def test_app_with_empty_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            tables = read_tables(Path(d)/"empty.db")
            with patch("market.storage.read_tables", return_value=tables):
                at = AppTest.from_file(str(ROOT/"app.py")).run(timeout=60)
                self.assertEqual(len(at.exception), 0)

    def test_app_populated_and_search(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d)/"test.db"; initialize(db)
            save_news(parse_feed(RSS, "Fixture", NOW), db)
            with connect(db) as con:
                for code, value in [("DCOILBRENTEU", 75), ("DCOILWTICO", 70), ("DGASNYH", 2.3), ("DHOILNYH", 2.5), ("DDFUELUSGULF", 2.6)]:
                    con.execute("INSERT INTO prices VALUES (?,?,?,?)", (NOW[:10], value, code, "https://fred.stlouisfed.org"))
            tables = read_tables(db)
            with patch("market.storage.read_tables", return_value=tables):
                at = AppTest.from_file(str(ROOT/"app.py")).run(timeout=60)
                self.assertEqual(len(at.exception), 0)
                # Select full history so the dated fixture is included.
                next(box for box in at.selectbox if box.label == "News lookback (days)").select("All history").run(timeout=60)
                self.assertEqual(at.metric[0].value, "1")
                at.text_input[0].set_value("no-match-xyz").run(timeout=60)
                self.assertEqual(len(at.exception), 0)
                self.assertEqual(at.metric[0].value, "0")

if __name__ == "__main__": unittest.main()
