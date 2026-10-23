import asyncio
import io
import time
import numpy as np
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.audio.vad import SileroVADDetector
from app.audio.diarizer import SpeakerClassifier
from app.audio.transcriber import FastTranscriber
from app.llm.filter import evaluate_claim_trigger
from app.rag.db import init_db_schema, close_db_pool
from app.rag.retriever import search_campaign_docs
from app.rag.web_search import search_live_web
from app.llm.deepseek_client import stream_deepseek_rebuttal

settings = get_settings()

# Instancias compartidas de modelos (Cargados una sola vez en el ciclo de vida del servidor)
vad_detector: SileroVADDetector | None = None
diarizer: SpeakerClassifier | None = None
transcriber: FastTranscriber | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vad_detector, diarizer, transcriber
    print("[INICIALIZACIÓN] Cargando componentes de Machine Learning e Inteligencia Factual...")
    vad_detector = SileroVADDetector(threshold=settings.VAD_THRESHOLD)
    diarizer = SpeakerClassifier(
        profile_path=settings.CANDIDATE_PROFILE_PATH,
        threshold=settings.SPEAKER_SIMILARITY_THRESHOLD,
    )
    transcriber = FastTranscriber(
        model_size=settings.WHISPER_MODEL_SIZE,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )
    try:
        await init_db_schema()
    except Exception as e:
        print(f"[DB] Advertencia al conectar con PostgreSQL: {e}")

    print("[INICIALIZACIÓN] Sistema listo para transmisión en vivo.")
    yield

    print("[CIERRE] Liberando conexiones...")
    await close_db_pool()


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "vad_loaded": vad_detector is not None,
        "diarizer_loaded": diarizer is not None,
        "candidate_calibrated": diarizer.candidate_profile is not None if diarizer else False,
        "transcriber_loaded": transcriber is not None,
    }


