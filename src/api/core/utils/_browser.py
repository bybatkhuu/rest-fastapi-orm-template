from pydantic import validate_call
from fastapi import Request


@validate_call(config={"arbitrary_types_allowed": True})
def is_browser(request: Request, threshold: int = 4) -> bool:
    _headers = request.headers
    _score = 0
    _user_agent = _headers.get("user-agent", "").lower()

    # Strong negative signals
    _non_browser_agents = (
        "curl",
        "wget",
        "postman",
        "insomnia",
        "python-requests",
        "aiohttp",
        "httpx",
        "go-http-client",
        "okhttp",
        "java/",
        "apache-httpclient",
        "powershell",
        "libwww-perl",
    )
    if any(_agent in _user_agent for _agent in _non_browser_agents):
        return False

    # User-Agent looks browser-ish
    _browser_agents = (
        "mozilla/",
        "chrome/",
        "safari/",
        "firefox/",
        "edg/",
        "opr/",
        "opera",
        "applewebkit/",
        "gecko/",
    )
    if any(_agent in _user_agent for _agent in _browser_agents):
        _score += 3

    # Modern browser security headers
    if "sec-fetch-site" in _headers:
        _score += 2

    if "sec-fetch-mode" in _headers:
        _score += 2

    if "sec-fetch-dest" in _headers:
        _score += 1

    if "sec-ch-ua" in _headers:
        _score += 2

    if "sec-ch-ua-mobile" in _headers:
        _score += 1

    if "sec-ch-ua-platform" in _headers:
        _score += 1

    # Typical browser _headers
    if "accept-language" in _headers:
        _score += 2

    if "origin" in _headers:
        _score += 1

    if "referer" in _headers:
        _score += 1

    # Accept header
    _accept = _headers.get("accept", "").lower()
    if "text/html" in _accept:
        _score += 2

    if "application/xhtml+xml" in _accept:
        _score += 2

    if "*/*" == _accept:
        _score -= 1

    # Final decision
    _result = _score >= threshold
    return _result


__all__ = [
    "is_browser",
]
