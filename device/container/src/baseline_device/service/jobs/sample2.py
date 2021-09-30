import json
import logging
import os
import sys
import threading
import time

import paho.mqtt.client as paho
import paho.mqtt.publish as paho_publish

from baseline_device.util.config import config
from baseline_device.util.mqtt import MqttLoggingHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client_id = os.environ['BASELINE_CLIENT_ID']

program = 'sample2'

connected = threading.Event()


def on_connect(client: paho.Client, userdata: dict, flags: dict, rc: int) -> None:
    # The value of rc determines success or not:
    #  0: Connection successful
    #  1: Connection refused - incorrect protocol version
    #  2: Connection refused - invalid client identifier
    #  3: Connection refused - server unavailable
    #  4: Connection refused - bad username or password
    #  5: Connection refused - not authorised
    #  6-255: Currently unused.
    if rc == 0: connected.set()


client = None
job_id = None

try:

    with open(f'/tmp/{config.app_name}/jobs/{program}', 'r') as f:
        execution = json.load(f)

    job_id = execution['jobId']

    client = paho.Client(clean_session=True)
    client.on_connect = on_connect
    client.enable_logger(logger)
    logger.addHandler(MqttLoggingHandler(client, f'$aws/rules/{config.topic_prefix}/things/{client_id}/log'))
    client.connect_async('localhost')
    client.loop_start()

    while not connected.is_set():
        time.sleep(1)

    logger.info('Job started!')

    time.sleep(30)

    logger.info('Job complete!')

    client.publish(f'$aws/things/{client_id}/jobs/{job_id}/update', qos=2, payload=json.dumps({
        'status': 'SUCCEEDED',
        'expectedVersion': execution['versionNumber'],
        'executionNumber': execution['executionNumber']
    }))

    sys.exit(0)

except SystemExit as e:
    raise e

except:

    logger.critical('Fatal shutdown...', exc_info=True)

    if job_id:
        try:
            client_publish = client.publish if client.is_connected() else paho_publish.single
            client_publish(f'$aws/things/{client_id}/jobs/{job_id}/update', qos=2, payload=json.dumps({
                'status': 'FAILED',
                'expectedVersion': execution['versionNumber'],
                'executionNumber': execution['executionNumber']
            }))
        except:
            logger.warning('Unable to send job status as FAILED', exc_info=True)

    sys.exit(1)

finally:

    if client:
        client.loop_stop()
        client.disconnect()
