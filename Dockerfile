FROM python:3.12.0a7-slim-buster

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip3 install --upgrade pip
RUN apt-get update && apt-get install -y gcc libffi-dev
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

RUN mkdir ./swagger_server/swagger_downloaded
RUN mkdir ./swagger_server/swagger_generated

EXPOSE 5000

ENTRYPOINT ["python3"]

CMD ["-m", "swagger_server"]

