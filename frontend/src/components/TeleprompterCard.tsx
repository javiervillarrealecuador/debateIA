"use client";

import React from "react";
import { RebuttalCard } from "../hooks/useDebateSocket";
import { BookOpen, Globe, Flame } from "lucide-react";

interface TeleprompterCardProps {
  card: RebuttalCard;
  isLatest: boolean;
}

export const TeleprompterCard: React.FC<TeleprompterCardProps> = ({
  card,
  isLatest,
}) => {
  return (
    <article
      className={`rounded-2xl transition-all duration-300 border p-6 md:p-8 ${
        isLatest
          ? "bg-[#0c0c0c] border-[#00F0FF]/60 shadow-[0_0_40px_rgba(0,240,255,0.15)] ring-1 ring-[#00F0FF]/30"
          : "bg-[#090909] border-[#222] opacity-80"
      }`}
    >
      {/* Cabecera de la tarjeta: Afirmación del Oponente */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="flex items-center gap-1 text-[11px] font-black uppercase tracking-widest text-[#FF334B] bg-[#FF334B]/15 px-2.5 py-1 rounded-md border border-[#FF334B]/30">
            <Flame className="w-3.5 h-3.5" />
            AFIRMACIÓN OPONENTE
          </span>
          {card.totalLatencyMs && (
            <span className="text-xs font-mono text-[#888]">
              {card.totalLatencyMs.toFixed(0)} ms
            </span>
          )}
        </div>
        <p className="text-lg md:text-xl font-medium text-[#ccc] italic leading-snug">
          &ldquo;{card.claim}&rdquo;
        </p>
      </div>

      {/* Réplica Táctica del Teleprompter (Tipografía Gigante y Alto Contraste) */}
      <div className="my-5 p-5 md:p-6 rounded-xl bg-black border border-[#2a2a2a]">
        <div className="text-2xl md:text-4xl lg:text-5xl font-black tracking-tight text-white leading-tight font-sans whitespace-pre-line">
          {card.rebuttal}
          {card.isStreaming && (
            <span className="inline-block w-3.5 h-8 md:h-10 ml-2 bg-[#00F0FF] animate-pulse align-middle" />
          )}
        </div>
      </div>

      {/* Fuentes y Evidencia */}
      {card.sources.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-[#1a1a1a]">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#666]">
            FUENTES:
          </span>
          {card.sources.map((src, idx) => (
            <span
              key={idx}
              className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md ${
                src.type === "internal"
                  ? "bg-[#00FF66]/15 text-[#00FF66] border border-[#00FF66]/30"
                  : "bg-[#00F0FF]/15 text-[#00F0FF] border border-[#00F0FF]/30"
              }`}
            >
              {src.type === "internal" ? (
                <BookOpen className="w-3 h-3" />
              ) : (
                <Globe className="w-3 h-3" />
              )}
              {src.title}
            </span>
          ))}
        </div>
      )}
    </article>
  );
};
