import json
import functools
from flask import Flask
from requests import Response
from jsonschema import ValidationError
from connexion.utils import all_json, is_null
from connexion.exceptions import ExtraParameterProblem
from connexion.decorators.validation import ParameterValidator, RequestBodyValidator
from typing import Dict, Any
import logging

app = Flask(__name__)

class Error:
    def __init__(self, status, description):
        self.status = status
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "description": self.description}


def error_response(response: Error) -> Response:
    return app.response_class(
        response=json.dumps(response.to_dict(), default=str),
        status=response.status,
        mimetype='application/json')

def delete_none(_dict):
    """Delete None values recursively from all of the dictionaries, tuples, lists, sets"""
    if isinstance(_dict, dict):
        for key, value in list(_dict.items()):
            if isinstance(value, (list, dict, tuple, set)):
                _dict[key] = delete_none(value)
            elif value is None or key is None:
                del _dict[key]

    elif isinstance(_dict, (list, set, tuple)):
        _dict = type(_dict)(delete_none(item) for item in _dict if item is not None)

    return _dict


class CustomParameterValidator(ParameterValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):

            if self.strict_validation:
                query_errors = self.validate_query_parameter_list(request)
                formdata_errors = self.validate_formdata_parameter_list(request)

                if formdata_errors or query_errors:
                    raise ExtraParameterProblem(formdata_errors, query_errors)

            for param in self.parameters.get('query', []):
                error = self.validate_query_parameter(param, request)
                if error:
                    response = error_response(Error(status=400, description=f'Error: {error}'))
                    return self.api.get_response(response)

            for param in self.parameters.get('path', []):
                error = self.validate_path_parameter(param, request)
                if error:
                    response = error_response(Error(status=400, description=f'Error: {error}'))
                    return self.api.get_response(response)

            for param in self.parameters.get('header', []):
                error = self.validate_header_parameter(param, request)
                if error:
                    response = error_response(Error(status=400, description=f'Error: {error}'))
                    return self.api.get_response(response)

            for param in self.parameters.get('formData', []):
                error = self.validate_formdata_parameter(param, request)
                if error:
                    response = error_response(Error(status=400, description=f'Error: {error}'))
                    return self.api.get_response(response)

            return function(request)

        return wrapper


class CustomRequestBodyValidator(RequestBodyValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            if all_json(self.consumes):
                data = request.json

                if data is None and len(request.body) > 0 and not self.is_null_value_valid:
                    # the body has contents that were not parsed as JSON
                    return error_response(Error(
                        status=415,
                        description="Invalid Content-type ({content_type}), JSON data was expected".format(content_type=request.headers.get("Content-Type", ""))
                    ))
                
                error = self.validate_schema(data, request.url)
                if error and not self.has_default:
                    return error

            response = function(request)
            return response

        return wrapper

    def validate_schema(self, data, url):
        logging.error(data)
        logging.error(type(data))

        copy_data = data

        copy_data = delete_none(copy_data)
        logging.error(copy_data)
        logging.error(data)

        data = copy_data

        if self.is_null_value_valid and is_null(data):
            return None

        try:
            self.validator.validate(data)
        except ValidationError as exception:
            description = f'Validation error. Attribute "{exception.validator_value}" return this error: "{exception.message}"'
            print(description)
            return error_response(Error(
                status=400,
                description=description
            ))

        return None