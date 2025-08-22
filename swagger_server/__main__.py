#!/usr/bin/env python3

import connexion

import logging
from urllib import request
import json
import random
import string
import yaml
import traceback
import requests
from flask_cors import CORS
import sys

from swagger_server.controllers.feedback_controller import submit_feedback
from swagger_server.controllers import routing_request
from connexion.decorators.response import ResponseValidator
from swagger_server.custom_validators import CustomParameterValidator, CustomRequestBodyValidator

import os

import hiyapyco

from swagger_server.swagger_description import get_description, get_version, get_contact_email, get_api_title

security_dict = yaml.safe_load('''
        security:
        - bearerAuth: []
        ''')

static_ogc_parameter = yaml.safe_load('''
        parameters:
        - name: instance_id
          in: path
          description: the id of item to be executed
          required: true
          style: simple
          schema:
            type: string
''')

def getenv_split(name: str, sep: str = ":") -> tuple[bool, bool] | None:
    raw = os.getenv(name)
    if raw is None:
        return None

    if not is_AAI_Enabled:
        return False, False

    try:
        first, second = raw.split(sep, 1)
    except ValueError:  # not exactly two parts
        logging.warning(f"{name} must contain exactly two values separated by {sep!r}, "
            f"e.g. 'true:false'; got {raw!r}. Considering it as not set")
        return None

    truthy = {"1", "true", "yes", "on"}
    to_bool = lambda s: s.strip().lower() in truthy

    return to_bool(first), to_bool(second)

is_AAI_Enabled = os.getenv('IS_AAI_ENABLED') == 'true'

resources_api_setup = getenv_split('LOAD_RESOURCES_API')
ingestor_api_setup = getenv_split('LOAD_INGESTOR_API')
external_api_setup = getenv_split('LOAD_EXTERNAL_ACCESS_API')
backoffice_api_setup = getenv_split('LOAD_BACKOFFICE_API')
processing_api_setup = getenv_split('LOAD_PROCESSING_API')
sharing_api_setup = getenv_split('LOAD_SHARING_API')
converter_api_setup = getenv_split('LOAD_CONVERTER_API')
monitoring_api_setup = getenv_split('LOAD_MONITORING_API')
email_sender_api_setup = getenv_split('LOAD_EMAIL_SENDER_API')
submit_feedback_api_setup = getenv_split('LOAD_SUBMIT_FEEDBACK_API')

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
    new_key = new_key.replace("id","instance_id")
    d[new_key] = d.pop(old_key, default_value)

def remove_key(d, key):
    d.pop(key)

def add_method_to_dynamic_controller(randomname, host, service, isauth, only_admin: bool = False) :
    method_string = "\ndef "+randomname+"(meta_id=None, instance_id=None, plugin_id=None, relation_id=None):"
    method_string+= "\n    server = '"+host+service+"'+connexion.request.base_url.split('/api/v1')[1]"
    if isauth:
        if only_admin:
            method_string+= "\n    return call_redirect(connexion.request.query_string, True, server, True)"
        else:
            method_string+= "\n    return call_redirect(connexion.request.query_string, True, server, False)"
    else:
        method_string+= "\n    return call_redirect(connexion.request.query_string, False, server, False)"
    with open("./swagger_server/controllers/dynamic_controller.py", "a") as myfile:
        myfile.write(method_string)

