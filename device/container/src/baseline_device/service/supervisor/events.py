import json
import logging
import os
import select
import signal
import sys
import threading

import paho.mqtt.client as paho

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client_id = os.environ['BASELINE_CLIENT_ID']

client = None

try:

    client = paho.Client(clean_session=True)
    client.enable_logger(logger)
    client.connect_async('localhost')
    client.loop_start()

    terminate = threading.Event()


    def shutting_down() -> bool:
        return terminate.is_set() or \
               client._state == paho.mqtt_cs_disconnecting or \
               client._thread_terminate


    def shutdown(signum, frame) -> None:
        terminate.set()
        client.loop_stop()
        client.disconnect()


    signal.signal(signal.SIGINT, shutdown)

    sys.stdout.write('READY\n')
    sys.stdout.flush()

    while not shutting_down():

        available, _, _ = select.select([sys.stdin], [], [], 0.100)
        if not available: continue

        if shutting_down(): break

        try:

            data = sys.stdin.readline()
            headers = dict([x.split(':') for x in data.split()])
            body = sys.stdin.read(int(headers['len']))

            sys.stdout.write('RESULT 2\nOK')
            sys.stdout.write('READY\n')
            sys.stdout.flush()

        except:

            sys.stdout.write('RESULT 4\nFAIL')
            sys.stdout.write('READY\n')
            sys.stdout.flush()
            continue

        event_name = headers['eventname']

        # http://supervisord.org/events.html#supervisor-state-change-event-type
        if event_name.startswith('SUPERVISOR_STATE_CHANGE_'):
            client.publish(f'supervisor/events/SUPERVISOR_STATE_CHANGE', qos=2, payload=json.dumps({
                'eventname': event_name
            }))
            client.publish(f'supervisor/events/{event_name}', qos=2, payload=json.dumps({
                'eventname': event_name
            }))

        # http://supervisord.org/events.html#process-state-event-type
        elif event_name.startswith('PROCESS_STATE_'):
            body = dict([x.split(':') for x in body.split()])
            process_name = body['processname']
            client.publish(f'supervisor/processes/{process_name}/events/PROCESS_STATE', qos=2, payload=json.dumps({
                'eventname': event_name,
                **body
            }))
            client.publish(f'supervisor/processes/{process_name}/events/{event_name}', qos=2, payload=json.dumps({
                'eventname': event_name,
                **body
            }))

        else:

            body = dict([x.split(':') for x in body.split()]) if '\n' not in body else {'body': body}
            client.publish(f'supervisor/events/{event_name}', qos=2, payload=json.dumps({
                'eventname': event_name,
                **body
            }))

except:

    logger.critical('Fatal shutdown...', exc_info=True)

finally:

    if client:
        client.loop_stop()
        client.disconnect()
