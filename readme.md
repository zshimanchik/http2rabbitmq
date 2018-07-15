To run rabbitmq using docker:
`docker run -d --name rabbitmq4http --restart always -p 5672:5672 -e RABBITMQ_DEFAULT_USER=guest -e RABBITMQ_DEFAULT_PASS=guest rabbitmq:3.6.10`

Put configuration into `config.ini`
run `python3 http2rabbitmq/server.py ./config.ini`



