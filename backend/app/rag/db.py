import asyncio
import asyncpg
from pgvector.asyncpg import register_vector
from app.config import get_settings

settings = get_settings()

_pool: asyncpg.Pool | None = None


async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            min_size=2,
            max_size=10,
            init=init_connection,
        )
    return _pool


async def init_connection(conn: asyncpg.Connection):
    # Habilita el codec de pgvector para arrays de numpy / listas de floats
    await register_vector(conn)


async def init_db_schema():
    """Crea la extensión pgvector y la tabla de documentos de campaña si no existen."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS campaign_docs (
                id SERIAL PRIMARY KEY,
                drive_file_id TEXT NOT NULL,
                doc_title TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(384),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (drive_file_id, chunk_index)
            );
            """
        )
        # Índice HNSW para búsqueda por similitud coseno en menos de 5ms
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS campaign_docs_embedding_hnsw_idx
            ON campaign_docs USING hnsw (embedding vector_cosine_ops);
            """
        )
        print("[DB] Esquema y tabla de pgvector inicializados correctamente.")


async def close_db_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