def manipulate_and_generate_yaml(json_loaded, filename, service, host, isauth: bool, only_admin: bool = False) :
    json_loaded['info']['title'] = get_api_title()
    json_loaded['info']['description'] = get_description()
    json_loaded['info']['version'] = get_version()
    try:
        json_loaded['info']['contact']['email'] = get_contact_email()
    except:
        json_loaded['info']['contact'] = {"email" : get_contact_email()}
    json_loaded['servers'][0]['url'] = 'http://localhost:5000/api/v1'

    for key, value in list(json_loaded['paths'].items()):
        print(key)
        #cleanup paths
        if 'head' in json_loaded['paths'][key]: json_loaded['paths'][key].pop('head')
        #if 'options' in json_loaded['paths'][key]: json_loaded['paths'][key].pop('options')
        if 'patch' in json_loaded['paths'][key]: json_loaded['paths'][key].pop('patch')
        if 'trace' in json_loaded['paths'][key]: json_loaded['paths'][key].pop('trace')
        if 'tna' in key :
            remove_key(json_loaded['paths'], key)
        #if 'ogcexecute' in key:
        #    change_dict_key_and_id(json_loaded['paths'], key, os.getenv('BASECONTEXT')+service)
        change_dict_key(json_loaded['paths'], key, service)

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
                randomname = ''.join(random.choice(string.ascii_lowercase) for _ in range(30))
                if "monitoring" in key and monitoring_api_setup:
                    add_method_to_dynamic_controller(
                        randomname,
                        host,
                        service,
                        monitoring_api_setup[0],
                        monitoring_api_setup[1],
                    )
                else:
                    if 'get' in value and 'parameters' in value['get'] and isinstance(value['get']['parameters'], list) and len(value['get']['parameters']) > 0 and 'in' in value['get']['parameters'][0] and 'name' in value['get']['parameters'][0] and value['get']['parameters'][0]['in'] == 'path':
                        add_method_to_dynamic_controller(randomname, host, service, isauth, only_admin)
                    else :
                        add_method_to_dynamic_controller(randomname, host, service, isauth, only_admin)
                json_loaded['paths'][key]['get']['operationId'] = randomname
                json_loaded['paths'][key]['get']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth or ("monitoring" in key and monitoring_api_setup and monitoring_api_setup[0]):
                    json_loaded['paths'][key]['get'].update(security_dict)
            if 'options' in json_loaded['paths'][key]:
                randomname = ''.join(random.choice(string.ascii_lowercase) for _ in range(30))
                if "monitoring" in key and monitoring_api_setup:
                    add_method_to_dynamic_controller(
                        randomname,
                        host,
                        service,
                        monitoring_api_setup[0],
                        monitoring_api_setup[1],
                    )
                else:
                    if 'options' in value and 'parameters' in value['options'] and isinstance(value['options']['parameters'], list) and len(value['options']['parameters']) > 0 and 'in' in value['get']['parameters'][0] and 'name' in value['options']['parameters'][0] and value['options']['parameters'][0]['in'] == 'path':
                        add_method_to_dynamic_controller(randomname,host,service,isauth, only_admin)
                    else :
                        add_method_to_dynamic_controller(randomname,host,service,isauth, only_admin)
                json_loaded['paths'][key]['options']['operationId'] = randomname
                json_loaded['paths'][key]['options']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth or ("monitoring" in key and monitoring_api_setup and monitoring_api_setup[0]):
                    json_loaded['paths'][key]['options'].update(security_dict)
            if 'post' in json_loaded['paths'][key]:
                if service == "/submit_feedback":
                    path = "/submit_feedback"
                    json_loaded['paths'][path]['post']['operationId'] = "submit_feedback"
                    json_loaded['paths'][path]['post']['x-openapi-router-controller'] = "swagger_server.controllers.feedback_controller"
                    continue

                randomname = ''.join(random.choice(string.ascii_lowercase) for _ in range(30))
                add_method_to_dynamic_controller(randomname,host,service,isauth, only_admin)
                json_loaded['paths'][key]['post']['operationId'] = randomname
                json_loaded['paths'][key]['post']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth :
                    json_loaded['paths'][key]['post'].update(security_dict)
            if 'put' in json_loaded['paths'][key]:
                randomname = ''.join(random.choice(string.ascii_lowercase) for _ in range(30))
                if 'put' in value and 'parameters' in value['put'] and isinstance(value['put']['parameters'],list) and len(value['put']['parameters']) > 0 and 'in' in value['put']['parameters'][0] and 'name' in value['put']['parameters'][0] and value['put']['parameters'][0]['in'] == 'path':
                    add_method_to_dynamic_controller(randomname, host, service, isauth, only_admin)
                else:
                    add_method_to_dynamic_controller(randomname, host, service, isauth, only_admin)
                json_loaded['paths'][key]['put']['operationId'] = randomname
                json_loaded['paths'][key]['put']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth :
                    json_loaded['paths'][key]['put'].update(security_dict)
            if 'delete' in json_loaded['paths'][key]:
                randomname = ''.join(random.choice(string.ascii_lowercase) for _ in range(30))
                add_method_to_dynamic_controller(randomname,host,service,isauth, only_admin)
                json_loaded['paths'][key]['delete']['operationId'] = randomname
                json_loaded['paths'][key]['delete']['x-openapi-router-controller'] = "swagger_server.controllers.dynamic_controller"
                if isauth :
                    json_loaded['paths'][key]['delete'].update(security_dict)

    with open(filename, 'w') as file:
        documents = yaml.dump(json_loaded, file)




