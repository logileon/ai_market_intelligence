from datetime import date
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from market.storage import ROOT, connect
from market.steo import (SPECS, discover_releases, parse_workbook, ingest, read_steo, update_steo, aggregate, compare)

class STEOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vintages, cls.values = read_steo()
        cls.vintages = vintages
        cls.latest = vintages.iloc[0].to_dict()
        cls.release = {k:cls.latest[k] for k in ["release_month","released_at","source_url"]}
        cls.blob = (ROOT/"data"/cls.latest["raw_path"]).read_bytes()
        cls.record_count = len(parse_workbook(cls.blob,cls.release)[1])

    def test_archive_discovery_and_future_release(self):
        html = '''<table>
        <tr><td>October 2026</td><td>10/06/2026</td><td><a href="archives/oct26_base.xlsx">XLSX</a></td></tr>
        <tr><td>November 2026</td><td>11/10/2026</td><td><a href="archives/nov26_base.xlsx">XLSX</a></td></tr>
        <tr><td>September 2026</td><td>09/09/2026</td><td><a href="https://evil.invalid/sep26_base.xlsx">XLSX</a></td></tr>
        </table>'''
        releases = discover_releases(html, date(2026,10,24))
        self.assertEqual([x["release_month"] for x in releases],["2026-10"])
        with self.assertRaises(ValueError): discover_releases("<html>access denied</html>")

    def test_real_originals_provenance_and_balance(self):
        self.assertGreaterEqual(self.vintages.release_month.nunique(),7)
        for row in self.vintages.itertuples():
            blob = (ROOT/"data"/row.raw_path).read_bytes()
            self.assertEqual(sha256(blob).hexdigest(),row.sha256)
            release = dict(release_month=row.release_month,released_at=row.released_at,source_url=row.source_url)
            meta, records = parse_workbook(blob,release)
            self.assertEqual(meta["vintage_id"],row.vintage_id)
            self.assertEqual(len({r[1] for r in records}),len(SPECS))
            self.assertEqual(len(records),len(SPECS)*len({r[2] for r in records}))
            frame = pd.DataFrame(records,columns=["vintage_id","series","period","value","is_forecast","source_sheet","source_row","source_cell"])
            wide = frame.pivot(index="period",columns="series",values="value")
            self.assertLess((wide.papr_world-wide.patc_world+wide.t3_stchange_world).abs().max(),0.02)
            self.assertEqual(frame[frame.series=="BREPUUS"].iloc[0].source_cell,"C7")
            self.assertTrue((frame.is_forecast == (frame.period > meta["historical_cutoff"]).astype(int)).all())

    def test_wrong_vintage_rejected(self):
        bad = dict(self.release,release_month="2000-01")
        with self.assertRaises(ValueError): parse_workbook(self.blob,bad)

    def test_idempotent_ingestion_and_corrected_file_retention(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data") as d:
            db = Path(d)/"market.db"
            vid, n = ingest(self.blob,self.release,db)
            self.assertEqual(n,self.record_count)
            self.assertEqual(ingest(self.blob,self.release,db),(vid,0))
            # A byte-distinct valid ZIP represents a revised download, without changing test source values.
            other, n = ingest(self.blob+b"\n",self.release,db)
            self.assertNotEqual(other,vid)
            v, data = read_steo(db)
            self.assertEqual(len(v),2)
            self.assertEqual(len(data),2*self.record_count)
            self.assertTrue(all((Path(d)/r.raw_path).exists() for r in v.itertuples()))

    def test_outage_preserves_all_vintages(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data") as d:
            db = Path(d)/"market.db"
            ingest(self.blob,self.release,db)
            with patch("market.steo.get_bytes",side_effect=ConnectionError("offline")):
                results=update_steo(db)
            self.assertEqual(results[0]["status"],"error")
            v,data=read_steo(db)
            self.assertEqual(len(v),1); self.assertEqual(len(data),self.record_count)

    def test_monthly_cache_skips_old_downloads_and_refreshes_latest(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data") as d:
            db = Path(d)/"market.db"
            ingest(self.blob,self.release,db)
            with patch("market.steo.discover_releases",return_value=[self.release]), patch("market.steo.get_bytes",return_value=b"<html/>") as get:
                result=update_steo(db,refresh_latest=False)
            self.assertEqual(get.call_count,1)
            self.assertEqual(result[0]["items"],0)
            with patch("market.steo.discover_releases",return_value=[self.release]), patch("market.steo.get_bytes",side_effect=[b"<html/>",self.blob]) as get:
                result=update_steo(db)
            self.assertEqual(get.call_count,2)
            self.assertEqual(result[0]["status"],"ok")
            self.assertEqual(result[0]["items"],0)

    def test_aggregation_days_prices_cutoff_and_missing(self):
        rows=[]
        for code,vals in [("papr_world",[100,110,100]),("patc_world",[99,100,99]),("BREPUUS",[60,90,60])]:
            for month,value in zip(["2024-01","2024-02","2024-03"],vals):
                rows.append(dict(vintage_id="v",series=code,period=month,value=value,is_forecast=int(month>"2024-01")))
        f=pd.DataFrame(rows)
        q=aggregate(f,"Quarter").set_index("series")
        self.assertAlmostEqual(q.loc["papr_world","value"],(100*31+110*29+100*31)/91)
        self.assertEqual(q.loc["BREPUUS","value"],70)
        self.assertAlmostEqual(q.loc["balance","value"],q.loc["papr_world","value"]-q.loc["patc_world","value"])
        self.assertEqual(q.loc["papr_world","status"],"History + forecast")
        missing=aggregate(f[f.period!="2024-02"],"Quarter")
        self.assertTrue(missing.value.isna().all())
        self.assertTrue((missing.status=="Incomplete period").all())

    def test_comparison_outer_alignment_and_zero_base(self):
        a=pd.DataFrame([
            dict(vintage_id="new",series="balance",period="2027-01",value=1,status="EIA forecast"),
            dict(vintage_id="old",series="balance",period="2027-01",value=0,status="EIA forecast"),
            dict(vintage_id="new",series="balance",period="2027-02",value=2,status="EIA forecast")])
        c=compare(a,"new","old","balance").set_index("period")
        self.assertEqual(c.loc["2027-01","delta"],1)
        self.assertTrue(pd.isna(c.loc["2027-01","delta_pct"]))
        self.assertTrue(pd.isna(c.loc["2027-02","delta"]))

    def test_steo_ui_version_metric_and_frequency_controls(self):
        at=AppTest.from_file(str(ROOT/"app.py")).run(timeout=45)
        self.assertEqual(len(at.exception),0)
        self.assertTrue(any(t.label=="EIA balances & forecasts" for t in at.tabs))
        at.selectbox(key="steo_current").select(self.vintages.iloc[-1].vintage_id)
        at.selectbox(key="steo_frequency").select("Year")
        at.selectbox(key="steo_metric").select("patc_world")
        at.run(timeout=45)
        self.assertEqual(len(at.exception),0)
        self.assertEqual(at.selectbox(key="steo_current").value,self.vintages.iloc[-1].vintage_id)
        at.radio(key="steo_comparison_scope").set_value("Forecast periods in both vintages only").run(timeout=45)
        self.assertEqual(len(at.exception),0)

    def test_steo_ui_empty_archive(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data") as d:
            empty=read_steo(Path(d)/"empty.db")
            with patch("market.steo_ui.read_steo",return_value=empty):
                at=AppTest.from_file(str(ROOT/"app.py")).run(timeout=45)
                self.assertEqual(len(at.exception),0)
                self.assertTrue(any("STEO vintages are loaded" in x.value for x in at.info))

if __name__=="__main__": unittest.main()

