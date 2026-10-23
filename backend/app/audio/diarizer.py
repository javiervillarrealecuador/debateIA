import os
from pathlib import Path
from typing import Tuple
import numpy as np
from resemblyzer import VoiceEncoder


class SpeakerClassifier:
    """
    Compara las intervenciones vocales procesadas contra el perfil biométrico
    pregrabado del candidato ('candidate_profile.npy') mediante similitud coseno.
    """

    def __init__(self, profile_path: str, threshold: float = 0.70):
        self.profile_path = Path(profile_path)
        self.threshold = threshold
        self.encoder = VoiceEncoder(device="cpu")
        self.candidate_profile: np.ndarray | None = None
        self.load_candidate_profile()

    def load_candidate_profile(self) -> bool:
        if self.profile_path.exists():
            try:
                emb = np.load(str(self.profile_path))
                norm = np.linalg.norm(emb)
                if norm > 0:
                    self.candidate_profile = emb / norm
                else:
                    self.candidate_profile = emb
                print(f"[BIOMETRÍA] Perfil de voz cargado desde: {self.profile_path}")
                return True
            except Exception as e:
                print(f"[BIOMETRÍA] Error al leer {self.profile_path}: {e}")
                self.candidate_profile = None
                return False
        else:
            print(f"[BIOMETRÍA] Advertencia: Perfil de voz {self.profile_path} no encontrado.")
            self.candidate_profile = None
            return False

    def classify(self, audio_16k_float: np.ndarray) -> Tuple[str, float]:
        """
        Calcula el embedding del chunk/utterance y la similitud coseno contra el candidato.
        Retorna:
            - speaker: 'candidate' | 'opponent' | 'unknown'
            - similarity: float [-1.0 .. 1.0]
        """
        # Se requieren al menos ~0.4s de audio (6400 muestras) para un embedding confiable
        if len(audio_16k_float) < 6400:
            return "opponent", 0.0

        try:
            # Resemblyzer extrae vector de 256 dimensiones
            emb = self.encoder.embed_utterance(audio_16k_float)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm

            if self.candidate_profile is None:
                # Si aún no existe el archivo calibrado, se asume oponente para no silenciar alertas
                return "opponent", 0.0

            # Producto escalar equivale a similitud coseno con vectores normalizados
            similarity = float(np.dot(self.candidate_profile, emb))

            if similarity >= self.threshold:
                return "candidate", similarity
            else:
                return "opponent", similarity
        except Exception as e:
            print(f"[BIOMETRÍA] Error durante extracción de embedding: {e}")
            return "opponent", 0.0
