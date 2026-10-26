"""Integration checks for display-only intraday oil, without live network requests."""
import json
import re
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from market.storage import ROOT
from market.intraday import chart_html, ticker_html, INSTRUMENTS

class IntradayTests(unittest.TestCase):
    def test_chart_inputs_are_explicit_and_source_attributed(self):
        for benchmark,symbol in [('WTI','TVC:USOIL'),('Brent','TVC:UKOIL')]:
            html=chart_html(benchmark,'15')
            match=re.search(r'<script[^>]+async>(.*?)</script>',html,re.S)
            config=json.loads(match.group(1))
            self.assertEqual(config['symbol'],symbol)
            self.assertEqual(config['interval'],'15')
            self.assertEqual(config['timezone'],'Etc/UTC')
            self.assertEqual(config['locale'],'en')
            self.assertIn('by TradingView',html)
            self.assertIn(INSTRUMENTS[benchmark]['url'],html)
        with self.assertRaises(ValueError):chart_html('WTI','unsupported')
        self.assertNotEqual(chart_html('WTI',nonce=0),chart_html('WTI',nonce=1))
        self.assertIn('TVC:UKOIL',ticker_html())

    def test_intraday_controls_do_not_request_or_store_prices(self):
        # Streamlit emits HTML; price subscriptions happen in the browser only.
        with patch('requests.get',side_effect=AssertionError('unexpected server quote request')):
            at=AppTest.from_file(str(ROOT/'app.py')).run(timeout=90)
            self.assertEqual(len(at.exception),0)
            self.assertTrue(any(t.label=='Intraday oil' for t in at.tabs))
            at.radio(key='oil_chart_layout').set_value('Single chart').run(timeout=90)
            at.selectbox(key='oil_benchmark').select('Brent')
            at.selectbox(key='oil_candle_interval').select('15 minutes').run(timeout=90)
            self.assertEqual(len(at.exception),0)
            old=at.session_state['oil_feed_nonce'] if 'oil_feed_nonce' in at.session_state else 0
            at.button(key='oil_reconnect').click().run(timeout=90)
            self.assertEqual(at.session_state['oil_feed_nonce'],old+1)
            self.assertEqual(len(at.exception),0)

if __name__=='__main__':unittest.main()
