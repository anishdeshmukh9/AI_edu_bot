import urllib.parse


def youtube_search(query: str):
    """
    Returns 2–3 clickable YouTube search URLs for the topic.
    This is fast, reliable, and never blocks the API.
    """
    queries = [
        query,
        f"{query} physics",
        f"{query} tutorial",
    ]

    links = []
    for q in queries:
        encoded = urllib.parse.quote_plus(q)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        links.append(url)

    return links[:3]
