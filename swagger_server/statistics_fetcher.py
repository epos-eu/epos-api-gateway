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
    
import requests
from flask import request, Response
import urllib.parse

def scientific_example_fetcher():
    scientific_base_url = os.getenv("SCIENTIFIC_BASE_URL")
    scientific_token = os.getenv("SCIENTIFIC_TOKEN")
    if not scientific_base_url or not scientific_token:
        return Response("Scientific service is not configured", status=500)
    project_id = request.args.get("project_id")
    file_path = request.args.get("file_path")
    ref = request.args.get("ref", "main")  # default to main if not provided

    if not project_id or not file_path:
        return Response("Missing required query parameters: project_id and file_path", status=400)

    # Encode the file path properly for GitLab API
    encoded_file_path = urllib.parse.quote(file_path, safe="")

    url = (
        f"{scientific_base_url}/{project_id}/repository/files/"
        f"{encoded_file_path}/raw?ref={ref}&private_token={scientific_token}"
    )

    try:
        r = requests.get(url)
        return Response(r.content, status=r.status_code, content_type=r.headers.get("Content-Type"))
    except Exception as e:
        return Response(str(e), status=500)
