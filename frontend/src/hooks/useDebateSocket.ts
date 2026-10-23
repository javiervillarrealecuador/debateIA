import { useEffect, useRef, useState, useCallback } from "react";

export interface SourceItem {
  type: "internal" | "web";
  title: string;
  url?: string;
}

export interface RebuttalCard {
  id: string;
  claim: string;
  rebuttal: string;
  sources: SourceItem[];
  isStreaming: boolean;
  retrievalMs?: number;
  totalLatencyMs?: number;
  timestamp: number;
}

export interface TranscriptItem {
  speaker: "candidate" | "opponent";
  confidence: number;
  text: string;
  timestamp: number;
}

export function useDebateSocket(url?: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [cards, setCards] = useState<RebuttalCard[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [lastLatency, setLastLatency] = useState<number | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const wsUrl =
    url ||
    process.env.NEXT_PUBLIC_WS_URL ||
    (typeof window !== "undefined"
      ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/audio`
      : "ws://localhost:8000/ws/audio");

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        setIsConnected(true);
        console.log("[WS] Conectado exitosamente al backend de debateIA");
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log("[WS] Desconectado. Reintentando en 2 segundos...");
        reconnectTimeoutRef.current = setTimeout(connect, 2000);
      };

      ws.onerror = (err) => {
        console.error("[WS] Error de conexión:", err);
        ws.close();
      };

      ws.onmessage = (event) => {
        if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data);
            handleSocketMessage(data);
          } catch (e) {
            console.error("[WS] Error parseando JSON:", e);
          }
        }
      };

      socketRef.current = ws;
    } catch (e) {
      console.error("[WS] Error al instanciar WebSocket:", e);
      reconnectTimeoutRef.current = setTimeout(connect, 2000);
    }
  }, [wsUrl]);

  const handleSocketMessage = (data: any) => {
    switch (data.type) {
      case "transcription":
        setTranscripts((prev) => [
          ...prev.slice(-30), // Conservar los últimos 30 fragmentos de contexto
          {
            speaker: data.speaker,
            confidence: data.confidence,
            text: data.text,
            timestamp: data.timestamp,
          },
        ]);
        break;

      case "alert_triggered":
        // Pre-alerta visual inmediata
        break;

      case "stream_start": {
        const newCard: RebuttalCard = {
          id: `card_${Date.now()}`,
          claim: data.claim,
          rebuttal: "",
          sources: data.sources || [],
          isStreaming: true,
          retrievalMs: data.retrieval_time_ms,
          timestamp: Date.now(),
        };
        setCards((prev) => [newCard, ...prev]);
        break;
      }

      case "stream_token":
        setCards((prev) => {
          if (prev.length === 0) return prev;
          const [first, ...rest] = prev;
          return [
            {
              ...first,
              rebuttal: first.rebuttal + data.token,
            },
            ...rest,
          ];
        });
        break;

      case "stream_end":
        setLastLatency(data.latency_ms);
        setCards((prev) => {
          if (prev.length === 0) return prev;
          const [first, ...rest] = prev;
          return [
            {
              ...first,
              isStreaming: false,
              totalLatencyMs: data.latency_ms,
              rebuttal: data.full_text || first.rebuttal,
            },
            ...rest,
          ];
        });
        break;
    }
  };

  const sendAudioChunk = (pcmBytes: ArrayBuffer) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(pcmBytes);
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  return {
    isConnected,
    cards,
    transcripts,
    lastLatency,
    sendAudioChunk,
  };
}
