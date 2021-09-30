import json
import logging
import os
import signal
import uuid

import paho.mqtt.client as paho

import baseline_device.util.hex
from baseline_device import util
from baseline_device.util.config import config
from baseline_device.util.date import format_utc
from baseline_device.util.mqtt import MqttLoggingHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client_id = os.environ['BASELINE_CLIENT_ID']


def on_connect(client: paho.Client, userdata: dict, flags: dict, rc: int) -> None:
    logger.info(f'Local Client: CONNECTED')

    client.subscribe(f'$SYS/broker/connection/{client_id}/state', qos=2)

    # updating the shadow will create it if it does not exist
    client.publish(f'$aws/things/{client_id}/shadow/name/sample/update', qos=2, payload=json.dumps({
        'state': {
            'desired': {
                'connected': format_utc(),
                'random': util.hex.rand12()
            }
        },
        # AWS IoT Core uses this for tracking responses, just an example here
        'clientToken': str(uuid.uuid4())
    }))


def bridge_connection_status(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    status = 'ONLINE' if message.payload == b'1' else 'OFFLINE'
    logger.info(f'Remote Bridge Connection: {status}')


client = None

try:

    client = paho.Client(clean_session=True)
    client.on_connect = on_connect
    client.enable_logger(logger)
    logger.addHandler(MqttLoggingHandler(client, f'$aws/rules/{config.topic_prefix}/things/{client_id}/log'))
    client.message_callback_add(f'$SYS/broker/connection/{client_id}/state', bridge_connection_status)
    client.connect_async('localhost')
    client.loop_start()

    signal.sigwait([signal.SIGINT])

except:

    logger.critical('Fatal shutdown...', exc_info=True)

finally:

    if client:
        client.loop_stop()
        client.disconnect()
