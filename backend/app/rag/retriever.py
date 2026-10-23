import asyncio
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from app.rag.db import get_db_pool

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        print("[EMBEDDINGS] Cargando all-MiniLM-L6-v2 en CPU...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _embedder


def compute_embedding(text: str) -> np.ndarray:
    """Genera vector de 384 dimensiones normalizado L2."""
    model = get_embedder()
    emb = model.encode(text, normalize_embeddings=True)
    return np.array(emb, dtype=np.float32)


async def search_campaign_docs(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Búsqueda semántica HNSW en PostgreSQL / pgvector para documentos internos de campaña.
    Latencia promedio estimada: 15-30ms.
    """
    try:
        loop = asyncio.get_running_loop()
        query_vector = await loop.run_in_executor(None, compute_embedding, query)

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Operador <=> calcula distancia coseno en pgvector
            rows = await conn.fetch(
                """
                SELECT doc_title, content, (1 - (embedding <=> $1)) as similarity
                FROM campaign_docs
                ORDER BY embedding <=> $1
                LIMIT $2;
                """,
                query_vector,
                top_k,
            )

            results = []
            for row in rows:
                if row["similarity"] >= 0.35:  # Filtro de relevancia mínima
                    results.append(
                        {
                            "source": row["doc_title"],
                            "content": row["content"],
                            "similarity": float(row["similarity"]),
                        }
                    )
            return results
    except Exception as e:
        print(f"[RAG] Error en búsqueda de pgvector: {e}")
        return []
