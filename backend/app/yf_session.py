"""Shared yfinance session that impersonates a real browser.

Yahoo Finance blocks requests from cloud provider IPs by detecting
non-browser TLS fingerprints. curl_cffi replicates Chrome's TLS
handshake, bypassing this detection.
"""
try:
    from curl_cffi import requests as cffi_requests
    session = cffi_requests.Session(impersonate="chrome")
except ImportError:
    import requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    })
