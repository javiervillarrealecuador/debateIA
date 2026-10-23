import io
from typing import Optional
import numpy as np
from faster_whisper import WhisperModel


class FastTranscriber:
    """
    Transcriptor de voz ultrarrápido basado en faster-whisper (CTranslate2).
    Optimizado para CPU en entornos de Hetzner Cloud con cuantización INT8
    y decodificación voraz (beam_size=1) para minimizar la latencia a < 250ms.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "es",
    ):
        print(
            f"[STT] Inicializando faster-whisper '{model_size}' en {device} ({compute_type})..."
        )
        self.language = language
        # Carga el modelo optimizado con CTranslate2
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=4,
            num_workers=1,
        )

    def transcribe(self, audio_16k_float: np.ndarray) -> str:
        """
        Transcribe un fragmento de audio 16kHz float32 (-1.0 a 1.0).
        """
        if len(audio_16k_float) < 1600:  # Menos de 100ms
            return ""

        # faster-whisper acepta directamente arreglos numpy float32
        segments, _ = self.model.transcribe(
            audio_16k_float,
            language=self.language,
            beam_size=1,  # Búsqueda voraz (Greedy) para latencia mínima
            best_of=1,
            temperature=0.0,
            vad_filter=False,  # Silero VAD ya filtró el audio previamente
            without_timestamps=True,
        )

        full_text = " ".join([segment.text.strip() for segment in segments]).strip()
        return full_text
