import requests
import json
from flask import Response
import logging
import urllib.parse

import requests
from flask import Response, send_file, make_response, jsonify
import jwt
import os

PREFIX = os.getenv('PREFIX', '')

RESOURCES_HOST = 'http://'+PREFIX+'resources-service:8080'
WORKSPACES_HOST = 'http://'+PREFIX+'workspace-service:8080'
EXTERNAL_ACCESS_HOST = 'http://'+PREFIX+'external-access-service:8080'
INGESTOR_HOST = 'http://'+PREFIX+'ingestor-service:8080'
BACKOFFICE_HOST = 'http://'+PREFIX+'backoffice-service:8080'
CONVERTER_HOST = 'http://'+PREFIX+'converter-service:8080'
CONVERTER_ROUTINE_HOST = 'http://'+PREFIX+'converter-routine:8080'
DATA_METADATA_HOST = 'http://'+PREFIX+'data-metadata-service:8080'
PROCESSING_ACCESS_HOST = 'http://'+PREFIX+'distributed-processing-service:8080'
EMAIL_SENDER_HOST = 'http://'+PREFIX+'email-sender-service:8080'
SHARING_HOST = 'http://'+PREFIX+'sharing-service:8080'

RESOURCES_SERVICE = "/api/resources-service/v1"
EXTERNAL_SERVICE = "/api/external-access-service/v1"
WORKSPACE_SERVICE = "/api/workspaces-service/v1"
INGESTOR_SERVICE = "/api/ingestor-service/v1"
BACKOFFICE_SERVICE = "/api/backoffice-service/v1"
PROCESSING_SERVICE = "/api/distributed-processing-service/v1"
EMAIL_SENDER_SERVICE = "/api/email-sender-service/v1"
SHARING_SERVICE = "/api/sharing-service/v1"
CONVERTER_SERVICE = "/api/converter-service/v1"
CONVERTER_ROUTINE_SERVICE = "/api/converter-routine/v1"


def authorizationCall(bearer_token):
    auth_response = requests.get(os.getenv('AAI_SERVICE_ENDPOINT'), headers={'Authorization': bearer_token})
    return Response(auth_response.content, auth_response.status_code)

def isAdmin(bearer_token: str, query: str) -> bool:
    try:
        response = requests.get(BACKOFFICE_HOST + BACKOFFICE_SERVICE + '/user/self?' + query, headers={'Authorization': bearer_token})

        content_str = response.content.decode('utf-8')
        parsed_json = json.loads(content_str)
        # it returns a list with just one item
        user_data = parsed_json[0]

        return user_data.get("isAdmin", False)
    except:
        return False

def authorizationJWT(bearer_token):
    bearer_token = bearer_token.replace("Bearer ", "")
    decoded = jwt.decode(bearer_token, os.getenv('SECURITY_KEY'), algorithms=["HS256"])
    if decoded["issuer"] == "EPOS ICS-C" :
        return Response(decoded, 200)
    else:
        return Response("TOKEN NOT VALID", 401)

def routingrequest(server, method, headers, query, body, request):

    logging.warning('Executing the actual request with the following parameters: ')
    logging.warning('[server]:\n'+str(server)+'\n')
    logging.warning('[method]:\n'+str(method)+'\n')
    logging.warning('[headers]:\n'+str(headers)+'\n')
    logging.warning('[query]:\n'+str(query)+'\n')
    logging.warning('[body]:\n'+str(body)+'\n')
    logging.warning(f'{server}?{query}')    

    if method == 'GET' :
        with requests.get(f'{server}?{query}', data=body, headers=headers, allow_redirects=False, stream=True) as resp:
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]
            logging.warning(resp.content)
            logging.warning(str(len(resp.content)))
            try:
                return (json.loads(resp.content), resp.status_code, headers)
            except Exception as e:
                logging.warning("Exception "+str(e))
                return (json.loads("{}"), resp.status_code, headers)
            #if len(resp.content) == 0:
            #    logging.warning("Empty body for the request")
            #    return (json.loads("{}"), resp.status_code, headers)
            #return (resp.content, resp.status_code, headers)
        #resp = requests.get(f'{server}?{query}', data=body, headers=headers, allow_redirects=False)
    if method == 'POST' :
        if request.is_json:
            resp = requests.post(f'{server}?{query}', json=request.json, headers=headers, allow_redirects=False)
        else:
            resp = requests.post(f'{server}?{query}', json=body, headers=headers, allow_redirects=False)
    if method == 'PUT' :
        if request.is_json:
            resp = requests.put(f'{server}?{query}', json=request.json, headers=headers, allow_redirects=False)
        else:
            resp = requests.put(f'{server}?{query}', json=body, headers=headers, allow_redirects=False)
    if method == 'DELETE' :
        resp = requests.delete(f'{server}?{query}', data=body, headers=headers, allow_redirects=False)

    logging.warning(resp)

    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    logging.warning("RESPONSE DEBUG : "+str(resp.status_code)+" "+resp.headers.get('content-type'))

    #if resp.status_code == 302:
    #    return (json.loads("{}"), resp.status_code, headers)

    if len(resp.content) == 0:
        logging.warning("Empty body for the request")
        return (json.loads("{}"), resp.status_code, headers)
    return (json.loads(resp.content), resp.status_code, headers)
    
