"""Find pages that appear to host a given client's booking photo.

Uses Google's official Custom Search JSON API (not scraping google.com search
result pages directly, which is against Google's terms). Requires a Custom
Search Engine configured to search the whole web, plus an API key.

Setup:
  1. https://programmablesearchengine.google.com/ -> create a search engine,
     set it to search the entire web, copy its Search Engine ID (cx).
  2. https://console.cloud.google.com -> enable "Custom Search API", create
     an API key.
"""
from googleapiclient.discovery import build


def find_mugshot_pages(client_name: str, api_key: str, cx: str, num_results: int = 20) -> list[dict]:
    """Return a list of {title, link, snippet} results for likely mugshot pages."""
    service = build("customsearch", "v1", developerKey=api_key)
    query = f'"{client_name}" mugshot OR arrest OR booking'

    results = []
    start = 1
    while len(results) < num_results:
        batch_size = min(10, num_results - len(results))
        response = service.cse().list(q=query, cx=cx, start=start, num=batch_size).execute()
        items = response.get("items", [])
        if not items:
            break
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        start += batch_size

    return results
