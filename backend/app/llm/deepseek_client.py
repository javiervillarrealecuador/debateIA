import json
from typing import AsyncIterator, List, Dict
import httpx
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """Eres el apuntador táctico ultrarrápido del candidato en un debate en vivo.
Tu misión es refutar, contraargumentar o precisar afirmaciones del oponente en formato teleprompter de lectura instantánea.

REGLAS CRÍTICAS INQUEBRANTABLES:
1. Genera MÁXIMO 2 viñetas.
2. MÁXIMO 12 palabras por cada viñeta.
3. Formato telegráfico obligatorio por viñeta:
   • [Dato oficial o cifra real] ([Fuente]): [Réplica o pregunta contundente].
4. Cero preámbulos, cero saludos, cero conclusiones. Directo al grano.
5. Si no hay datos específicos en el contexto, ataca la premisa con solidez económica o institucional en menos de 10 palabras."""


async def stream_deepseek_rebuttal(
    claim_text: str,
    internal_docs: List[Dict[str, str]],
    web_results: List[Dict[str, str]],
) -> AsyncIterator[str]:
    """
    Envía la solicitud en streaming a DeepSeek V3 (deepseek-chat).
    Produce tokens individuales en tiempo real mediante SSE para el teleprompter PWA.
    """
    # Construcción de contexto ultra-resumido para no dilatar el Time-to-First-Token (TTFT)
    context_lines = []
    if internal_docs:
        context_lines.append("--- PLAN DE GOBIERNO / DOSSIER INTERNO ---")
        for doc in internal_docs[:2]:
            context_lines.append(f"[{doc['source']}]: {doc['content'][:250]}")

    if web_results:
        context_lines.append("--- EVIDENCIA WEB / NOTICIAS EN VIVO ---")
        for web in web_results[:2]:
            context_lines.append(f"[{web['source']}]: {web['snippet'][:200]}")

    context_str = "\n".join(context_lines)

    user_message = f"""AFIRMACIÓN DEL OPONENTE:
"{claim_text}"

EVIDENCIA Y DATOS DISPONIBLES:
{context_str if context_str else "No hay fuentes directas disponibles. Genera réplica de criterio firme."}

Genera las 2 viñetas telegráficas (máx 12 palabras c/u) ahora:"""

    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,  # Baja temperatura para precisión fáctica y rapidez
        "max_tokens": 80,    # Límite estricto para evitar respuestas largas
        "stream": True,
    }

    url = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=4.0) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[DEEPSEEK] Error {response.status_code}: {error_text.decode('utf-8')}")
                    yield f"• Error al consultar DeepSeek API ({response.status_code})."
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            delta = data_json["choices"][0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
        except httpx.TimeoutException:
            print("[DEEPSEEK] Timeout excedido en llamada streaming.")
            yield "• Tiempo agotado al generar réplica en vivo."
        except Exception as e:
            print(f"[DEEPSEEK] Excepción durante streaming: {e}")
            yield f"• Error de conexión con el motor de réplica."
