import httpx
from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    raw_content: str | None = None
    published_date: str | None = None


class SearchError(RuntimeError):
    pass


class TavilySearch:
    URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        max_results: int = 3,
        include_raw_content: bool = False,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key
        self._max_results = max_results
        self._include_raw_content = include_raw_content
        self._timeout = timeout
        self._transport = transport

    async def search(self, query: str) -> list[SearchResult]:
        payload = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": self._max_results,
            "include_published_date": True,
        }
        if self._include_raw_content:
            payload["include_raw_content"] = "text"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                res = await client.post(self.URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise SearchError(f"Tavily request failed: {type(exc).__name__}") from exc
        if res.status_code != 200:
            raise SearchError(f"Tavily returned HTTP {res.status_code}: {res.text[:200]}")

        results = []
        for item in res.json().get("results", []):
            if item.get("url") and item.get("content"):
                results.append(
                    SearchResult(
                        title=item.get("title") or item["url"],
                        url=item["url"],
                        content=item["content"],
                        raw_content=item.get("raw_content") or None,
                        published_date=item.get("published_date"),
                    )
                )
        return results
