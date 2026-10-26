import unittest
from unittest.mock import patch, Mock
import pandas as pd
import plotly.express as px
from market.refining import crack_series, chronology, scenario_balance
from market.newsapi import parse_articles, fetch_newsapi
from market.analysis import analyze
from market.storage import ROOT
from streamlit.testing.v1 import AppTest

class ResearchTests(unittest.TestCase):
    def prices(self):
        rows=[]
        for date, vals in [('2026-01-02', {'DCOILWTICO':70,'DCOILBRENTEU':75,'DGASUSGULF':2,'DDFUELUSGULF':3}),
                           ('2026-01-03', {'DCOILWTICO':71,'DGASUSGULF':2.1})]:
            rows += [dict(date=date,series=k,value=v) for k,v in vals.items()]
        return pd.DataFrame(rows)

    def test_crack_units_yields_and_missing_dates(self):
        cracks=crack_series(self.prices())
        first=cracks[cracks.date == pd.Timestamp('2026-01-02',tz='UTC')].set_index('spread')
        self.assertEqual(first.loc['Gasoline crack','value'],14)
        self.assertEqual(first.loc['ULSD crack','value'],56)
        self.assertEqual(first.loc['3:2:1','value'],28)
        self.assertEqual(len(cracks[cracks.spread == '3:2:1']),1)
        brent=crack_series(self.prices(),'DCOILBRENTEU').set_index('spread')
        self.assertEqual(brent.loc['3:2:1','value'],23)
        self.assertTrue(crack_series(pd.DataFrame()).empty)

    def test_signed_periods_always_chronological(self):
        df=pd.DataFrame({'period':['2026Q1','2026Q2','2026Q3','2026Q4'],'value':[-1,2,-3,4], 'sign':['-','+','-','+']})
        fig=chronology(px.bar(df,x='period',y='value',color='sign'),df.period)
        self.assertEqual(list(fig.layout.xaxis.categoryarray),df.period.tolist())
        self.assertEqual(fig.layout.xaxis.categoryorder,'array')

    def test_scenario_signs_and_volumes(self):
        self.assertEqual(scenario_balance(105,104,-2,0,91),(-1,-91))
        self.assertEqual(scenario_balance(105,104,0,-1,90),(2,180))

    def test_newsapi_metadata_dates_and_rss_dedup_id(self):
        item={'title':'Diesel refinery outage','description':'ULSD supply disruption', 'url':'https://example.org/a?utm_source=test','source':{'name':'Publisher'},'publishedAt':'2026-01-01T10:00:00Z'}
        rows=parse_articles({'status':'ok','articles':[item]},'2026-01-02T10:00:00+00:00')
        self.assertEqual(rows[0]['published_at'],'2026-01-01T10:00:00+00:00')
        self.assertEqual(rows[0]['url'],'https://example.org/a')
        self.assertIn('Diesel & gasoil',rows[0]['topics'])
        item['publishedAt']='not a date'
        self.assertIsNone(parse_articles({'status':'ok','articles':[item]},'2026-01-02T10:00:00+00:00')[0]['published_at'])
        with self.assertRaises(ValueError): parse_articles({'status':'error'},'2026-01-02T10:00:00+00:00')

    def test_newsapi_header_and_safe_failure(self):
        response=Mock(status_code=200)
        response.json.return_value={'status':'ok','articles':[]}
        with patch('market.newsapi.requests.get',return_value=response) as get:
            self.assertIsNone(fetch_newsapi('2026-01-02T10:00:00+00:00',key='test-secret')[2])
            self.assertEqual(get.call_count,1)
            self.assertEqual(get.call_args.kwargs['headers']['X-Api-Key'],'test-secret')
            self.assertNotIn('apiKey',get.call_args.kwargs['params'])
        with patch('market.newsapi.requests.get',side_effect=Exception('test-secret')):
            self.assertNotIn('test-secret',fetch_newsapi('2026-01-02T10:00:00+00:00',key='test-secret')[2])
        with patch.dict('os.environ',{},clear=True):
            self.assertEqual(fetch_newsapi('2026-01-02T10:00:00+00:00')[1],[])

    def test_topics_separate_products(self):
        self.assertIn('Jet fuel',analyze('Jet fuel demand')['topics'])
        self.assertNotIn('Diesel & gasoil',analyze('Jet fuel demand')['topics'])
        self.assertIn('Fuel oil & bunkers',analyze('Fuel oil bunker')['topics'])

    def test_refining_and_scenario_controls(self):
        at=AppTest.from_file(str(ROOT/'app.py')).run(timeout=60)
        self.assertEqual(len(at.exception),0)
        next(x for x in at.selectbox if x.label=='Crude benchmark').select('DCOILBRENTEU').run(timeout=60)
        self.assertEqual(len(at.exception),0)
        next(x for x in at.slider if x.label.startswith('Supply shock')).set_value(-1.0).run(timeout=60)
        self.assertEqual(len(at.exception),0)
        self.assertTrue(any(x.label=='Scenario balance' for x in at.metric))

if __name__=='__main__': unittest.main()
