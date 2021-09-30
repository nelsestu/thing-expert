import json
import logging
import os
import sys
import time

import paho.mqtt.publish as paho

from baseline_device.util.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client_id = os.environ['BASELINE_CLIENT_ID']

program = 'sample1'

job_id = None

try:

    with open(f'/tmp/{config.app_name}/jobs/{program}', 'r') as f:
        execution = json.load(f)

    job_id = execution['jobId']

    logger.info('Job started!')

    time.sleep(30)

    logger.info('Job complete!')

    paho.single(f'$aws/things/{client_id}/jobs/{job_id}/update', qos=2, payload=json.dumps({
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
            paho.single(f'$aws/things/{client_id}/jobs/{job_id}/update', qos=2, payload=json.dumps({
                'status': 'FAILED',
                'expectedVersion': execution['versionNumber'],
                'executionNumber': execution['executionNumber']
            }))
        except:
            logger.warning('Unable to send job status as FAILED', exc_info=True)

    sys.exit(1)
