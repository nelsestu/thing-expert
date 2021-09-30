import json
import logging
import os
import shutil

import OpenSSL.crypto as openssl
import paho.mqtt.client as paho

from baseline_device.util import hex
from baseline_device.util.config import config
from baseline_device.util.file import mkdtemp
from baseline_device.util.mqtt import connect_and_wait
from baseline_device.util.mqtt import send_and_receive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

client = None

try:

    with open(f'/etc/{config.app_name}/aws/endpoint', 'r') as f:
        aws_endpoint = f.read()

    client_key = openssl.PKey()
    client_key.generate_key(openssl.TYPE_RSA, 2048)
    client_key_pem = openssl.dump_privatekey(openssl.FILETYPE_PEM, client_key)
    client_key_pem = client_key_pem.decode('utf-8')

    client_csr = openssl.X509Req()
    client_subject = client_csr.get_subject()
    client_subject.C = 'US'
    client_subject.CN = config.app_name
    client_csr.set_pubkey(client_key)
    client_csr.sign(client_key, 'sha256')
    client_csr.verify(client_key)
    client_csr_pem = openssl.dump_certificate_request(openssl.FILETYPE_PEM, client_csr)
    client_csr_pem = client_csr_pem.decode('utf-8')

    # force iot:ClientId to be 128 characters to avoid collisions when randomly selected by new clients.
    # https://docs.aws.amazon.com/general/latest/gr/iot-core.html#iot-protocol-limits
    client_id = hex.rand(128)

    client = paho.Client(client_id, clean_session=True)
    client.enable_logger(logger)
    client.tls_set(
        ca_certs=f'/etc/{config.app_name}/aws/root.crt',
        certfile=f'/etc/{config.app_name}/aws/client.crt',
        keyfile=f'/etc/{config.app_name}/aws/client.key',
        cert_reqs=paho.ssl.CERT_REQUIRED,
        tls_version=paho.ssl.PROTOCOL_SSLv23
    )

    client.loop_start()

    connect_and_wait(client, aws_endpoint, port=8883)

    response = send_and_receive(
        client=client,
        topic=f'$aws/rules/{config.topic_prefix}/clients/{client_id}/provision',
        payload=json.dumps({
            'csr': client_csr_pem
        }),
        qos=1
    )

    if not response:
        raise Exception('No response from provision(1) request.')

    if response.topic.endswith('/rejected'):
        raise Exception('Provision(1) request rejected.')

    response = response.payload.decode('utf-8')
    response = json.loads(response)

    certificate_arn = response['arn']
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    certificate_pem = response['pem']

    certificate = openssl.load_certificate(openssl.FILETYPE_PEM, certificate_pem)
    certificate_subject = certificate.get_subject()

    thing_name = certificate_subject.CN

    with mkdtemp() as tmp_dir:

        with open(f'{tmp_dir}/client.crt', 'w') as f:
            f.write(certificate_pem)

        with open(f'{tmp_dir}/client.key', 'w') as f:
            f.write(client_key_pem)

        # reconnect using the thing_name as the client_id to verify provisioning
        client.loop_stop()
        client.disconnect()

        client.reinitialise(thing_name, clean_session=True)
        client.enable_logger(logger)
        client.tls_set(
            ca_certs=f'/etc/{config.app_name}/aws/root.crt',
            certfile=f'{tmp_dir}/client.crt',
            keyfile=f'{tmp_dir}/client.key',
            cert_reqs=paho.ssl.CERT_REQUIRED,
            tls_version=paho.ssl.PROTOCOL_SSLv23
        )

        client.loop_start()

        connect_and_wait(client, aws_endpoint, port=8883)

        response = send_and_receive(
            client=client,
            topic=f'$aws/rules/{config.topic_prefix}/things/{thing_name}/provision',
            qos=1
        )

        client.loop_stop()
        client.disconnect()
        client = None

        if not response:
            raise Exception('No response from provision(2) request.')

        if response.topic.endswith('/rejected'):
            raise Exception('Provision(2) request rejected.')

        persistent_dir = f'/mnt/{config.app_name}/aws'

        try:

            os.makedirs(persistent_dir, exist_ok=True)

            with open(f'{persistent_dir}/thing.id', 'w') as f:
                f.write(thing_name)

            with open(f'{persistent_dir}/client.crt.id', 'w') as f:
                f.write(certificate_id)

            shutil.move(f'{tmp_dir}/client.crt', f'{persistent_dir}/client.crt')
            shutil.move(f'{tmp_dir}/client.key', f'{persistent_dir}/client.key')

        except:

            shutil.rmtree(persistent_dir)

            raise

except:

    logger.critical('Unable to complete provisioning.', exc_info=True)

    raise

finally:

    if client:
        client.loop_stop()
        client.disconnect()
