import json
import logging
import os
import signal
import subprocess
import threading
import typing

import paho.mqtt.client as paho

from baseline_device.util.config import config
from baseline_device.util.mqtt import MqttLoggingHandler
from baseline_device.util.os import shell

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client_id = os.environ['BASELINE_CLIENT_ID']

check_pending_timer: typing.Optional[threading.Timer] = None

active_job_execution: typing.Optional[dict] = None
active_job_timer: typing.Optional[threading.Timer] = None


def on_connect(client: paho.Client, userdata: dict, flags: dict, rc: int) -> None:
    client.subscribe(f'$aws/things/{client_id}/jobs/get/accepted', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/get/rejected', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/start-next/accepted', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/start-next/rejected', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/+/get/accepted', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/+/get/rejected', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/+/update/accepted', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/+/update/rejected', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/notify', qos=2)
    client.subscribe(f'$aws/things/{client_id}/jobs/notify-next', qos=2)
    client.subscribe(f'supervisor/processes/+/events/PROCESS_STATE', qos=2)

    client.publish(f'$aws/things/{client_id}/jobs/get', qos=2)

    global check_pending_timer
    if check_pending_timer: check_pending_timer.cancel()
    check_pending_timer = threading.Timer(600, client.publish, args=[f'$aws/things/{client_id}/jobs/get'], kwargs={'qos': 2})
    check_pending_timer.start()


