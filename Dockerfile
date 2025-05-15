FROM python:3.12.0a7-slim-buster

ENV API_VERSION="1.0.0"
ENV API_TITLE="API Gateway"
ENV CONTACT_EMAIL="apis@lists.epos-ip.org"

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip3 install --upgrade pip
RUN apt-get update && apt-get install -y gcc libffi-dev
RUN pip3 install --no-cache-dir -r requirements.txt

RUN pip3 install opentelemetry-distro
RUN pip3 install opentelemetry-exporter-otlp-proto-http
RUN opentelemetry-bootstrap -a install

COPY . /usr/src/app

RUN mkdir ./swagger_server/swagger_downloaded
RUN mkdir ./swagger_server/swagger_generated

EXPOSE 5000

ENTRYPOINT ["python3"]

CMD ["-m", "swagger_server"]

