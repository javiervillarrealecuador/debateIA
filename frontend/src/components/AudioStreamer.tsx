"use client";

import React, { useState, useRef, useEffect } from "react";
import { Mic, MicOff, Volume2 } from "lucide-react";

interface AudioStreamerProps {
  onAudioChunk: (buffer: ArrayBuffer) => void;
  isConnected: boolean;
}

export const AudioStreamer: React.FC<AudioStreamerProps> = ({
  onAudioChunk,
  isConnected,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  const startStreaming = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      mediaStreamRef.current = stream;

      // Forzar AudioContext a 16000 Hz exactos para coincidir con Silero VAD y faster-whisper
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);

      // ScriptProcessor de 1024 muestras (~64ms a 16kHz)
      const processor = audioCtx.createScriptProcessor(1024, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);

        // Calcular volumen para el indicador visual
        let sum = 0;
        const int16Buffer = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          sum += s * s;
          // Conversión Float32 [-1, 1] a Int16 [-32768, 32767]
          int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        const rms = Math.sqrt(sum / inputData.length);
        setAudioLevel(Math.min(100, Math.round(rms * 250)));

        // Transmitir buffer binario al WebSocket
        onAudioChunk(int16Buffer.buffer);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      setIsRecording(true);
    } catch (err) {
      console.error("[AUDIO] Error al acceder al micrófono:", err);
      alert("No se pudo acceder al micrófono. Por favor permite los permisos de audio.");
    }
  };

  const stopStreaming = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    setIsRecording(false);
    setAudioLevel(0);
  };

  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, []);

  return (
    <div className="flex items-center gap-3 bg-[#111] px-4 py-2 rounded-xl border border-[#222]">
      <button
        onClick={isRecording ? stopStreaming : startStreaming}
        disabled={!isConnected}
        className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-black tracking-wider text-sm transition-all duration-150 ${
          isRecording
            ? "bg-[#FF334B] text-white hover:bg-red-600 shadow-lg shadow-red-900/40 animate-pulse"
            : isConnected
            ? "bg-[#00F0FF] text-black hover:bg-cyan-300 font-bold"
            : "bg-[#222] text-[#666] cursor-not-allowed"
        }`}
      >
        {isRecording ? (
          <>
            <MicOff className="w-4 h-4" />
            DETENER MIC
          </>
        ) : (
          <>
            <Mic className="w-4 h-4" />
            INICIAR MIC EN VIVO
          </>
        )}
      </button>

      {/* Medidor visual de volumen (VU Meter) */}
      <div className="flex items-center gap-1.5 w-24 h-4 bg-[#1a1a1a] rounded-full px-1 overflow-hidden border border-[#2a2a2a]">
        <div
          className={`h-2 rounded-full transition-all duration-75 ${
            audioLevel > 60
              ? "bg-[#FF334B]"
              : audioLevel > 25
              ? "bg-[#FFD600]"
              : "bg-[#00FF66]"
          }`}
          style={{ width: `${Math.max(5, audioLevel)}%` }}
        />
      </div>
    </div>
  );
};
