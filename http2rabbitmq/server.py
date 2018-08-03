import asyncio
import json
import logging
import os
import sys

import aio_pika
from aiohttp import web

logger = logging.getLogger(__name__)


async def handle(request):
    answer_queue = await request.app['rabbit'].declare_queue(exclusive=True, auto_delete=True)
    await request.app['rabbit'].default_exchange.publish(
        aio_pika.Message(
            body=json.dumps({
                'method': request.method,
                'url': str(request.url),
                'query': dict(request.query),
                'headers': dict(request.headers),
                'body': await request.text(),
                'answer_queue': answer_queue.name,
            }).encode()
        ),
        routing_key=config.rabbitmq_request_queue
    )
    retry = 0
    answer = await answer_queue.get(timeout=5, fail=False)
    while answer is None and retry < 10:
        await asyncio.sleep(0.3)
        retry += 1
        answer = await answer_queue.get(timeout=5, fail=False)

    if answer is not None:
        logger.debug('answer: %r', answer.body)
        body = answer.body
    else:
        logger.debug('no answer received from rabbitmq')
        body = '{"response": "{}"}'
    data = json.loads(body)
    return web.Response(text=data['response'], headers={'Content-Type':'text/json'})


async def connect_rabbitmq(loop, username, password, host):
    logger.debug(host)
    connection = await aio_pika.connect_robust(f"amqp://{username}:{password}@{host}/", loop=loop)
    channel = await connection.channel()
    await channel.declare_queue(config.rabbitmq_request_queue)
    return channel


async def close_rabbitmq_connection(app):
    await app['rabbit'].close()


def main(config):
    loop = asyncio.get_event_loop()
    app = web.Application()
    app['config'] = config
    app['rabbit'] = loop.run_until_complete(connect_rabbitmq(
        loop,
        config.rabbitmq_username,
        config.rabbitmq_password,
        config.rabbitmq_host
    ))

    app.add_routes([
        web.get('/{tail:.*}', handle),
        web.post('/{tail:.*}', handle),
    ])

    app.on_shutdown.extend([
        close_rabbitmq_connection
    ])

    web.run_app(app, host=config.app_host, port=config.app_port)


class Config:
    app_host = 'localhost'
    app_port = 8080
    rabbitmq_host = 'localhost'
    rabbitmq_port = 5672
    rabbitmq_username = 'guest'
    rabbitmq_password = 'guest'
    rabbitmq_request_queue = 'requests'


if __name__ == '__main__':
    import argparse
    import configparser

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('config')
    args = arg_parser.parse_args()

    if not os.path.exists(args.config):
        logger.critical(f"File {args.config} doesn't exist")
        sys.exit(1)
    parser = configparser.ConfigParser()
    parser.read(args.config)

    loglevel = parser.get('app', 'log', fallback='INFO')
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logging.basicConfig(format='%(levelname)s:%(message)s')
    logger.setLevel(numeric_level)
    logger.info('info starting...')

    config = Config()
    config.app_host = parser.get('app', 'host', fallback='localhost')
    config.app_port = parser.getint('app', 'port', fallback=8080)
    config.rabbitmq_host = parser.get('rabbitmq', 'host')
    config.rabbitmq_port = parser.getint('rabbitmq', 'port')
    config.rabbitmq_username = parser.get('rabbitmq', 'username')
    config.rabbitmq_password = parser.get('rabbitmq', 'password')

    main(config)
