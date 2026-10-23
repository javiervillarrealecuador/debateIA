import asyncio
import base64
import io
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

from app.config import get_settings
from app.rag.db import get_db_pool, init_db_schema
from app.rag.retriever import compute_embedding

settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    """Inicializa el cliente de Google Drive API mediante Service Account."""
    creds = None
    # 1. Chequeo de credenciales en Base64 (ideal para Coolify/Docker Env)
    if settings.GOOGLE_SERVICE_ACCOUNT_B64:
        try:
            raw_json = base64.b64decode(settings.GOOGLE_SERVICE_ACCOUNT_B64).decode(
                "utf-8"
            )
            info = json.loads(raw_json)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        except Exception as e:
            print(f"[DRIVE] Error al decodificar GOOGLE_SERVICE_ACCOUNT_B64: {e}")

    # 2. Chequeo de archivo en disco
    if creds is None and os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
        try:
            creds = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES
            )
        except Exception as e:
            print(f"[DRIVE] Error cargando archivo de credenciales: {e}")

    if not creds:
        raise ValueError(
            "No se encontraron credenciales válidas de Google Drive (archivo o base64)."
        )

    return build("drive", "v3", credentials=creds)


def chunk_text(
    text: str, chunk_size: int = 500, overlap: int = 80
) -> List[str]:
    """Divide el texto en fragmentos solapados optimizados para búsqueda de datos y cifras."""
    cleaned = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(cleaned):
        end = start + chunk_size
        chunk = cleaned[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


def extract_text_from_bytes(content_bytes: bytes, mime_type: str) -> str:
    """Extrae texto plano de archivos PDF o Markdown/Texto."""
    if "pdf" in mime_type:
        reader = PdfReader(io.BytesIO(content_bytes))
        full_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                full_text.append(t)
        return "\n".join(full_text)
    else:
        # Markdown, TXT, CSV
        return content_bytes.decode("utf-8", errors="ignore")


async def sync_google_drive_folder():
    """
    Escanea la carpeta de Google Drive configurada, descarga documentos de campaña,
    los fragmenta, calcula embeddings vectoriales y los sincroniza en PostgreSQL con pgvector.
    """
    if not settings.GOOGLE_DRIVE_FOLDER_ID:
        print("[DRIVE] GOOGLE_DRIVE_FOLDER_ID no configurado. Omitiendo sincronización.")
        return

    print(f"[*] Iniciando sincronización de Drive (Carpeta: {settings.GOOGLE_DRIVE_FOLDER_ID})...")
    service = get_drive_service()

    # Listar archivos no eliminados dentro de la carpeta
    query = f"'{settings.GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false"
    results = (
        service.files()
        .list(q=query, fields="files(id, name, mimeType, modifiedTime)")
        .execute()
    )
    files = results.get("files", [])
    print(f"[*] Archivos encontrados en Google Drive: {len(files)}")

    pool = await get_db_pool()

    for f in files:
        file_id = f["id"]
        name = f["name"]
        mime_type = f["mimeType"]

        print(f"[*] Procesando: '{name}' (ID: {file_id}, Tipo: {mime_type})")

        try:
            # Descarga de contenido según el tipo de archivo de Drive
            if mime_type == "application/vnd.google-apps.document":
                request = service.files().export_media(
                    fileId=file_id, mimeType="text/plain"
                )
            else:
                request = service.files().get_media(fileId=file_id)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            raw_bytes = fh.getvalue()
            text = extract_text_from_bytes(raw_bytes, mime_type)

            chunks = chunk_text(text)
            print(f"   -> Extraídos {len(chunks)} fragmentos.")

            # Limpiar chunks anteriores de este documento para evitar duplicados
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM campaign_docs WHERE drive_file_id = $1;", file_id
                )

                # Insertar nuevos chunks con embeddings
                for idx, chunk in enumerate(chunks):
                    emb = compute_embedding(chunk)
                    await conn.execute(
                        """
                        INSERT INTO campaign_docs (drive_file_id, doc_title, chunk_index, content, embedding)
                        VALUES ($1, $2, $3, $4, $5);
                        """,
                        file_id,
                        name,
                        idx,
                        chunk,
                        emb,
                    )
            print(f"   [OK] '{name}' indexado con éxito en pgvector.")

        except Exception as e:
            print(f"[ERROR] Error al procesar archivo '{name}': {e}", file=sys.stderr)


if __name__ == "__main__":
    async def main():
        await init_db_schema()
        await sync_google_drive_folder()

    asyncio.run(main())
