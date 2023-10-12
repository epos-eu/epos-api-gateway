import connexion
import logging
import urllib
import json
import os
import io
import base64
import requests
from flask import Response, send_file, make_response, jsonify

from swagger_server import util
from swagger_server.controllers import routing_request

def call_redirect(query, isauthrequest, server):

    query = query.decode("utf-8")
    query = urllib.parse.unquote(query)

    if isauthrequest :
        try:
            auth_response = ""
            if "monitoring" in connexion.request.path:
                auth_response = routing_request.authorizationJWT(connexion.request.headers['Authorization'])
            else:
                auth_response = routing_request.authorizationCall(connexion.request.headers['Authorization'])
            
            if auth_response.status_code == 401 :
                return ("Wrong or expired token provided", 401, connexion.request.headers.items())
            else:
                if "monitoring" not in connexion.request.path:
                    json_payload = json.loads(auth_response.response[0])
                    query += "&userId=" + json_payload['eduPersonUniqueId']
                if "sender" in connexion.request.path:
                    json_payload = json.loads(auth_response.response[0])
                    query += "&userEmail=" + json_payload['email'] + "&firstName=" + json_payload['firstname'] + "&lastName=" + json_payload['lastName']

        except:
            return ("No authentication token provided or error while checking it...", 401, connexion.request.headers.items())

    return routing_request.routingrequest(server,
                            connexion.request.method, 
                            connexion.request.headers, 
                            query,
                            connexion.request.form,
                            connexion.request)

def tcsconnections_ogc_execute_get_using_get(item):  # noqa: E501
    """queries on external services endpoint

    this endpoint enable queries on external services from ics-c to tcs to get data to be visualized or downloaded # noqa: E501

    :param id: the id of item to be executed
    :type id: str

    :rtype: str
    """

    query = connexion.request.query_string.decode("utf-8") 
    query = urllib.parse.unquote(query)

    server = routing_request.EXTERNAL_ACCESS_HOST+os.getenv('BASECONTEXT')+routing_request.EXTERNAL_SERVICE+connexion.request.base_url.split('/api/v1')[1]
    
    logging.warning('Executing the actual request with the following parameters: ')
    logging.warning('[server]:\n'+str(server)+'\n')
    logging.warning('[method]:\n'+str(connexion.request.method)+'\n')
    logging.warning('[headers]:\n'+str(connexion.request.headers)+'\n')
    logging.warning('[query]:\n'+str(query)+'\n')
    logging.warning('[body]:\n'+str(connexion.request.form)+'\n')

    logging.warning(f'{server}?{query}')    

    resp = requests.get(f'{server}?{query}', data=connexion.request.form, headers=connexion.request.headers, allow_redirects=False)

    logging.warning(str(resp.headers))
    if str(resp.headers['content-type']) == "image/png" :
        pad = len(resp.content)%4
        text_len = len(resp.content)
        code = resp.text[:text_len - pad]
        b = base64.urlsafe_b64decode(code.strip())
        #b = b.encode('utf-8')
        buf = io.BytesIO(b)
        buf.seek(0)
        return send_file(buf, mimetype="image/png")
    else:
         return Response(response=resp.content, status=resp.status_code,  mimetype=resp.headers['content-type'])
  