# GetPendingJobExecutions:
# Gets the list of all jobs for a thing that are not in a terminal state.
# https://docs.aws.amazon.com/iot/latest/developerguide/jobs-api.html
def jobs_get_accepted(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    active_execution = active_job_execution

    # {
    #     "inProgressJobs": [{
    #         "jobId": "string",
    #         "queuedAt": timestamp,
    #         "startedAt": timestamp,
    #         "lastUpdatedAt": timestamp,
    #         "versionNumber": number,
    #         "executionNumber": long
    #     }],
    #     "queuedJobs": [{
    #         "jobId": "string",
    #         "queuedAt": timestamp,
    #         "lastUpdatedAt": timestamp,
    #         "versionNumber": number,
    #         "executionNumber": long
    #     }],
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    payload = json.loads(message.payload.decode('utf-8'))

    in_progress_jobs = payload['inProgressJobs']
    queued_jobs = payload['queuedJobs']

    def start_next() -> None:
        client.publish(f'$aws/things/{client_id}/jobs/start-next', qos=2)

    if in_progress_jobs:
        next_execution = in_progress_jobs[0]
        if not active_execution:
            start_next()
        elif active_execution['jobId'] != next_execution['jobId']:
            stop_job_execution(active_execution)
            start_next()
        elif pidof_job_execution(active_execution) == 0:  # pid of 0 means not running
            restart_job_execution(active_execution)
    else:
        if active_execution:
            stop_job_execution(active_execution)
        if queued_jobs:
            start_next()


def jobs_get_rejected(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "code": "ErrorCode",
    #     "message": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    logger.error(f'MQTT request rejected for topic {message.topic}:\n{message.payload}')


# StartNextPendingJobExecution:
# Gets and starts the next pending job execution for a thing (status IN_PROGRESS or QUEUED).
# * Any job executions with status IN_PROGRESS are returned first.
# * Job executions are returned in the order in which they were created.
# * If the next pending job execution is QUEUED, its state is changed to IN_PROGRESS and the job execution's status details are set as specified.
# * If the next pending job execution is already IN_PROGRESS, its status details are not changed.
# * If no job executions are pending, the response does not include the execution field.
# * You can optionally create a step timer by setting a value for the stepTimeoutInMinutes property.
#   If you don't update the value of this property by running UpdateJobExecution, the job execution times out when the step timer expires.
# https://docs.aws.amazon.com/iot/latest/developerguide/jobs-api.html
def jobs_start_next_accepted(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    active_execution = active_job_execution

    # {
    #     "execution": {
    #         "jobId": "string",
    #         "jobDocument": "string",
    #         "status": "IN_PROGRESS",
    #         "queuedAt": timestamp,
    #         "startedAt": timestamp,
    #         "lastUpdatedAt": timestamp,
    #         "versionNumber": number,
    #         "executionNumber": long
    #     },
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    payload = json.loads(message.payload.decode('utf-8'))

    if 'execution' in payload:
        next_execution = payload['execution']
        if not active_execution:
            start_job_execution(next_execution)
        elif active_execution['jobId'] != next_execution['jobId']:
            stop_job_execution(active_execution)
            start_job_execution(next_execution)
        elif pidof_job_execution(active_execution) == 0:  # pid of 0 means not running
            restart_job_execution(active_execution)


def jobs_start_next_rejected(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "code": "ErrorCode",
    #     "message": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    logger.error(f'MQTT request rejected for topic {message.topic}:\n{message.payload}')


# DescribeJobExecution:
# Gets detailed information about a job execution.
# You can set the jobId to $next to return the next pending job execution for a thing (status IN_PROGRESS or QUEUED).
# https://docs.aws.amazon.com/iot/latest/developerguide/jobs-api.html
def jobs_jobid_get_accepted(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "execution": {
    #         "jobId": "string",
    #         "jobDocument": "string",
    #         "status": "QUEUED|IN_PROGRESS|FAILED|SUCCEEDED|CANCELED|TIMED_OUT|REJECTED|REMOVED",
    #         "queuedAt": timestamp,
    #         "startedAt": timestamp,
    #         "lastUpdatedAt": timestamp,
    #         "versionNumber": number,
    #         "executionNumber": long
    #     },
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    payload = json.loads(message.payload.decode('utf-8'))

    execution = payload['execution']

    global active_job_execution
    active_job_execution = execution

    if execution['status'] in ['FAILED', 'CANCELED', 'TIMED_OUT', 'REJECTED', 'REMOVED']:
        stop_job_execution(execution)


def jobs_jobid_get_rejected(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    execution = active_job_execution
    if not execution: return

    # {
    #     "code": "ErrorCode",
    #     "message": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    payload = json.loads(message.payload.decode('utf-8'))

    if payload.get('code') == 'TerminalStateReached':
        topic_job_id = message.topic.split('/')[4]
        if topic_job_id == execution['jobId']:
            stop_job_execution(execution)
            client.publish(f'$aws/things/{client_id}/jobs/get', qos=2)
    else:
        logger.error(f'MQTT request rejected for topic {message.topic}:\n{message.payload}')


# UpdateJobExecution:
# Updates the status of a job execution. You can optionally create a step timer by setting a value for the stepTimeoutInMinutes property.
# If you don't update the value of this property by running UpdateJobExecution again, the job execution times out when the step timer expires.
# https://docs.aws.amazon.com/iot/latest/developerguide/jobs-api.html
def jobs_jobid_update_accepted(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "executionState": {
    #         "status": "QUEUED|IN_PROGRESS|FAILED|SUCCEEDED|CANCELED|TIMED_OUT|REJECTED|REMOVED",
    #         "versionNumber": number
    #     },
    #     "jobDocument": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    pass


def jobs_jobid_update_rejected(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "code": "ErrorCode",
    #     "message": "string",
    #     "timestamp": timestamp,
    #     "clientToken": "string"
    # }
    logger.error(f'MQTT request rejected for topic {message.topic}:\n{message.payload}')


# JobExecutionsChanged:
# Sent whenever a job execution is added to or removed from the list of pending job executions for a thing.
# https://docs.aws.amazon.com/iot/latest/developerguide/jobs-api.html
def jobs_notify(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "jobs": {
    #         "JobExecutionState": [{
    #             "jobId": "string",
    #             "queuedAt": timestamp,
    #             "startedAt": timestamp,
    #             "lastUpdatedAt": timestamp,
    #             "versionNumber": number,
    #             "executionNumber": long
    #         }]
    #     },
    #     "timestamp": timestamp,
    # }
    client.publish(f'$aws/things/{client_id}/jobs/get', qos=2)


# NextJobExecutionChanged:
# Sent whenever there is a change to which job execution is next on the list of pending job executions for a thing,
# as defined for DescribeJobExecution with jobId $next. This message is not sent when the next job's execution details
# change, only when the next job that would be returned by DescribeJobExecution with jobId $next has changed.
# Consider job executions J1 and J2 with state QUEUED. J1 is next on the list of pending job executions.
# If the state of J2 is changed to IN_PROGRESS while the state of J1 remains unchanged, then this notification is
# sent and contains details of J2.
# https://docs.aws.amazon.com/iot/latest/developerguide/jobs-api.html
def jobs_notify_next(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    # {
    #     "execution": {
    #         "jobId": "string",
    #         "jobDocument": "string",
    #         "status": "QUEUED|IN_PROGRESS",
    #         "queuedAt": timestamp,
    #         "startedAt": timestamp,
    #         "lastUpdatedAt": timestamp,
    #         "versionNumber": number,
    #         "executionNumber": long
    #     },
    #     "timestamp": timestamp,
    # }
    client.publish(f'$aws/things/{client_id}/jobs/get', qos=2)


def start_job_execution(execution: dict) -> None:
    job_id = execution['jobId']

    job_document = execution['jobDocument']
    program = job_document['program']

    os.makedirs(f'/tmp/{config.app_name}/jobs', exist_ok=True)

    with open(f'/tmp/{config.app_name}/jobs/{program}', 'w') as f:
        json.dump(execution, f)

    shell(f'/usr/bin/supervisorctl'
          f' -c /etc/{config.app_name}/supervisord.conf'
          f' start jobs_{program}')

    global active_job_execution
    active_job_execution = execution

    global active_job_timer
    if active_job_timer: active_job_timer.cancel()
    active_job_timer = threading.Timer(60, client.publish, args=[f'$aws/things/{client_id}/jobs/{job_id}/get'], kwargs={'qos': 2})
    active_job_timer.start()


def restart_job_execution(execution: dict) -> None:
    job_document = execution['jobDocument']
    program = job_document['program']

    shell(f'/usr/bin/supervisorctl'
          f' -c /etc/{config.app_name}/supervisord.conf'
          f' restart jobs_{program}')


def stop_job_execution(execution: dict) -> None:
    job_document = execution['jobDocument']
    program = job_document['program']

    shell(f'/usr/bin/supervisorctl'
          f' -c /etc/{config.app_name}/supervisord.conf'
          f' stop jobs_{program}')

    reset_job_execution()


def reset_job_execution() -> None:
    global active_job_execution
    active_job_execution = None

    global active_job_timer
    if active_job_timer:
        active_job_timer.cancel()
        active_job_timer = None


def pidof_job_execution(execution: dict) -> int:
    job_document = execution['jobDocument']
    program = job_document['program']

    pid = shell(f'/usr/bin/supervisorctl'
                f' -c /etc/{config.app_name}/supervisord.conf'
                f' pid jobs_{program}', stdout=subprocess.STDOUT)

    return int(pid)


def supervisor_process_state(client: paho.Client, userdata: dict, message: paho.MQTTMessage) -> None:
    execution = active_job_execution
    if not execution: return

    payload = json.loads(message.payload.decode('utf-8'))

    job_document = execution['jobDocument']
    program = job_document['program']

    if payload['processname'] != program: return

    # http://supervisord.org/events.html#process-state-stopped-event-type
    # http://supervisord.org/events.html#process-state-exited-event-type
    if payload['eventname'] in ['PROCESS_STATE_STOPPED', 'PROCESS_STATE_EXITED']:
        reset_job_execution()

    # in the case where you might have your job process use supervisor's autorestart feature,
    # you may want the FAILED status to only send when supervisor gives up and goes into FATAL state.
    # http://supervisord.org/events.html#process-state-fatal-event-type
    elif payload['eventname'] == 'PROCESS_STATE_FATAL':
        reset_job_execution()

        job_id = execution['jobId']
        client.publish(f'$aws/things/{client_id}/jobs/{job_id}/update', qos=2, payload=json.dumps({
            'status': 'FAILED',
            'expectedVersion': execution['versionNumber'],
            'executionNumber': execution['executionNumber']
        }))


client = None

try:

    client = paho.Client(clean_session=True)
    client.on_connect = on_connect
    client.enable_logger(logger)
    logger.addHandler(MqttLoggingHandler(client, f'$aws/rules/{config.topic_prefix}/things/{client_id}/log'))
    client.message_callback_add(f'$aws/things/{client_id}/jobs/get/accepted', jobs_get_accepted)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/get/rejected', jobs_get_rejected)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/start-next/accepted', jobs_start_next_accepted)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/start-next/rejected', jobs_start_next_rejected)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/+/get/accepted', jobs_jobid_get_accepted)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/+/get/rejected', jobs_jobid_get_rejected)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/+/update/accepted', jobs_jobid_update_accepted)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/+/update/rejected', jobs_jobid_update_rejected)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/notify', jobs_notify)
    client.message_callback_add(f'$aws/things/{client_id}/jobs/notify-next', jobs_notify_next)
    client.message_callback_add(f'supervisor/processes/+/events/PROCESS_STATE', supervisor_process_state)
    client.connect_async('localhost')
    client.loop_start()

    signal.sigwait([signal.SIGINT])

except:

    logger.critical('Fatal shutdown...', exc_info=True)

finally:

    if active_job_timer:
        active_job_timer.cancel()

    if check_pending_timer:
        check_pending_timer.cancel()

    if client:
        client.loop_stop()
        client.disconnect()
