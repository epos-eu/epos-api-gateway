import os


def get_description():
    return """
**{api_title} Documentation**

Welcome to the Swagger documentation for the **{api_title}** service. This service consolidates the API definitions of all available services within the EPOS Platform.

In this documentation, you will find the list of services, their respective endpoints, and parameters. It is important to note that:

- **Public Endpoints**: These can be accessed without authentication and provide general information.
- **Restricted Endpoints**: These require user authentication and are designed for specific operations.

Please be aware that some endpoints may not be fully documented at this time. Additionally, these APIs are primarily intended for use by the platform's GUI and not for direct exploration of the data catalog.

Use this documentation as a reference for understanding the available services, but keep in mind that the focus of these endpoints is on supporting the internal functionality of the EPOS Platform.

For more information on how the EPOS Platform works you can reference the documentation of the [EPOS OpenSouce Project](https://epos-eu.github.io/epos-open-source/).
    
""".format(**{"api_title": get_api_title()})


def get_api_title():
    return os.environ["API_TITLE"]


def get_contact_email():
    return os.environ["CONTACT_EMAIL"]


def get_version():
    return os.environ["API_VERSION"]
