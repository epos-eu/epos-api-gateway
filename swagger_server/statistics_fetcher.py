import logging
import requests
from flask import request, Response
import os

def statistics_fetcher():
    statistic_base_url = os.getenv("BRGM_BASE_URL")
    statistic_token = os.getenv("BRGM_TOKEN")
    #get query string from request
    query_string = request.query_string.decode("utf-8")
    #checks
    if not query_string:
        return {"error": "No query parameters provided"}, 400
    
    # build full url
    full_url = f"{statistic_base_url}?{query_string}&token_auth={statistic_token}"
    logging.info(f"stats url: {full_url}")
    
    try:
        # Forward the request to BRGM
        resp = requests.get(full_url)
        # Return the response content and status code directly
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type", "application/json"))
    except requests.RequestException as e:
        return {"error": str(e)}, 500
    
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
