import logging
import signal

import paho.mqtt.client as paho

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


def on_connect(client: paho.Client, userdata: dict, flags: dict, rc: int) -> None:
    logger.info(f'Connected: CLIENT({client}), USERDATA({userdata}), FLAGS({flags}), RC({rc})')
    client.subscribe(f'$SYS/broker/connection/#', qos=2)


def on_message(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    logger.info(f'Message: CLIENT({client}), USERDATA({userdata}), TOPIC({message.topic}, PAYLOAD({message.payload})')


client = None

try:

    client = paho.Client(clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.enable_logger(logger)
    client.connect_async('localhost')
    client.loop_start()

    signal.sigwait([signal.SIGINT])

except:

    logger.critical('Fatal shutdown...', exc_info=True)

finally:

    if client:
        client.loop_stop()
        client.disconnect()