async def process_utterance(
    audio_data: np.ndarray,
    websocket: WebSocket,
    utterance_start_time: float,
):
    """
    Procesa un bloque de habla completa detectado por Silero VAD:
    1. Diarización y Clasificación (Candidato vs Oponente)
    2. Transcripción con faster-whisper INT8
    3. Si habla el oponente:
       - Filtro de afirmaciones / cifras
       - Búsqueda en paralelo (pgvector + Tavily/Brave)
       - Generación en streaming ultra-corto vía DeepSeek V3
    """
    global diarizer, transcriber
    loop = asyncio.get_running_loop()

    # 1. Diarización (Similitud coseno contra perfil del candidato)
    speaker, similarity = await loop.run_in_executor(
        None, diarizer.classify, audio_data
    )

    # 2. Transcripción en CPU optimizada
    text = await loop.run_in_executor(None, transcriber.transcribe, audio_data)
    if not text or len(text.strip()) < 2:
        return

    # Notificar transcripción inmediata a la PWA
    await websocket.send_json(
        {
            "type": "transcription",
            "speaker": speaker,
            "confidence": similarity,
            "text": text,
            "timestamp": time.time(),
        }
    )

    # Si es el candidato quien habla, no se requiere refutación inmediata
    if speaker == "candidate":
        return

    # 3. Filtro léxico/factual: Comprobar si requiere réplica
    is_claim, reason = evaluate_claim_trigger(text)
    if not is_claim:
        return

    # Alerta visual en teleprompter mientras se ejecuta la búsqueda
    await websocket.send_json(
        {
            "type": "alert_triggered",
            "claim": text,
            "reason": reason,
            "timestamp": time.time(),
        }
    )

    # 4. Búsqueda simultánea asíncrona (pgvector docs internos + Web en vivo)
    t0 = time.time()
    internal_task = search_campaign_docs(text, top_k=2)
    web_task = search_live_web(text, max_results=2)

    internal_docs, web_results = await asyncio.gather(
        internal_task, web_task, return_exceptions=True
    )

    if isinstance(internal_docs, Exception):
        internal_docs = []
    if isinstance(web_results, Exception):
        web_results = []

    retrieval_ms = (time.time() - t0) * 1000

    # Fuentes recopiladas para mostrar en el pie de la tarjeta del teleprompter
    sources_summary = []
    for d in internal_docs:
        sources_summary.append({"type": "internal", "title": d.get("source", "Dossier")})
    for w in web_results:
        sources_summary.append({"type": "web", "title": w.get("source", "Web"), "url": w.get("url", "")})

    await websocket.send_json(
        {
            "type": "stream_start",
            "claim": text,
            "sources": sources_summary,
            "retrieval_time_ms": round(retrieval_ms, 1),
        }
    )

    # 5. Streaming de réplica con DeepSeek V3
    full_rebuttal = []
    async for token in stream_deepseek_rebuttal(text, internal_docs, web_results):
        full_rebuttal.append(token)
        await websocket.send_json(
            {
                "type": "stream_token",
                "token": token,
            }
        )

    total_latency_ms = (time.time() - utterance_start_time) * 1000

    await websocket.send_json(
        {
            "type": "stream_end",
            "latency_ms": round(total_latency_ms, 1),
            "full_text": "".join(full_rebuttal),
        }
    )


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """
    Recepción continua de audio PCM 16-bit 16kHz Mono binario desde el cliente/micrófono.
    Procesamiento continuo en ventanas de 512 muestras con Silero VAD.
    """
    await websocket.accept()
    print("[WS] Conexión WebSocket de audio establecida.")

    if vad_detector:
        vad_detector.reset_states()

    # Buffer de acumulador en muestras float32
    utterance_frames: List[np.ndarray] = []
    is_speaking = False
    silence_samples_count = 0
    utterance_start_time = 0.0

    # Constantes basadas en 16kHz
    SAMPLE_RATE = 16000
    WINDOW_SIZE = 512  # 32ms por ventana VAD
    SILENCE_SAMPLES_THRESHOLD = int((settings.SILENCE_DURATION_MS / 1000.0) * SAMPLE_RATE)
    MAX_UTTERANCE_SAMPLES = int((settings.MAX_UTTERANCE_MS / 1000.0) * SAMPLE_RATE)

    # Buffer residual de bytes crudos
    byte_remainder = b""

    try:
        while True:
            raw_bytes = await websocket.receive_bytes()
            if not raw_bytes:
                continue

            full_bytes = byte_remainder + raw_bytes
            # Cada muestra int16 son 2 bytes
            usable_bytes_len = len(full_bytes) - (len(full_bytes) % 2)
            byte_remainder = full_bytes[usable_bytes_len:]

            if usable_bytes_len == 0:
                continue

            # Conversión int16 -> float32 normalizado (-1.0 a 1.0)
            int16_samples = np.frombuffer(full_bytes[:usable_bytes_len], dtype=np.int16)
            float_samples = (int16_samples / 32768.0).astype(np.float32)

            # Iteración en bloques de 512 muestras para Silero VAD
            offset = 0
            while offset + WINDOW_SIZE <= len(float_samples):
                chunk = float_samples[offset : offset + WINDOW_SIZE]
                offset += WINDOW_SIZE

                has_voice, prob = vad_detector.is_speech(chunk)

                if has_voice:
                    if not is_speaking:
                        is_speaking = True
                        utterance_frames = []
                        silence_samples_count = 0
                        utterance_start_time = time.time()

                    utterance_frames.append(chunk)
                    silence_samples_count = 0

                    # Forzar corte si el interlocutor habla sin parar más de MAX_UTTERANCE_MS
                    current_samples = sum(len(f) for f in utterance_frames)
                    if current_samples >= MAX_UTTERANCE_SAMPLES:
                        audio_block = np.concatenate(utterance_frames)
                        asyncio.create_task(
                            process_utterance(audio_block, websocket, utterance_start_time)
                        )
                        utterance_frames = []
                        is_speaking = False
                        silence_samples_count = 0
                        vad_detector.reset_states()
                else:
                    if is_speaking:
                        utterance_frames.append(chunk)
                        silence_samples_count += WINDOW_SIZE

                        # Se detectó pausa suficiente: Procesar frase completa
                        if silence_samples_count >= SILENCE_SAMPLES_THRESHOLD:
                            is_speaking = False
                            silence_samples_count = 0
                            if utterance_frames:
                                audio_block = np.concatenate(utterance_frames)
                                asyncio.create_task(
                                    process_utterance(
                                        audio_block, websocket, utterance_start_time
                                    )
                                )
                                utterance_frames = []
                                vad_detector.reset_states()

    except WebSocketDisconnect:
        print("[WS] Cliente desconectado limpiamente.")
    except Exception as e:
        print(f"[WS] Error en la conexión: {e}")
    finally:
        if utterance_frames and is_speaking:
            audio_block = np.concatenate(utterance_frames)
            asyncio.create_task(
                process_utterance(audio_block, websocket, utterance_start_time)
            )
