import sqlite3

from src.extractor import read_sqlite_db

class DummyCursor:
    def execute(self, *args, **kwargs):
        raise sqlite3.Error("boom")

    def fetchall(self):
        return []

class DummyConnection:
    def __init__(self):
        self.closed = False
    def cursor(self):
        return DummyCursor()
    def close(self):
        self.closed = True


def test_read_sqlite_db_closes_on_error(monkeypatch):
    dummy_conn = DummyConnection()
    def dummy_connect(path):
        return dummy_conn
    monkeypatch.setattr(sqlite3, 'connect', dummy_connect)

    result = read_sqlite_db('dummy')

    assert result is None
    assert dummy_conn.closed
