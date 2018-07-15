FROM python:3.6

RUN mkdir /app
COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt
COPY http2rabbitmq /app/http2rabbitmq/
COPY config.ini /app/config.ini

CMD python -u /app/http2rabbitmq/server.py /app/config.ini
