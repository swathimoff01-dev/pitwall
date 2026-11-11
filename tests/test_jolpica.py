import pytest

from pitwall.ingest_jolpica import parse_duration
from pitwall.jolpica import JolpicaClient


def test_parse_duration_seconds():
    assert parse_duration("23.456") == pytest.approx(23.456)


def test_parse_duration_over_a_minute():
    assert parse_duration("1:02.345") == pytest.approx(62.345)


class FakeClient(JolpicaClient):
    def __init__(self):  # no network, no cache folder
        self.offsets = []

    def get(self, path, season=None, offset=0):
        self.offsets.append(offset)
        return {"MRData": {"limit": "100", "total": "250", "offset": str(offset)}}


def test_pages_walks_every_offset():
    client = FakeClient()
    assert len(list(client.pages("2024/results/", 2024))) == 3
    assert client.offsets == [0, 100, 200]

def test_parse_duration_missing():
    assert parse_duration("") is None
    assert parse_duration(None) is None