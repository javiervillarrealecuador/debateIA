#!/usr/bin/env python3
"""
Test Mic Client for DebateIA
Captura audio del micrófono local a 16kHz 16-bit PCM Mono y lo envía en streaming
binario continuo por WebSocket al backend para probar latencia y respuestas en tiempo real.
"""

import asyncio
import json
import sys
import pyaudio
import websockets

CHUNK_SIZE = 1024  # Muestras por chunk (~64ms a 16kHz)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


async def send_audio(ws_url: str):
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    print(f"[*] Conectando a {ws_url}...")
    async with websockets.connect(ws_url) as ws:
        print("[*] Conexión establecida. Transmitiendo audio... Presiona Ctrl+C para detener.")

        async def audio_sender():
            loop = asyncio.get_running_loop()
            while True:
                data = await loop.run_in_executor(None, stream.read, CHUNK_SIZE, False)
                await ws.send(data)

        async def message_receiver():
            async for msg in ws:
                try:
                    payload = json.loads(msg)
                    msg_type = payload.get("type")
                    if msg_type == "transcription":
                        speaker = payload.get("speaker")
                        text = payload.get("text")
                        conf = payload.get("confidence", 0)
                        print(f"\n[{speaker.upper()} - {conf:.2f}] {text}")
                    elif msg_type == "stream_token":
                        sys.stdout.write(payload.get("token", ""))
                        sys.stdout.flush()
                    elif msg_type == "stream_end":
                        print(f"\n[LATENCIA TOTAL: {payload.get('latency_ms', 0)} ms]\n" + "-"*40)
                except Exception:
                    pass

        try:
            await asyncio.gather(audio_sender(), message_receiver())
        except asyncio.CancelledError:
            pass
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000/ws/audio"
    try:
        asyncio.run(send_audio(url))
    except KeyboardInterrupt:
        print("\n[*] Transmisión finalizada por el usuario.")
