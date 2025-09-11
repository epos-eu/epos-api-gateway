import requests
from flask import request, Response
import os

def scientific_example_fetcher():
    scientific_base_url = os.getenv("SCIENTIFIC_BASE_URL")
    scientific_token = os.getenv("SCIENTIFIC_TOKEN")
    if not scientific_base_url or not scientific_token:
        return Response("Scientific service is not configured", status=500)
    url = (f"{scientific_base_url}&private_token={scientific_token}")

    try:
        r = requests.get(url)
        return Response(r.content, status=r.status_code, content_type=r.headers.get("Content-Type"))
    except Exception as e:
        return Response(str(e), status=500)
