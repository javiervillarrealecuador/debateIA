import torch
import numpy as np
from typing import Optional, Tuple


class SileroVADDetector:
    """
    Detector de actividad vocal (VAD) en streaming basado en Silero VAD v4/v5.
    Evalúa ventanas de audio a 16 kHz (muestras en bloques de 512 = 32ms) y
    determina probabilidad de voz con latencia sub-milisegundo en CPU.
    """

    def __init__(self, threshold: float = 0.5, sampling_rate: int = 16000):
        self.sampling_rate = sampling_rate
        self.threshold = threshold
        # Carga el modelo Silero pre-entrenado
        self.model, self.utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
            trust_repo=True,
        )
        self.model.eval()
        self.reset_states()

    def reset_states(self):
        """Reinicia el estado recurrente interno de Silero VAD."""
        self.model.reset_states()

    def is_speech(self, audio_chunk_16k_float: np.ndarray) -> Tuple[bool, float]:
        """
        Evalúa un bloque de audio de exactamente 512 muestras (32ms a 16kHz).
        Retorna (es_voz: bool, probabilidad: float).
        """
        if len(audio_chunk_16k_float) != 512:
            # Rellena o recorta si difiere por poco
            if len(audio_chunk_16k_float) < 512:
                audio_chunk_16k_float = np.pad(
                    audio_chunk_16k_float,
                    (0, 512 - len(audio_chunk_16k_float)),
                    mode="constant",
                )
            else:
                audio_chunk_16k_float = audio_chunk_16k_float[:512]

        tensor_chunk = torch.from_numpy(audio_chunk_16k_float).float()
        with torch.no_grad():
            speech_prob = self.model(tensor_chunk, self.sampling_rate).item()

        return (speech_prob >= self.threshold), speech_prob
