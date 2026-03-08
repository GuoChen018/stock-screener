"""Shared yfinance session with browser-like user-agent.

Yahoo Finance blocks requests from cloud provider IPs that use
default Python user-agents. This module patches yfinance to use
a browser-like UA string.
"""
import requests

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
})
