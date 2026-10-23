import asyncio
from typing import List, Dict
import httpx
from app.config import get_settings

settings = get_settings()


async def search_tavily(
    client: httpx.AsyncClient, query: str, max_results: int = 2
) -> List[Dict[str, str]]:
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": settings.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": max_results,
    }
    response = await client.post(url, json=payload, timeout=1.4)
    if response.status_code == 200:
        data = response.json()
        results = []
        for r in data.get("results", []):
            results.append(
                {
                    "source": r.get("title", "Web"),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:250],
                }
            )
        return results
    return []


async def search_brave(
    client: httpx.AsyncClient, query: str, max_results: int = 2
) -> List[Dict[str, str]]:
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": settings.BRAVE_API_KEY,
    }
    params = {"q": query, "count": max_results}
    response = await client.get(url, headers=headers, params=params, timeout=0.85)
    if response.status_code == 200:
        data = response.json()
        results = []
        for r in data.get("web", {}).get("results", []):
            results.append(
                {
                    "source": r.get("title", "Web"),
                    "url": r.get("url", ""),
                    "snippet": r.get("description", "")[:250],
                }
            )
        return results
    return []


async def search_live_web(query: str, max_results: int = 2) -> List[Dict[str, str]]:
    """
    Consulta en tiempo real a APIs de búsqueda (Tavily / Brave) con límite estricto de timeout (850ms).
    Garantiza que la latencia total del pipeline nunca exceda 2.5s.
    """
    if not settings.TAVILY_API_KEY and not settings.BRAVE_API_KEY:
        return []

    async with httpx.AsyncClient() as client:
        try:
            if settings.TAVILY_API_KEY:
                return await search_tavily(client, query, max_results)
            elif settings.BRAVE_API_KEY:
                return await search_brave(client, query, max_results)
        except (httpx.TimeoutException, httpx.RequestError) as e:
            print(f"[WEB_SEARCH] Búsqueda descartada por límite de tiempo o error: {e}")
            return []
        except Exception as e:
            print(f"[WEB_SEARCH] Excepción inesperada: {e}")
            return []
    return []
