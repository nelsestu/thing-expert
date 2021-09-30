import io
import json
import logging.handlers
import os
import threading
import time
import traceback
import typing
import uuid

import paho.mqtt.client as paho


def connect_and_wait(client: paho.Client, *connect_args, timeout=15, **connect_kwargs) -> typing.Optional[int]:
    complete = threading.Event()
    result = None

    _on_connect = client.on_connect

    def on_connect(client: paho.Client, userdata: dict, flags: dict, rc: int) -> None:
        nonlocal result
        result = (client, userdata, flags, rc)
        complete.set()

    client.on_connect = on_connect

    client.connect_async(*connect_args, **connect_kwargs)

    start = int(round(time.time()))
    while not complete.is_set():
        if int(round(time.time())) - start >= timeout:
            raise TimeoutError
        time.sleep(1)

    client.on_connect = _on_connect

    if result and isinstance(result, tuple):
        client, userdata, flags, rc = result
        if _on_connect: _on_connect(client, userdata, flags, rc)
        return rc

    return None


def subscribe_and_wait(client: paho.Client, *subscribe_args, timeout=15, **subscribe_kwargs) -> typing.Optional[bool]:
    complete = threading.Event()
    result = None
    mid = None

    _on_subscribe = client.on_subscribe

    def on_subscribe(client: paho.Client, userdata: dict, _mid: int, granted_qos: int, properties: dict = None) -> None:
        if _mid == mid:
            nonlocal result
            result = (client, userdata, _mid, granted_qos, properties)
            complete.set()

    client.on_subscribe = on_subscribe

    res, mid = client.subscribe(*subscribe_args, **subscribe_kwargs)

    if res != paho.MQTT_ERR_SUCCESS:
        raise ValueError(f'Subscribe received error result {res}')

    start = int(round(time.time()))
    while not complete.is_set():
        if int(round(time.time())) - start >= timeout:
            raise TimeoutError
        time.sleep(1)

    client.on_subscribe = _on_subscribe

    if result and isinstance(result, tuple):
        client, userdata, _mid, granted_qos, properties = result
        if _on_subscribe: _on_subscribe(client, userdata, _mid, granted_qos, properties)
        return True

    return None


def unsubscribe_and_wait(client: paho.Client, *unsubscribe_args, timeout=15, **unsubscribe_kwargs) -> typing.Optional[bool]:
    complete = threading.Event()
    result = None
    mid = None

    _on_unsubscribe = client.on_unsubscribe

    def on_unsubscribe(client: paho.Client, userdata: dict, _mid: int) -> None:
        if _mid == mid:
            nonlocal result
            result = (client, userdata, _mid)
            complete.set()

    client.on_unsubscribe = on_unsubscribe

    res, mid = client.unsubscribe(*unsubscribe_args, **unsubscribe_kwargs)

    if res != paho.MQTT_ERR_SUCCESS:
        raise ValueError(f'Unsubscribe received error result {res}')

    start = int(round(time.time()))
    while not complete.is_set():
        if int(round(time.time())) - start >= timeout:
            raise TimeoutError
        time.sleep(1)

    client.on_unsubscribe = _on_unsubscribe

    if result and isinstance(result, tuple):
        client, userdata, _mid = result
        if _on_unsubscribe: _on_unsubscribe(client, userdata, _mid)
        return True

    return None


def send_and_receive(client: paho.Client, topic: str, *publish_args, filter_by_client_token: bool = True, timeout: int = 15, **publish_kwargs) -> typing.Optional[paho.MQTTMessage]:
    complete = threading.Event()
    result = None

    if filter_by_client_token:
        payload = json.loads(publish_kwargs.get('payload') or '{}')
        client_token = payload.get('clientToken')
        if not client_token:  # inject the clientToken so we can filter responses
            payload['clientToken'] = client_token = str(uuid.uuid4())
            publish_kwargs['payload'] = json.dumps(payload)

    def callback(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:

        if filter_by_client_token:
            payload = json.loads(message.payload.decode('utf-8'))
            if client_token != payload.get('clientToken'): return

        nonlocal result
        result = message
        complete.set()

    if topic.startswith('$aws/rules/'):
        # we can't receive responses from the rules topic, so assume the prefix is chopped off
        resp_topic = topic[len('$aws/rules/'):]
    else:
        resp_topic = topic

    try:

        client.message_callback_add(f'{resp_topic}/accepted', callback)
        client.message_callback_add(f'{resp_topic}/rejected', callback)

        subscribe_kwargs = {}
        if 'qos' in publish_kwargs:
            subscribe_kwargs['qos'] = publish_kwargs['qos']

        subscribe_and_wait(client, f'{resp_topic}/accepted', **subscribe_kwargs)
        subscribe_and_wait(client, f'{resp_topic}/rejected', **subscribe_kwargs)

        message_info: paho.MQTTMessageInfo = client.publish(topic, *publish_args, **publish_kwargs)
        message_info.wait_for_publish()

        start = int(round(time.time()))
        while not complete.is_set():
            if int(round(time.time())) - start >= timeout:
                raise TimeoutError
            time.sleep(1)

        return result

    finally:

        client.message_callback_remove(f'{resp_topic}/accepted')
        client.message_callback_remove(f'{resp_topic}/rejected')

        try:
            unsubscribe_and_wait(client, f'{resp_topic}/accepted')
        except:
            pass

        try:
            unsubscribe_and_wait(client, f'{resp_topic}/rejected')
        except:
            pass


class MqttLoggingHandler(logging.Handler):

    def __init__(self, client: paho.Client, topic: str) -> None:
        super().__init__()
        self.client = client
        self.topic = topic

    def emit(self, record: logging.LogRecord) -> None:

        try:

            kwargs = {}

            if record.exc_info:
                kwargs['exception'] = self.format_exception(record.exc_info)

            self.client.publish(self.topic, qos=2, payload=json.dumps({
                'process': os.environ.get('SUPERVISOR_PROCESS_NAME'),
                'level': record.levelname,
                'message': record.getMessage(),
                'timestamp': round(record.created * 1000),
                **kwargs
            }))

        except:

            self.handleError(record)

    def format_exception(self, exc_info) -> str:
        sio = io.StringIO()
        traceback.print_exception(*exc_info, file=sio)
        value = sio.getvalue()
        sio.close()
        return value.strip()
