# debateIA - Asistente de Debate Político en Tiempo Real (< 2.5s Latency)

Sistema de teleprompter e inteligencia artificial para debates electorales y entrevistas en vivo.

## Arquitectura del Monorepo

```text
debateIA/
├── docker-compose.yml              # Configuración multicontenedor para Coolify / Hetzner
├── .env.example                    # Plantilla de variables de entorno
├── scripts/
│   ├── enroll_candidate.py         # Calibración de voz (15s audio -> candidate_profile.npy)
│   └── test_client_mic.py          # Cliente CLI para testear WebSocket y envío de PCM
├── backend/
│   ├── Dockerfile                  # Imagen optimizada CPU (PyTorch + CTranslate2)
│   ├── requirements.txt            # Dependencias Python 3.11+
│   └── app/
│       ├── config.py               # Settings con Pydantic BaseSettings
│       ├── main.py                 # FastAPI + WebSocket /ws/audio + Pipeline reactivo
│       ├── audio/
│       │   ├── vad.py              # Silero VAD (ONNX / Torch)
│       │   ├── diarizer.py         # Resemblyzer para similitud de voz
│       │   └── transcriber.py      # faster-whisper INT8
│       ├── rag/
│       │   ├── db.py               # Conexión asyncpg / PostgreSQL con pgvector
│       │   ├── drive_sync.py       # Sync Google Drive -> Chunks -> Embeddings -> pgvector
│       │   ├── retriever.py        # Búsqueda semántica HNSW pgvector
│       │   └── web_search.py       # Tavily / Brave Search API asíncrono
│       └── llm/
│           ├── filter.py           # Filtro léxico/heurístico ultrarrápido de afirmaciones
│           └── deepseek_client.py  # Streaming DeepSeek V3 con prompt telegráfico
└── frontend/
    ├── Dockerfile                  # Next.js standalone multistage
    ├── package.json
    ├── next.config.mjs
    ├── tailwind.config.ts
    ├── public/
    │   └── manifest.json           # Configuración PWA
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx            # Teleprompter oscuro de alto contraste
        │   └── globals.css
        ├── components/
        │   ├── AudioStreamer.tsx   # Captura AudioWorklet 16kHz PCM en vivo
        │   ├── TeleprompterCard.tsx # Tarjetas de réplica en streaming
        │   └── StatusHeader.tsx    # Métricas de latencia y estado de conexión
        └── hooks/
            └── useDebateSocket.ts  # Gestión de WebSocket y buffering de réplicas
```
