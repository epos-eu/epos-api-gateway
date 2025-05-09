# EPOS API Gateway

The **EPOS API Gateway** is a Python-based microservice within the European Plate Observing System (EPOS) infrastructure. It serves as a centralized entry point, orchestrating requests to various backend services, ensuring secure, efficient, and standardized access to EPOS resources.

---

## Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Key Components](#key-components)
* [Installation](#installation)
* [Configuration](#configuration)
* [Usage](#usage)
* [API Documentation](#api-documentation)
* [Development](#development)
* [Contributing](#contributing)
* [License](#license)

---

## Overview

The EPOS API Gateway is designed to:

* Provide a unified interface for external clients to interact with EPOS services.
* Handle request routing, authentication, and response aggregation.
* Facilitate integration with various backend microservices within the EPOS ecosystem.

---

## Architecture

The API Gateway follows a microservices architecture and is primarily built using Python. It leverages the Swagger Codegen tool to generate server stubs based on OpenAPI specifications, ensuring consistency and ease of maintenance.([epos-eu.github.io][1])

**High-Level Components:**

* **swagger\_server**: Contains the main application logic, including controllers and models.
* **.swagger-codegen**: Houses the Swagger Codegen configurations and templates.
* **Dockerfile**: Defines the containerization setup for deploying the service.
* **CI/CD Pipelines**: Managed via `.gitlab-ci.yml` and GitHub Actions workflows.([GitHub][2])

---

## Key Components

### 1. `swagger_server`

This directory contains the core application code.

* **controllers**: Defines the request handlers for various API endpoints.
* **models**: Contains data models corresponding to the API schemas.
* ****main**.py**: The entry point for running the application.([DZone][3])

### 2. `.swagger-codegen`

Includes configurations and templates used by Swagger Codegen to generate the server stubs.

### 3. `Dockerfile`

Specifies the environment setup for containerizing the application, facilitating consistent deployments.

### 4. CI/CD Pipelines

* **.gitlab-ci.yml**: Defines the GitLab CI/CD pipeline for automated testing and deployment.
* **.github/workflows**: Contains GitHub Actions workflows for continuous integration.

---

## Installation

**Prerequisites:**

* Python 3.7 or higher
* Docker (optional, for containerized deployments)

**Steps:**

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/epos-eu/epos-api-gateway.git
   cd epos-api-gateway
   ```



2. **Create a Virtual Environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```



3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```



4. **Run the Application:**

   ```bash
   python -m swagger_server
   ```



---

## Configuration

The application can be configured using environment variables or configuration files. Key configurations include:

* **API\_HOST**: Host address for the API Gateway.
* **API\_PORT**: Port on which the API Gateway listens.
* **BACKEND\_SERVICE\_URLS**: URLs of the backend services to which requests are routed.([alexdebrie.com][4])

*Note*: Ensure that all necessary configurations are properly set before running the application.

---

## Usage

Once the application is running, it exposes various endpoints as defined in the OpenAPI specification. Clients can interact with these endpoints to access different services provided by the EPOS infrastructure.

**Example:**

```bash
curl http://localhost:8080/api/v1/resource
```



---

## API Documentation

The API Gateway uses Swagger/OpenAPI for API documentation. Once the application is running, you can access the interactive API documentation at:

```
http://localhost:8080/api/v1/ui/
```



This interface allows you to explore the available endpoints, their request/response schemas, and test them directly.

---

## Development

**Project Structure:**

* **`swagger_server/`**: Main application code.
* **`tests/`**: Contains unit and integration tests.
* **`Dockerfile`**: Containerization setup.
* **`.gitlab-ci.yml` & `.github/workflows/`**: CI/CD configurations.

**Running Tests:**

```bash
pytest tests/
```



**Building Docker Image:**

```bash
docker build -t epos-api-gateway .
```



**Running Docker Container:**

```bash
docker run -d -p 8080:8080 epos-api-gateway
```



---

## Contributing

Contributions are welcome! To contribute:

1. **Fork the Repository**: Create your own fork of the project.
2. **Create a Branch**: Develop your feature or fix in a new branch.
3. **Commit Changes**: Ensure your commits are well-documented.
4. **Push to Fork**: Push your changes to your forked repository.
5. **Submit a Pull Request**: Open a pull request detailing your changes.

*Note*: Please adhere to the project's coding standards and include relevant tests for your contributions.

---

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

---

For more information on the EPOS infrastructure and related services, visit the [EPOS Open Source](https://epos-eu.github.io/epos-open-source/) page.

---

[1]: https://epos-eu.github.io/epos-open-source/ "EPOS Platform Open Source"
[2]: https://github.com/epos-eu/epos-api-gateway "epos-api-gateway - GitHub"
[3]: https://dzone.com/articles/introduction-to-api-gateway-in-microservices-architecture "API Gateway in Microservices Architecture"
[4]: https://www.alexdebrie.com/posts/api-gateway-elements/ "A Detailed Overview of AWS API Gateway | DeBrie Advisory"
