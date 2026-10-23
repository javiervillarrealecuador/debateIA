#!/usr/bin/env python3
"""
Enroll Candidate Voice Profile
Extrae un vector de embedding de 256 dimensiones de la voz del candidato
utilizando Resemblyzer a partir de un archivo WAV de ~15 segundos o grabación directa.
El archivo de salida 'candidate_profile.npy' se utiliza en runtime para calcular
la similitud coseno contra las intervenciones en vivo y distinguir al Candidato del Oponente.
"""

import argparse
import sys
from pathlib import Path
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav


def enroll_from_file(audio_path: str, output_path: str) -> None:
    path = Path(audio_path)
    if not path.exists():
        print(f"[ERROR] El archivo de audio '{audio_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Cargando y preprocesando audio de muestra: {audio_path}")
    try:
        # preprocess_wav convierte a mono, normaliza volumen y remuestrea a 16kHz
        wav = preprocess_wav(str(path))
    except Exception as e:
        print(f"[ERROR] Error al procesar el archivo de audio: {e}", file=sys.stderr)
        sys.exit(1)

    duration = len(wav) / 16000.0
    print(f"[*] Duración útil detectada: {duration:.2f} segundos")
    if duration < 5.0:
        print("[ADVERTENCIA] Se recomiendan al menos 10-15 segundos para mayor precisión.")

    print("[*] Inicializando VoiceEncoder (Resemblyzer)...")
    encoder = VoiceEncoder(device="cpu")

    print("[*] Calculando embedding de referencia del candidato...")
    # Se genera el embedding de la intervención completa
    embedding = encoder.embed_utterance(wav)

    # Normalización L2 unitaria explícita para producto escalar / similitud coseno directa
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(out_file), embedding)

    print(f"[EXITO] Perfil de voz guardado correctamente en: {out_file.resolve()}")
    print(f"[*] Dimensión del vector: {embedding.shape} (Norma L2: {np.linalg.norm(embedding):.4f})")


def main():
    parser = argparse.ArgumentParser(
        description="Generador de Perfil Biométrico Vocal para Asistente de Debate"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Ruta al archivo WAV/MP3 de calibración del candidato (mínimo 10-15s)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="candidate_profile.npy",
        help="Ruta donde se guardará el archivo .npy (por defecto: candidate_profile.npy)",
    )

    args = parser.parse_args()
    enroll_from_file(args.input, args.output)


if __name__ == "__main__":
    main()
