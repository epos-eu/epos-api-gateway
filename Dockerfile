FROM python:3.12-slim

ENV API_VERSION="1.0.0"
ENV API_TITLE="API Gateway"
ENV CONTACT_EMAIL="apis@lists.epos-ip.org"

ENV FLASK_DEBUG=0
ENV OTEL_SDK_DISABLED=true

USER 0

RUN mkdir -p /usr/src/app/swagger_server/swagger_downloaded \
 && mkdir /usr/src/app/swagger_server/swagger_generated \
 && chown -R 1001:1001 /usr/src/app/

WORKDIR /usr/src/app

COPY --chown=1001:1001 . requirements.txt /usr/src/app/

RUN python3 -m pip install --no-cache-dir --upgrade pip \
 && pip3 install --no-cache-dir -r requirements.txt \
 && opentelemetry-bootstrap -a install \
 && groupadd -g 1001 python \
 && useradd -r -u 1001 -m -s /sbin/nologin -g python python \
 && rm -rf \
      /var/cache/apt/* \
      /var/lib/apt/ \
      /var/cache/debconf/templates.dat* \
      /var/cache/debconf/* \
      /tmp/* \
      /var/tmp/* \
 && find /usr/local/lib/python3.12/site-packages/ -type d -name "tests" -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages/ -type f -name "*.exe" -delete \
 && find /usr/local/lib/python3.12/site-packages/ -type f -name "*.pyc" -delete \
 && find /usr/local/lib/python3.12/site-packages/ -type f -name "*.pyo" -delete


COPY --chown=1001:1001 . /usr/src/app

EXPOSE 5000

USER 1001

ENTRYPOINT ["python3"]

CMD ["-m", "swagger_server"]

