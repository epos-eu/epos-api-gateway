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
    
    try:
        # Forward the request to BRGM
        resp = requests.get(full_url)
        # Return the response content and status code directly
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type", "application/json"))
    except requests.RequestException as e:
        return {"error": str(e)}, 500