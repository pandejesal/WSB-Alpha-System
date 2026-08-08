import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.execution.execution_adapter import PaperbrokerClient, ExecutionAdapter

class DummyResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.text = "Dummy Error"
    def json(self):
        return self.json_data
    def raise_for_status(self):
        if self.status_code >= 400:
            from requests.exceptions import HTTPError
            raise HTTPError("HTTP Error")

class MockRequests:
    def __init__(self):
        self.last_post_kwargs = None
    def post(self, url, json=None, headers=None):
        self.last_post_kwargs = {'url': url, 'json': json, 'headers': headers}
        return DummyResponse({"status": "success", "order_id": 123}, 200)

import requests
requests.post = MockRequests().post

class TestExecutionAdapter(unittest.TestCase):
    def test_order_payload_generation(self):
        client = PaperbrokerClient(base_url="http://dummy")

        def mock_post(url, json=None, headers=None, timeout=None):
            self.assertEqual(json['ticker'], "AAPL")
            self.assertEqual(json['side'], "BUY")
            self.assertEqual(json['quantity'], 10)
            self.assertEqual(json['order_type'], "MARKET")
            self.assertEqual(json['target_cvar_allocation'], 0.05)
            return DummyResponse({"status": "success"}, 200)

        requests.post = mock_post

        result = client.place_order("AAPL", 10, "BUY", "MARKET", 0.05)
        self.assertEqual(result["status"], "success")

if __name__ == '__main__':
    unittest.main()
