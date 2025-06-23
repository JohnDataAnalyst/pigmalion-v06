from fastapi.testclient import TestClient
import backend.main as main

client = TestClient(main.app)

def test_keywords_invalid_category():
    resp = client.get('/trends/keywords?period=today&category=unknown')
    assert resp.status_code == 400


def test_keywords_success(monkeypatch):
    def fake_conn():
        class DummyCursor:
            def execute(self, sql, params):
                self.sql = sql
            def fetchall(self):
                return [('alpha', 3), ('beta', 2)]
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                pass
        class DummyConnection:
            def cursor(self):
                return DummyCursor()
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                pass
        return DummyConnection()

    monkeypatch.setattr(main, 'get_connection', fake_conn)
    resp = client.get('/trends/keywords?period=today&category=health_fitness&limit=2')
    assert resp.status_code == 200
    assert resp.json() == [
        {'rank': 1, 'keyword': 'alpha', 'occurrence': 3},
        {'rank': 2, 'keyword': 'beta', 'occurrence': 2},
    ]
