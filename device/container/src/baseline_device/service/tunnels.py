import json
import logging
import os
import signal

import paho.mqtt.client as paho

from baseline_device.util.config import config
from baseline_device.util.mqtt import MqttLoggingHandler
from baseline_device.util.os import shell

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client_id = os.environ['BASELINE_CLIENT_ID']


def on_connect(client: paho.Client, userdata: dict, flags: dict, rc: int) -> None:
    client.subscribe(f'$aws/things/{client_id}/tunnels/notify', qos=2)


def tunnels_notify(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "clientAccessToken": "<destination-client-access-token>",
    #     "clientMode": "destination",
    #     "region": "<aws-region",
    #     "services": ["destination-service"]
    # }
    payload = json.loads(message.payload.decode('utf-8'))

    if 'SSH' in payload['services']:
        os.makedirs(f'/tmp/{config.app_name}/localproxy', exist_ok=True)

        with open(f'/tmp/{config.app_name}/localproxy/ssh.ini', 'w') as f:
            f.write(f'region = {payload["region"]}')
            f.write(f'access-token = {payload["clientAccessToken"]}')
            f.write(f'destination-app = localhost:22')

        shell(f'/usr/bin/supervisorctl'
              f' -c /etc/{config.app_name}/supervisord.conf'
              f' start ssh')


client = None

try:

    client = paho.Client(clean_session=True)
    client.on_connect = on_connect
    client.enable_logger(logger)
    logger.addHandler(MqttLoggingHandler(client, f'$aws/rules/{config.topic_prefix}/things/{client_id}/log'))
    client.message_callback_add(f'$aws/things/{client_id}/tunnels/notify', tunnels_notify)
    client.connect_async('localhost')
    client.loop_start()

    signal.sigwait([signal.SIGINT])

except:

    logger.critical('Fatal shutdown...', exc_info=True)

finally:

    if client:
        client.loop_stop()
        client.disconnect()
