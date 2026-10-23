"use client";

import React from "react";
import { Zap, Wifi, WifiOff } from "lucide-react";

interface StatusHeaderProps {
  isConnected: boolean;
  lastLatency: number | null;
}

export const StatusHeader: React.FC<StatusHeaderProps> = ({
  isConnected,
  lastLatency,
}) => {
  const getLatencyBadge = () => {
    if (lastLatency === null) return null;
    let color = "text-[#00FF66] border-[#00FF66]/30 bg-[#00FF66]/10";
    if (lastLatency > 2000 && lastLatency <= 2500) {
      color = "text-[#FFD600] border-[#FFD600]/30 bg-[#FFD600]/10";
    } else if (lastLatency > 2500) {
      color = "text-[#FF334B] border-[#FF334B]/30 bg-[#FF334B]/10";
    }

    return (
      <div
        className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold border ${color}`}
      >
        <Zap className="w-3.5 h-3.5 animate-pulse" />
        <span>{lastLatency.toFixed(0)} ms</span>
      </div>
    );
  };

  return (
    <header className="flex items-center justify-between border-b border-[#1c1c1c] bg-[#080808] px-6 py-3 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <span className="text-xl font-black tracking-tighter text-white">
          debate<span className="text-[#00F0FF]">IA</span>
        </span>
        <span className="text-[11px] font-bold uppercase tracking-widest text-black bg-[#FFD600] px-2 py-0.5 rounded">
          PROMPTER VIVO
        </span>
      </div>

      <div className="flex items-center gap-4">
        {getLatencyBadge()}

        <div className="flex items-center gap-2">
          {isConnected ? (
            <div className="flex items-center gap-1.5 text-xs text-[#00FF66] font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-[#00FF66] animate-pulse" />
              <span>ONLINE</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-[#FF334B] font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FF334B]" />
              <span>OFFLINE</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
