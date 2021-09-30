import json
import logging
import os
import signal
import threading
import typing

import paho.mqtt.client as paho

import baseline_device.util.dict
from baseline_device import util
from baseline_device.util.config import config
from baseline_device.util.mqtt import MqttLoggingHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client_id = os.environ['BASELINE_CLIENT_ID']

shadow_name = 'sample'
shadow_timer: typing.Optional[threading.Timer] = None


def on_connect(client: paho.Client, userdata: dict, flags: dict, rc: int) -> None:
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/get/accepted', qos=2)
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/get/rejected', qos=2)
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/delta', qos=2)
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/documents', qos=2)
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/accepted', qos=2)
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/rejected', qos=2)
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/delete/accepted', qos=2)
    client.subscribe(f'$aws/things/{client_id}/shadow/name/{shadow_name}/delete/rejected', qos=2)

    client.publish(f'$aws/things/{client_id}/shadow/name/{shadow_name}/get', qos=2)

    global shadow_timer
    if shadow_timer: shadow_timer.cancel()
    shadow_timer = threading.Timer(600, client.publish, args=[f'$aws/things/{client_id}/shadow/name/{shadow_name}/get'], kwargs={'qos': 2})
    shadow_timer.start()


def shadow_get_accepted(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "state": {
    #         "desired": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         },
    #         "reported": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         },
    #         "delta": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         }
    #     },
    #     "metadata": {
    #         "desired": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         },
    #         "reported": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         }
    #     },
    #     "timestamp": timestamp,
    #     "clientToken": "token",
    #     "version": number
    # }
    payload = json.loads(message.payload.decode('utf-8'))
    state = payload['state']
    handle_shadow_state(state)


def shadow_get_rejected(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "code": "ErrorCode",
    #     "message": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    payload = json.loads(message.payload.decode('utf-8'))

    if payload['code'] == 404:  # the shadow is not set up for this device, or was deleted
        if os.path.isfile(f'/tmp/{config.app_name}/shadows/{shadow_name}'):
            os.remove(f'/tmp/{config.app_name}/shadows/{shadow_name}')
    else:
        logger.error(f'MQTT request rejected for topic {message.topic}:\n{message.payload}')


# AWS IoT publishes a response state document to this topic when it accepts a change for the device's shadow,
# and the request state document contains different values for desired and reported states:
# * A message published on update/delta includes only the desired attributes that differ between the desired and reported sections.
#   It contains all of these attributes, regardless of whether these attributes were contained in the current update message or were
#   already stored in AWS IoT. Attributes that do not differ between the desired and reported sections are not included.
# * If an attribute is in the reported section but has no equivalent in the desired section, it is not included.
# * If an attribute is in the desired section but has no equivalent in the reported section, it is included.
# * If an attribute is deleted from the reported section but still exists in the desired section, it is included.
def shadow_update_delta(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "state": {
    #         "attribute1": integer,
    #         "attributeN": boolean
    #     },
    #     "metadata": {
    #         "attribute1": {"timestamp": timestamp},
    #         "attributeN": {"timestamp": timestamp}
    #     },
    #     "timestamp": timestamp,
    #     "clientToken": "token",
    #     "version": number
    # }
    client.publish(f'$aws/things/{client_id}/shadow/name/{shadow_name}/get', qos=2)


def shadow_update_documents(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #   "previous" : {
    #     "state": {
    #         "desired": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         },
    #         "reported": {
    #             "attribute1": integer1,
    #             "attributeN": boolean1
    #         }
    #     },
    #     "metadata": {
    #         "desired": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         },
    #         "reported": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         }
    #     },
    #     "version": number
    #   },
    #   "current": {
    #     "state": {
    #         "desired": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         },
    #         "reported": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         }
    #     },
    #     "metadata": {
    #         "desired": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         },
    #         "reported": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         }
    #     },
    #     "version": number
    #   },
    #   "timestamp": timestamp,
    #   "clientToken": "token"
    # }
    payload = json.loads(message.payload.decode('utf-8'))
    state = payload['current']['state']
    handle_shadow_state(state)


def shadow_update_accepted(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "state": {
    #         "desired": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         },
    #         "reported": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         },
    #         "delta": {
    #             "attribute1": integer,
    #             "attributeN": boolean
    #         }
    #     },
    #     "metadata": {
    #         "desired": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         },
    #         "reported": {
    #             "attribute1": { "timestamp": timestamp },
    #             "attributeN": { "timestamp": timestamp }
    #         }
    #     },
    #     "timestamp": timestamp,
    #     "clientToken": "token",
    #     "version": number
    # }
    client.publish(f'$aws/things/{client_id}/shadow/name/{shadow_name}/get', qos=2)


def shadow_update_rejected(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "code": "ErrorCode",
    #     "message": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    logger.error(f'MQTT request rejected for topic {message.topic}:\n{message.payload}')


def shadow_delete_accepted(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    if os.path.isfile(f'/tmp/{config.app_name}/shadows/{shadow_name}'):
        os.remove(f'/tmp/{config.app_name}/shadows/{shadow_name}')


def shadow_delete_rejected(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "code": "ErrorCode",
    #     "message": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    logger.error(f'MQTT request rejected for topic {message.topic}:\n{message.payload}')


def handle_shadow_state(state: dict) -> None:
    # {
    #     "desired": {
    #         "attribute1": integer,
    #         "attributeN": boolean
    #     },
    #     "reported": {
    #         "attribute1": integer,
    #         "attributeN": boolean
    #     },
    #     "delta": {
    #         "attribute1": integer,
    #         "attributeN": boolean
    #     }
    # }

    desired = state.get('desired') or {}
    reported = state.get('reported') or {}
    added, removed, changed = util.dict.diff(reported, desired)

    os.makedirs(f'/tmp/{config.app_name}/shadows', exist_ok=True)

    with open(f'/tmp/{config.app_name}/shadows/{shadow_name}', 'w') as f:
        json.dump(desired, f)

    if len({**added, **removed, **changed}):  # something is out of sync, report the differences
        client.publish(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update', qos=2, payload=json.dumps({
            'state': {
                'reported': {
                    **desired,
                    **{k: None for k, v in removed.items()}  # must send NULL to remove an attribute
                }
            }
        }))


client = None

try:

    client = paho.Client(clean_session=True)
    client.on_connect = on_connect
    client.enable_logger(logger)
    logger.addHandler(MqttLoggingHandler(client, f'$aws/rules/{config.topic_prefix}/things/{client_id}/log'))
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/get/accepted', shadow_get_accepted)
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/get/rejected', shadow_get_rejected)
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/delta', shadow_update_delta)
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/documents', shadow_update_documents)
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/accepted', shadow_update_accepted)
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/update/rejected', shadow_update_rejected)
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/delete/accepted', shadow_delete_accepted)
    client.message_callback_add(f'$aws/things/{client_id}/shadow/name/{shadow_name}/delete/rejected', shadow_delete_rejected)
    client.connect_async('localhost')
    client.loop_start()

    signal.sigwait([signal.SIGINT])

except:

    logger.critical('Fatal shutdown...', exc_info=True)

finally:

    if shadow_timer:
        shadow_timer.cancel()

    if client:
        client.loop_stop()
        client.disconnect()