def load_configuration():
    conf_array = []

    if converter_api_setup :
        try:
            item = request.urlopen(routing_request.CONVERTER_HOST+routing_request.CONVERTER_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded,
                r'./swagger_server/swagger_downloaded/converter.yaml',
                routing_request.CONVERTER_SERVICE,
                routing_request.CONVERTER_HOST,
                converter_api_setup[0],
                converter_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/converter.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of converter host")
            traceback.print_exc()
            sys.exit()
        try:
            item = request.urlopen(routing_request.CONVERTER_ROUTINE_HOST+routing_request.CONVERTER_ROUTINE_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded, 
                r'./swagger_server/swagger_downloaded/converter-routine.yaml',
                routing_request.CONVERTER_ROUTINE_SERVICE, 
                routing_request.CONVERTER_ROUTINE_HOST, 
                converter_api_setup[0],
                converter_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/converter-routine.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of converter host")
            traceback.print_exc()
            sys.exit()
    if resources_api_setup:
        try:
            item = request.urlopen(routing_request.RESOURCES_HOST+routing_request.RESOURCES_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded,
                r'./swagger_server/swagger_downloaded/resources.yaml',
                routing_request.RESOURCES_SERVICE,
                routing_request.RESOURCES_HOST,
                resources_api_setup[0],
                resources_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/resources.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of resource host")
            traceback.print_exc()
            sys.exit()
    if ingestor_api_setup:
        try:
            item = request.urlopen(routing_request.INGESTOR_HOST+routing_request.INGESTOR_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded, 
                r'./swagger_server/swagger_downloaded/ingestor.yaml',
                routing_request.INGESTOR_SERVICE, 
                routing_request.INGESTOR_HOST, 
                ingestor_api_setup[0],
                ingestor_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/ingestor.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of ingestor host")
            traceback.print_exc()
            sys.exit()
    if external_api_setup:
        try:
            item = request.urlopen(routing_request.EXTERNAL_ACCESS_HOST+routing_request.EXTERNAL_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded,
                r'./swagger_server/swagger_downloaded/external.yaml',
                routing_request.EXTERNAL_SERVICE,
                routing_request.EXTERNAL_ACCESS_HOST,
                external_api_setup[0],
                external_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/external.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of external access host")
            traceback.print_exc()
            sys.exit()
    if backoffice_api_setup:
        try:
            item = request.urlopen(routing_request.BACKOFFICE_HOST+routing_request.BACKOFFICE_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded, 
                r'./swagger_server/swagger_downloaded/backoffice.yaml',
                routing_request.BACKOFFICE_SERVICE, 
                routing_request.BACKOFFICE_HOST, 
                backoffice_api_setup[0],
                backoffice_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/backoffice.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of backoffice host")
            traceback.print_exc()
            sys.exit()
    if processing_api_setup:
        try:
            item = request.urlopen(routing_request.PROCESSING_ACCESS_HOST+routing_request.PROCESSING_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded,
                r'./swagger_server/swagger_downloaded/processing.yaml',
                routing_request.PROCESSING_SERVICE,
                routing_request.PROCESSING_ACCESS_HOST,
                processing_api_setup[0],
                processing_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/processing.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of processing host")
            traceback.print_exc()
            sys.exit()
    if email_sender_api_setup:
        try:
            item = request.urlopen(routing_request.EMAIL_SENDER_HOST+routing_request.EMAIL_SENDER_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded, 
                r'./swagger_server/swagger_downloaded/sender.yaml',
                routing_request.EMAIL_SENDER_SERVICE, 
                routing_request.EMAIL_SENDER_HOST, 
                email_sender_api_setup[0],
                email_sender_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/sender.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of email sender host")
            traceback.print_exc()
            sys.exit()
    if sharing_api_setup:
        try:
            item = request.urlopen(routing_request.SHARING_HOST+routing_request.SHARING_SERVICE+"/api-docs")
            json_loaded = json.loads(item.read())
            manipulate_and_generate_yaml(
                json_loaded,
                r'./swagger_server/swagger_downloaded/sharing.yaml',
                routing_request.SHARING_SERVICE,
                routing_request.SHARING_HOST,
                sharing_api_setup[0],
                sharing_api_setup[1],
            )
            conf_array.append(open("./swagger_server/swagger_downloaded/sharing.yaml", "r", encoding="utf-8").read())
        except:
            logging.error("Error executing fetch of sharing host")
            traceback.print_exc()
            sys.exit()

    
    try:
            
        conf_array.append(open("./swagger_server/swagger_partial/feedback_services.yaml", "r", encoding="utf-8").read())
    except:
            logging.error("Error executing fetch of feedback host")
            traceback.print_exc()
            sys.exit()



    # ADD Security component
    conf_array.append(open("./swagger_server/swagger_partial/security_component.yaml", "r", encoding="utf-8").read())

    conf = hiyapyco.load(conf_array, method=hiyapyco.METHOD_MERGE)

    if os.path.exists('./swagger_server/swagger_generated/swagger_built.yaml'):
        os.remove('./swagger_server/swagger_generated/swagger_built.yaml')

    with open('./swagger_server/swagger_generated/swagger_built.yaml', 'w') as file:
        file.write(hiyapyco.dump(conf))
        file.close()

def resources_health():
    resp = requests.get(routing_request.RESOURCES_HOST+routing_request.RESOURCES_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def ingestor_health():
    resp = requests.get(routing_request.INGESTOR_HOST+routing_request.INGESTOR_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def exernal_access_health():
    resp = requests.get(routing_request.EXTERNAL_ACCESS_HOST+routing_request.EXTERNAL_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def converter_health():
    resp = requests.get(routing_request.CONVERTER_HOST+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def backoffice_health():
    resp = requests.get(routing_request.BACKOFFICE_HOST+routing_request.BACKOFFICE_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def data_metadata_service_health():
    resp = requests.get(routing_request.DATA_METADATA_HOST+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def processing_health():
    resp = requests.get(routing_request.PROCESSING_ACCESS_HOST+routing_request.PROCESSING_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def email_sender_health():
    resp = requests.get(routing_request.EMAIL_SENDER_HOST+routing_request.EMAIL_SENDER_SERVICE+"/actuator/health", allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]

    return (json.loads(resp.text), resp.status_code, headers)

def main():
    validator_map = {
        'parameter': CustomParameterValidator,
        'body': CustomRequestBodyValidator,
        'response': ResponseValidator,
    }

    load_configuration()

    app = connexion.App(__name__, specification_dir='./swagger_generated/')
    #app.app.json=JSONEncoder
    app.add_api('swagger_built.yaml', arguments={'title': 'API Gateway'},validator_map=validator_map, pythonic_params=True)
    flask_app = app.app
    CORS(flask_app)
    app.add_url_rule("/api/v1/submit_feedback", "submit_feedback", submit_feedback, methods=["POST"])
    app.add_url_rule("/api/v1/resources-service/health", "resources_health", resources_health)
    app.add_url_rule("/api/v1/ingestor-service/health", "ingestor_health", ingestor_health)
    app.add_url_rule("/api/v1/external-access-service/health", "exernal_access_health", exernal_access_health)
    app.add_url_rule("/api/v1/converter-service/health", "converter_health", converter_health)
    app.add_url_rule("/api/v1/backoffice-service/health", "backoffice_health", backoffice_health)
    app.add_url_rule("/api/v1/data-metadata-service/health", "data_metadata_service_health", data_metadata_service_health)
    app.add_url_rule("/api/v1/processing-access-service/health", "processing_health", processing_health)
    app.add_url_rule("/api/v1/email-sender-service/health", "email_sender_health", email_sender_health)
    path=os.getenv('BASECONTEXT', '')
    proxied = ReverseProxied(
        flask_app.wsgi_app,
        script_name=path
    )
    flask_app.wsgi_app = proxied
    app.run(port=5000)


if __name__ == '__main__':
    main()
