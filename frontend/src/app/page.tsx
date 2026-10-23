"use client";

import React, { useState, useEffect, useRef } from "react";
import { useDebateSocket } from "../hooks/useDebateSocket";
import { StatusHeader } from "../components/StatusHeader";
import { AudioStreamer } from "../components/AudioStreamer";
import { TeleprompterCard } from "../components/TeleprompterCard";
import { User, ShieldAlert, Sparkles, Radio } from "lucide-react";

export default function TeleprompterPage() {
  const { isConnected, cards, transcripts, lastLatency, sendAudioChunk } =
    useDebateSocket();

  const [showLiveTranscript, setShowLiveTranscript] = useState(true);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  // Registro del Service Worker para PWA
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .then((reg) => console.log("[PWA] Service Worker registrado:", reg.scope))
        .catch((err) => console.error("[PWA] Error registrando SW:", err));
    }
  }, []);

  return (
    <div className="flex flex-col h-screen w-full bg-[#050505] text-white overflow-hidden">
      {/* Barra de Estado y Latencia */}
      <StatusHeader isConnected={isConnected} lastLatency={lastLatency} />

      {/* Barra de Control de Captura de Audio */}
      <div className="flex items-center justify-between px-6 py-3 bg-[#0a0a0a] border-b border-[#1c1c1c]">
        <div className="flex items-center gap-3">
          <AudioStreamer
            onAudioChunk={sendAudioChunk}
            isConnected={isConnected}
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowLiveTranscript(!showLiveTranscript)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors ${
              showLiveTranscript
                ? "bg-[#1f1f1f] border-[#333] text-white"
                : "bg-transparent border-[#222] text-[#777]"
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            {showLiveTranscript ? "OCULTAR TRANSCRIPCIÓN" : "VER TRANSCRIPCIÓN"}
          </button>
        </div>
      </div>

      {/* Contenedor Principal: Split View (Teleprompter Réplicas + Feed Transcripción) */}
      <div className="flex flex-1 overflow-hidden">
        {/* PANEL PRINCIPAL: TELEPROMPTER DE RÉPLICAS */}
        <main className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
          <div ref={scrollAnchorRef} />

          {cards.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 border border-dashed border-[#1f1f1f] rounded-2xl bg-[#080808]/50">
              <Sparkles className="w-12 h-12 text-[#00F0FF] mb-4 animate-pulse" />
              <h2 className="text-2xl font-black tracking-tight text-white mb-2">
                TELEPROMPTER EN ESPERA ACTIVA
              </h2>
              <p className="text-[#777] max-w-md text-sm leading-relaxed">
                El sistema está escuchando a 16 kHz. En cuanto el oponente emita una afirmación,
                cifra o cuestionamiento, las viñetas de réplica aparecerán aquí en menos de 2.5s.
              </p>
            </div>
          ) : (
            cards.map((card, idx) => (
              <TeleprompterCard
                key={card.id}
                card={card}
                isLatest={idx === 0}
              />
            ))
          )}
        </main>

        {/* PANEL LATERAL: TRANSCRIPCIÓN Y DIARIZACIÓN EN TIEMPO REAL */}
        {showLiveTranscript && (
          <aside className="w-80 md:w-96 border-l border-[#1a1a1a] bg-[#070707] flex flex-col h-full">
            <div className="px-4 py-3 border-b border-[#181818] flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wider text-[#999]">
                DIARIZACIÓN EN VIVO
              </span>
              <span className="text-[10px] bg-[#1a1a1a] text-[#888] px-2 py-0.5 rounded font-mono">
                Silero VAD + Resemblyzer
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {transcripts.length === 0 ? (
                <div className="text-xs text-[#555] text-center mt-10">
                  Esperando actividad de voz...
                </div>
              ) : (
                transcripts.map((t, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded-xl border text-xs leading-relaxed ${
                      t.speaker === "candidate"
                        ? "bg-[#0c1a10] border-[#00FF66]/30 text-[#e0e0e0]"
                        : "bg-[#1a0e10] border-[#FF334B]/30 text-[#e0e0e0]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className={`font-black uppercase tracking-wider text-[10px] flex items-center gap-1 ${
                          t.speaker === "candidate"
                            ? "text-[#00FF66]"
                            : "text-[#FF334B]"
                        }`}
                      >
                        {t.speaker === "candidate" ? (
                          <>
                            <User className="w-3 h-3" /> CANDIDATO
                          </>
                        ) : (
                          <>
                            <ShieldAlert className="w-3 h-3" /> OPONENTE
                          </>
                        )}
                      </span>
                      <span className="text-[10px] font-mono text-[#666]">
                        {(t.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p>{t.text}</p>
                  </div>
                ))
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
