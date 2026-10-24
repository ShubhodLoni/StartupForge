import os
import uuid

import pytest

from app.db import Database, PgReportStore, PgVectorIndex
from app.rag import Chunk, HashEmbedder, RunRetriever

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
async def db():
    database = Database(URL, dim=384)
    await database.open()
    created = {"reports": [], "runs": []}
    database.created = created
    yield database
    await database.run(lambda conn: conn.execute("delete from reports where id = any(%s::uuid[])", (created["reports"],)))
    await database.run(lambda conn: conn.execute("delete from chunks where run_id = any(%s::uuid[])", (created["runs"],)))
    await database.close()


def chunk(url, text, kind="market"):
    return Chunk(url=url, title=url, kind=kind, query="q", chunk_index=0, text=text)


async def test_pgvector_search_ranks_and_scopes(db):
    index, emb = PgVectorIndex(db), HashEmbedder()
    run, other = str(uuid.uuid4()), str(uuid.uuid4())
    db.created["runs"] += [run, other]
    await RunRetriever(index, emb, run).index_chunks(
        [
            chunk("https://a.org", "pricing plans per month subscription"),
            chunk("https://b.org", "dental clinics miss phone calls", kind="competitor"),
            chunk("https://c.org", "weather in paris today"),
        ]
    )
    await RunRetriever(index, emb, other).index_chunks([chunk("https://z.org", "dental clinics miss phone calls")])

    retriever = RunRetriever(index, emb, run)
    top = await retriever.retrieve("why do dental clinics miss calls", k=2)
    assert top[0].url == "https://b.org"
    assert all(c.url != "https://z.org" for c in top)
    assert [c.url for c in await retriever.retrieve("calls", 5, kinds=["competitor"])] == ["https://b.org"]


async def test_report_store_roundtrip(db):
    store = PgReportStore(db)
    rid = str(uuid.uuid4())
    db.created["reports"].append(rid)
    report = {
        "id": rid,
        "generated_at": "2026-10-24T12:00:00+00:00",
        "request": {"idea": "Test idea for storage"},
        "report": {"title": "StoreTest"},
        "finance": {"assumptions": {"price_per_month": 10}},
    }
    await store.save(report)
    assert await store.get(rid) == report

    report["finance"]["assumptions"]["price_per_month"] = 20
    await store.save(report)
    assert (await store.get(rid))["finance"]["assumptions"]["price_per_month"] == 20

    listed = await store.list(100)
    assert any(r["id"] == rid and r["title"] == "StoreTest" for r in listed)
    assert await store.get("not-a-uuid") is None
    assert await store.get(str(uuid.uuid4())) is None
