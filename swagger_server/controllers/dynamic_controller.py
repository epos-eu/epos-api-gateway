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

def call_redirect(query, isauthrequest, server, only_admin: bool = False):
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
                    query += "&email=" + json_payload['email'] + "&firstName=" + json_payload['firstname'] + "&lastName=" + json_payload['lastName']

                    if only_admin:
                        isAdmin = routing_request.isAdmin(connexion.request.headers['Authorization'], query)
                        if not isAdmin:
                            return ("Only admins have access to this endpoint. You are not an admin.", 401, connexion.request.headers.items())

                if "sender" in connexion.request.path:
                    json_payload = json.loads(auth_response.response[0])
                    query += "&userEmail=" + json_payload['email'] + "&firstName=" + json_payload['firstname'] + "&lastName=" + json_payload['lastName']

        except:
            return ("No authentication token provided or error while checking it...", 401, connexion.request.headers.items())
    
    if "search" in connexion.request.path:
        try:
            auth_response = ""
            auth_response = routing_request.authorizationCall(connexion.request.headers['Authorization'])
            if auth_response.status_code == 401 :
                print("Wrong or expired auth token provided for search endpoints, skipping auth")
            else:
                json_payload = json.loads(auth_response.response[0])
                query += "&userId=" + json_payload['eduPersonUniqueId']
        except:
            print("No auth token provided for search endpoints, skipping auth")


    return routing_request.routingrequest(server,
                            connexion.request.method, 
                            connexion.request.headers, 
                            query,
                            connexion.request.get_data(),
                            connexion.request)

def tcsconnections_ogc_execute_get_using_get(instance_id=None):  # noqa: E501
    """queries on external services endpoint

    this endpoint enable queries on external services from ics-c to tcs to get data to be visualized or downloaded # noqa: E501

    :param id: the id of item to be executed
    :type id: str

    :rtype: str
    """

    query = connexion.request.query_string.decode("utf-8") 
    query = urllib.parse.unquote(query)

    server = routing_request.EXTERNAL_ACCESS_HOST+routing_request.EXTERNAL_SERVICE+connexion.request.base_url.split('/api/v1')[1]
    
    logging.warning('Executing the actual request with the following parameters: ')
    logging.warning('[server]:\n'+str(server)+'\n')
    logging.warning('[method]:\n'+str(connexion.request.method)+'\n')
    logging.warning('[headers]:\n'+str(connexion.request.headers)+'\n')
    logging.warning('[query]:\n'+str(query)+'\n')
    logging.warning('[body]:\n'+str(connexion.request.form)+'\n')

    logging.warning(f'{server}?{query}')    

    #resp = requests.get(f'{server}?{query}', data=connexion.request.form, headers=connexion.request.headers, allow_redirects=False)

    #logging.warning(str(resp.headers))
    
    return routing_request.routingrequest(server,
                            connexion.request.method, 
                            connexion.request.headers, 
                            query,
                            connexion.request.form,
                            connexion.request)
  
