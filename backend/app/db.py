import asyncio
import json
import logging
import uuid

from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.rag import Chunk

logger = logging.getLogger("startupforge")


def schema_sql(dim: int) -> str:
    return f"""
create table if not exists reports (
    id uuid primary key,
    title text not null,
    idea text not null,
    created_at timestamptz not null,
    data jsonb not null
);
create index if not exists reports_created_idx on reports (created_at desc);

create table if not exists chunks (
    id bigserial primary key,
    run_id uuid not null,
    url text not null,
    title text not null,
    kind text not null,
    query text not null,
    published_date text,
    chunk_index int not null,
    content text not null,
    embedding vector({dim}) not null
);
create index if not exists chunks_run_idx on chunks (run_id);
"""


class Database:
    def __init__(self, url: str, dim: int = 384):
        self.url, self.dim = url, dim
        self.pool: ConnectionPool | None = None

    def _open(self):
        import psycopg

        with psycopg.connect(self.url, autocommit=True) as conn:
            conn.execute("create extension if not exists vector")
        self.pool = ConnectionPool(self.url, min_size=1, max_size=5, configure=register_vector, open=True)
        with self.pool.connection() as conn:
            conn.execute(schema_sql(self.dim))

    async def open(self):
        await asyncio.to_thread(self._open)
        logger.info("Connected to PostgreSQL")

    async def close(self):
        if self.pool:
            await asyncio.to_thread(self.pool.close)

    async def run(self, fn):
        def task():
            with self.pool.connection() as conn:
                return fn(conn)

        return await asyncio.to_thread(task)


class PgVectorIndex:
    def __init__(self, db: Database):
        self.db = db

    async def add(self, run_id, chunks: list[Chunk], vectors):
        import numpy as np

        def fn(conn):
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into chunks (run_id, url, title, kind, query, published_date, chunk_index, content, embedding)"
                    " values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        (run_id, c.url, c.title, c.kind, c.query, c.published_date, c.chunk_index, c.text, np.array(v, dtype=np.float32))
                        for c, v in zip(chunks, vectors)
                    ],
                )

        await self.db.run(fn)

    async def search(self, run_id, vector, k, kinds=None):
        import numpy as np

        def fn(conn):
            sql = (
                "select url, title, kind, query, published_date, chunk_index, content from chunks"
                " where run_id = %s and (%s::text[] is null or kind = any(%s::text[]))"
                " order by embedding <=> %s limit %s"
            )
            rows = conn.execute(sql, (run_id, kinds, kinds, np.array(vector, dtype=np.float32), k)).fetchall()
            return [
                Chunk(url=r[0], title=r[1], kind=r[2], query=r[3], published_date=r[4], chunk_index=r[5], text=r[6])
                for r in rows
            ]

        return await self.db.run(fn)


class PgReportStore:
    def __init__(self, db: Database):
        self.db = db

    async def save(self, report: dict) -> None:
        def fn(conn):
            conn.execute(
                "insert into reports (id, title, idea, created_at, data) values (%s, %s, %s, %s, %s)"
                " on conflict (id) do update set title = excluded.title, data = excluded.data",
                (report["id"], report["report"]["title"], report["request"]["idea"], report["generated_at"], Jsonb(report)),
            )

        await self.db.run(fn)

    async def get(self, report_id: str) -> dict | None:
        try:
            uuid.UUID(report_id)
        except ValueError:
            return None

        def fn(conn):
            row = conn.execute("select data from reports where id = %s", (report_id,)).fetchone()
            return row[0] if row else None

        return await self.db.run(fn)

    async def list(self, limit: int = 20) -> list[dict]:
        def fn(conn):
            rows = conn.execute(
                "select id::text, title, idea, created_at from reports order by created_at desc limit %s", (limit,)
            ).fetchall()
            return [{"id": r[0], "title": r[1], "idea": r[2], "generated_at": r[3].isoformat()} for r in rows]

        return await self.db.run(fn)


class MemoryReportStore:
    def __init__(self):
        self._reports: dict[str, dict] = {}

    async def save(self, report: dict) -> None:
        self._reports[report["id"]] = json.loads(json.dumps(report, default=str))

    async def get(self, report_id: str) -> dict | None:
        return self._reports.get(report_id)

    async def list(self, limit: int = 20) -> list[dict]:
        items = sorted(self._reports.values(), key=lambda r: r["generated_at"], reverse=True)[:limit]
        return [
            {"id": r["id"], "title": r["report"]["title"], "idea": r["request"]["idea"], "generated_at": r["generated_at"]}
            for r in items
        ]
