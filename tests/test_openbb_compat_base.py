import pytest
from datetime import date, datetime
from src.data.openbb_compat.base import (
    StandardQuery,
    StandardData,
    ProviderAdapter,
    EmptyDataError,
    AnnotatedResult,
)
from src.data.openbb_compat.registry import Registry, RegistryLoader

class DummyQuery(StandardQuery):
    pass

class DummyData(StandardData):
    value: float

class DummyAdapter(ProviderAdapter[DummyQuery, DummyData]):
    def to_query(self, params: dict) -> DummyQuery:
        return DummyQuery(**params)

    def fetch(self, query: DummyQuery, creds: dict | None = None) -> list:
        return [{"date": "2023-01-01", "value": 10.0}]

    def to_records(self, query: DummyQuery, raw: list) -> list[DummyData]:
        if not raw:
            raise EmptyDataError("No data found")
        return [DummyData(**r) for r in raw]

def test_standard_query_uppercase():
    query = StandardQuery(symbol="aapl")
    assert query.symbol == "AAPL"

def test_standard_data_date_parsing():
    d1 = StandardData(date="2023-01-01")
    assert d1.date == date(2023, 1, 1)

    d2 = StandardData(date=datetime(2023, 1, 1, 12, 0))
    assert d2.date == date(2023, 1, 1)

    d3 = StandardData(date=date(2023, 1, 1))
    assert d3.date == date(2023, 1, 1)

    with pytest.raises(ValueError):
         StandardData(date="invalid-date")

def test_provider_adapter_not_implemented():
    class IncompleteAdapter(ProviderAdapter):
        pass

    adapter = IncompleteAdapter()

    with pytest.raises(NotImplementedError):
        adapter.to_query({})

    with pytest.raises(NotImplementedError):
        adapter.fetch(StandardQuery(symbol="AAPL"))

    with pytest.raises(NotImplementedError):
        adapter.to_records(StandardQuery(symbol="AAPL"), [])

def test_dummy_adapter_flow():
    adapter = DummyAdapter()
    query = adapter.to_query({"symbol": "msft"})
    assert query.symbol == "MSFT"

    raw = adapter.fetch(query)
    records = adapter.to_records(query, raw)

    assert len(records) == 1
    assert records[0].date == date(2023, 1, 1)
    assert records[0].value == 10.0

    with pytest.raises(EmptyDataError):
        adapter.to_records(query, [])

def test_annotated_result():
    res = AnnotatedResult([DummyData(date="2023-01-01", value=10.0)], metadata={"source": "test"})
    assert len(res.results) == 1
    assert res.metadata["source"] == "test"

def test_registry():
    registry = Registry.default()
    adapter = DummyAdapter()

    registry.include("dummy", adapter)
    assert registry.get("dummy") == adapter

    with pytest.raises(KeyError):
        registry.get("nonexistent")

def test_registry_loader():
    registry = RegistryLoader.from_entrypoints()
    assert isinstance(registry, Registry)
