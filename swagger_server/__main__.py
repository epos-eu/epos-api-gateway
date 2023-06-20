#!/usr/bin/env python3

import connexion

import logging
import urllib
import json
import random
import string
import yaml
import traceback
import requests

from swagger_server.controllers import routing_request

import os

import hiyapyco

from swagger_server import encoder

security_dict = yaml.safe_load('''
        security:
        - bearerAuth: []
        ''')

static_ogc_parameter = yaml.safe_load('''
        parameters:
        - name: item
          in: path
          description: the id of item to be executed
          required: true
          style: simple
          schema:
            type: string
''')

class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    reverse proxy to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.
    In nginx:
    location /proxied {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Path /proxied;
    }
    :param app: the WSGI application
    :param script_name: override the default script name (path)
    :param scheme: override the default scheme
    :param server: override the default server
    '''

    def __init__(self, app, script_name=None, scheme=None, server=None):
        self.app = app
        self.script_name = script_name
        self.scheme = scheme
        self.server = server

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_FORWARDED_PATH', '') or self.script_name
        if script_name:
            environ['SCRIPT_NAME'] = "/" + script_name.lstrip("/")
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO_OLD'] = path_info
                environ['PATH_INFO'] = path_info[len(script_name):]
        scheme = environ.get('HTTP_X_SCHEME', '') or self.scheme
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        server = environ.get('HTTP_X_FORWARDED_SERVER', '') or self.server
        if server:
            environ['HTTP_HOST'] = server
        return self.app(environ, start_response)

def change_dict_key(d, old_key, to_be_replaced, replacing="", default_value=None):
    new_key = old_key.replace(to_be_replaced,replacing)
    d[new_key] = d.pop(old_key, default_value)

def change_dict_key_and_id(d, old_key, to_be_replaced, replacing="", default_value=None):
    new_key = old_key.replace(to_be_replaced,replacing)
    new_key = new_key.replace("id","item")
    d[new_key] = d.pop(old_key, default_value)

def remove_key(d, key):
    d.pop(key)

def add_method_to_dynamic_controller(randomname, host, service, isauth, path_parameter_name = '') :
    method_string = "\ndef "+randomname+"(instance_id=None):"
    method_string+= "\n    server = '"+host+"'+os.getenv('BASECONTEXT')+'"+service+"'+connexion.request.base_url.split('/api/v1')[1]"
    if isauth :
        method_string+= "\n    return call_redirect(connexion.request.query_string, True, server)"
    else:
        method_string+= "\n    return call_redirect(connexion.request.query_string, False, server)"
    with open("./swagger_server/controllers/dynamic_controller.py", "a") as myfile:
        myfile.write(method_string)

def manipulate_and_generate_yaml(json_loaded, filename, service, host, isauth) :
    json_loaded['info']['title'] = 'API Gateway'
    json_loaded['info']['description'] = 'This is the API Gateway Swagger page.'
    json_loaded['info']['version'] = '1.0.0'
    json_loaded['servers'][0]['url'] = 'http://localhost:5000/api/v1'
    for key, value in list(json_loaded['paths'].items()):
        print(key)
        if 'tna' in key :
            remove_key(json_loaded['paths'], key)
        if 'ogcexecute' in key:
            change_dict_key_and_id(json_loaded['paths'], key, os.getenv('BASECONTEXT')+service)
        change_dict_key(json_loaded['paths'], key, os.getenv('BASECONTEXT')+service)

    # CLEANUP Empty endpoints
    for key, value in list(json_loaded['paths'].items()):
        if value == None:
            del json_loaded['paths'][key]

    #CHANGE operationID
    for key, value in list(json_loaded['paths'].items()):
        if "ogcexecute" in key:
            json_loaded['paths'][key]['get']['operationId'] = "tcsconnections_ogc_execute_get_using_get"
            json_loaded['paths'][key]['get'].pop('parameters')
            json_loaded['paths'][key]['get'].update(static_ogc_parameter)
            json_loaded['paths'][key]['get']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
        else:
            if 'get' in json_loaded['paths'][key]:
                randomname = ''.join(random.choice(string.ascii_lowercase) for i in range(30))
                if "monitoring" in key:
                    add_method_to_dynamic_controller(randomname,host,service,os.getenv('IS_MONITORING_AUTH') == 'true')
                else:
                    if 'get' in value and 'parameters' in value['get'] and isinstance(value['get']['parameters'], list) and len(value['get']['parameters']) > 0 and 'in' in value['get']['parameters'][0] and 'name' in value['get']['parameters'][0] and value['get']['parameters'][0]['in'] == 'path':
                        add_method_to_dynamic_controller(randomname,host,service,isauth, value['get']['parameters'][0]['name'])
                    else :
                        add_method_to_dynamic_controller(randomname,host,service,isauth)
                json_loaded['paths'][key]['get']['operationId'] = randomname
                json_loaded['paths'][key]['get']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth or ("monitoring" in key and os.getenv('IS_MONITORING_AUTH') == 'true'):
                    json_loaded['paths'][key]['get'].update(security_dict)
            if 'post' in json_loaded['paths'][key]:
                randomname = ''.join(random.choice(string.ascii_lowercase) for i in range(30))
                add_method_to_dynamic_controller(randomname,host,service,isauth)
                json_loaded['paths'][key]['post']['operationId'] = randomname
                json_loaded['paths'][key]['post']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth :
                    json_loaded['paths'][key]['post'].update(security_dict)
            if 'put' in json_loaded['paths'][key]:
                randomname = ''.join(random.choice(string.ascii_lowercase) for i in range(30))
                if 'put' in value and 'parameters' in value['put'] and isinstance(value['put']['parameters'],list) \
                        and len(value['put']['parameters']) > 0 and 'in' in value['put']['parameters'][0] and 'name' in \
                        value['put']['parameters'][0] and value['put']['parameters'][0]['in'] == 'path':
                    add_method_to_dynamic_controller(randomname, host, service, isauth,
                                                     value['put']['parameters'][0]['name'])
                else:
                    add_method_to_dynamic_controller(randomname, host, service, isauth)
                json_loaded['paths'][key]['put']['operationId'] = randomname
                json_loaded['paths'][key]['put']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth :
                    json_loaded['paths'][key]['put'].update(security_dict)
            if 'delete' in json_loaded['paths'][key]:
                randomname = ''.join(random.choice(string.ascii_lowercase) for i in range(30))
                add_method_to_dynamic_controller(randomname,host,service,isauth)
                json_loaded['paths'][key]['delete']['operationId'] = randomname
                json_loaded['paths'][key]['delete']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth :
                    json_loaded['paths'][key]['delete'].update(security_dict)

    with open(filename, 'w') as file:
        documents = yaml.dump(json_loaded, file)

def load_configuration():

    conf_array = []
    
    if os.getenv('LOAD_RESOURCES_API') == "true" : 
        try:
            item = urllib.request.urlopen(routing_request.RESOURCES_HOST+os.getenv('BASECONTEXT')+routing_request.RESOURCES_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(json_loaded, r'./swagger_server/swagger_downloaded/resources.yaml',routing_request.RESOURCES_SERVICE, routing_request.RESOURCES_HOST, False)
            conf_array.append(open("./swagger_server/swagger_downloaded/resources.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of resource host")
            traceback.print_exc()
    if os.getenv('LOAD_INGESTOR_API') == "true" : 
        try:
            item = urllib.request.urlopen(routing_request.INGESTOR_HOST+os.getenv('BASECONTEXT')+routing_request.INGESTOR_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(json_loaded, r'./swagger_server/swagger_downloaded/ingestor.yaml',routing_request.INGESTOR_SERVICE, routing_request.INGESTOR_HOST, False)
            conf_array.append(open("./swagger_server/swagger_downloaded/ingestor.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of ingestor host")
            traceback.print_exc()
    if os.getenv('LOAD_EXTERNAL_ACCESS_API') == "true" : 
        try:
            item = urllib.request.urlopen(routing_request.EXTERNAL_ACCESS_HOST+os.getenv('BASECONTEXT')+routing_request.EXTERNAL_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(json_loaded, r'./swagger_server/swagger_downloaded/external.yaml',routing_request.EXTERNAL_SERVICE, routing_request.EXTERNAL_ACCESS_HOST, False)
            conf_array.append(open("./swagger_server/swagger_downloaded/external.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of external access host")
            traceback.print_exc()
    if os.getenv('LOAD_BACKOFFICE_API') == "true" :
        try:
            item = urllib.request.urlopen(routing_request.BACKOFFICE_HOST+os.getenv('BASECONTEXT')+routing_request.BACKOFFICE_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(json_loaded, r'./swagger_server/swagger_downloaded/backoffice.yaml',routing_request.BACKOFFICE_SERVICE, routing_request.BACKOFFICE_HOST, os.getenv('IS_AAI_ENABLED') == 'true')
            conf_array.append(open("./swagger_server/swagger_downloaded/backoffice.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of backoffice host")
            traceback.print_exc()
    if os.getenv('LOAD_PROCESSING_API') == "true" :
        try:
            item = urllib.request.urlopen(routing_request.PROCESSING_ACCESS_HOST+os.getenv('BASECONTEXT')+routing_request.PROCESSING_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(json_loaded, r'./swagger_server/swagger_downloaded/processing.yaml',routing_request.PROCESSING_SERVICE, routing_request.PROCESSING_ACCESS_HOST, os.getenv('IS_AAI_ENABLED') == 'true')
            conf_array.append(open("./swagger_server/swagger_downloaded/processing.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of processing host")
            traceback.print_exc()


    # ADD Security component
    conf_array.append(open("./swagger_server/swagger_partial/security_component.yaml", "r", encoding="utf-8").read())

    conf = hiyapyco.load(conf_array, method=hiyapyco.METHOD_MERGE)

    if os.path.exists('./swagger_server/swagger_generated/swagger_built.yaml'):
        os.remove('./swagger_server/swagger_generated/swagger_built.yaml')

    with open('./swagger_server/swagger_generated/swagger_built.yaml', 'w') as file:
        file.write(hiyapyco.dump(conf))
        file.close()

def resources_health():
    resp = requests.get(routing_request.RESOURCES_HOST+os.getenv('BASECONTEXT')+routing_request.RESOURCES_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def ingestor_health():
    resp = requests.get(routing_request.INGESTOR_HOST+os.getenv('BASECONTEXT')+routing_request.INGESTOR_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def exernal_access_health():
    resp = requests.get(routing_request.EXTERNAL_ACCESS_HOST+os.getenv('BASECONTEXT')+routing_request.EXTERNAL_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def converter_health():
    resp = requests.get(routing_request.CONVERTER_HOST+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def backoffice_health():
    resp = requests.get(routing_request.BACKOFFICE_HOST+os.getenv('BASECONTEXT')+routing_request.BACKOFFICE_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def data_metadata_service_health():
    resp = requests.get(routing_request.DATA_METADATA_HOST+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def processing_health():
    resp = requests.get(routing_request.PROCESSING_ACCESS_HOST+os.getenv('BASECONTEXT')+routing_request.PROCESSING_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def main():

    load_configuration()

    app = connexion.App(__name__, specification_dir='./swagger_generated/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger_built.yaml', arguments={'title': 'API Gateway'}, pythonic_params=True)
    flask_app = app.app
    app.add_url_rule("/api/v1/resources-service/health", "resources_health", resources_health)
    app.add_url_rule("/api/v1/ingestor-service/health", "ingestor_health", ingestor_health)
    app.add_url_rule("/api/v1/external-access-service/health", "exernal_access_health", exernal_access_health)
    app.add_url_rule("/api/v1/converter-service/health", "converter_health", converter_health)
    app.add_url_rule("/api/v1/backoffice-service/health", "backoffice_health", backoffice_health)
    app.add_url_rule("/api/v1/data-metadata-service/health", "data_metadata_service_health", data_metadata_service_health)
    app.add_url_rule("/api/v1/processing-access-service/health", "processing_health", processing_health)
    path=os.getenv('BASECONTEXT')
    proxied = ReverseProxied(
        flask_app.wsgi_app,
        script_name=path
    )
    flask_app.wsgi_app = proxied
    app.run(port=5000)

if __name__ == '__main__':
    main()
