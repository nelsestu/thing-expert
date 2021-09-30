import traceback
import uuid

import OpenSSL.crypto as openssl
import boto3

import baseline_cloud.core.aws.secrets
import baseline_cloud.core.aws.ssm
import baseline_cloud.core.date
import baseline_cloud.core.mqtt
from baseline_cloud import core
from baseline_cloud.core import aws
from baseline_cloud.core.config import config
from . import RE_UUID

RULE_PROVISION = rf'^\$aws/rules/{config.topic_prefix}/clients/[0-9a-f]{{128}}/provision$'
RULE_VERIFY = rf'^\$aws/rules/{config.topic_prefix}/things/{RE_UUID}/provision$'

iot_client = boto3.client('iot')


def verify(event: dict, context) -> None:
    thing_name = event['clientId']

    try:

        add_thing_to_thing_group(thing_name, f'{config.app_name}-verified')
        remove_thing_from_thing_group(thing_name, f'{config.app_name}-unverified')

        core.mqtt.respond(event, 'accepted')

    except:

        try:
            add_thing_to_thing_group(thing_name, f'{config.app_name}-unverified')
        except:
            pass

        try:
            remove_thing_from_thing_group(thing_name, f'{config.app_name}-verified')
        except:
            pass

        core.mqtt.respond(event, 'rejected', error=traceback.format_exc())

        raise


def provision(event: dict, context) -> None:
    client_crt_arn = None

    thing_name = str(uuid.uuid4())

    try:

        csr_pem = event['csr']

        cacert_arn = aws.ssm.get_parameter(f'/{config.app_name}/cacert')
        cacert_id = cacert_arn.rsplit(maxsplit=1, sep='/')[1]

        cacert_key_pem = aws.secrets.get_secret_value(f'/{config.app_name}/key/{cacert_id}')
        cacert_key = openssl.load_privatekey(openssl.FILETYPE_PEM, cacert_key_pem)

        cacert_crt_pem = get_ca_certificate(cacert_arn)
        cacert_crt = openssl.load_certificate(openssl.FILETYPE_PEM, cacert_crt_pem)
        cacert_subject = cacert_crt.get_subject()

        client_csr = openssl.load_certificate_request(openssl.FILETYPE_PEM, csr_pem)
        client_subject = client_csr.get_subject()
        if cacert_subject.C: client_subject.C = cacert_subject.C
        if cacert_subject.ST: client_subject.ST = cacert_subject.ST
        if cacert_subject.L: client_subject.L = cacert_subject.L
        if cacert_subject.O: client_subject.O = cacert_subject.O
        client_subject.CN = thing_name

        client_crt = openssl.X509()
        client_crt.set_notBefore(cacert_crt.get_notBefore())
        client_crt.set_notAfter(cacert_crt.get_notAfter())
        client_crt.set_subject(client_subject)
        client_crt.set_pubkey(client_csr.get_pubkey())
        client_crt.set_issuer(cacert_subject)
        client_crt.sign(cacert_key, 'sha256')
        client_crt_pem = openssl.dump_certificate(openssl.FILETYPE_PEM, client_crt)
        client_crt_pem = client_crt_pem.decode('utf-8')

        client_crt_arn = register_certificate(cacert_crt_pem, client_crt_pem)

        create_thing(thing_name, config.app_name)
        attach_thing_principal(thing_name, client_crt_arn)

        add_thing_to_thing_group(thing_name, f'{config.app_name}-unverified')

        core.mqtt.respond(event, 'accepted', arn=client_crt_arn, pem=client_crt_pem)

    except:

        try:
            delete_thing(thing_name)
        except:
            pass

        try:
            delete_certificate(client_crt_arn)
        except:
            pass

        core.mqtt.respond(event, 'rejected', error=traceback.format_exc())

        raise


def create_thing(thing_name: str, thing_type: str) -> None:
    iot_client.create_thing(
        thingName=thing_name,
        thingTypeName=thing_type,
        attributePayload={
            'attributes': {
                'createdAt': core.date.format_utc()
            },
            'merge': True
        },
    )


def delete_thing(thing_name: str) -> None:
    iot_client.delete_thing(thingName=thing_name)


def add_thing_to_thing_group(thing_name: str, thing_group_name: str) -> None:
    iot_client.add_thing_to_thing_group(
        thingName=thing_name,
        thingGroupName=thing_group_name
    )


def remove_thing_from_thing_group(thing_name: str, thing_group_name: str) -> None:
    iot_client.remove_thing_from_thing_group(
        thingName=thing_name,
        thingGroupName=thing_group_name
    )


def attach_thing_principal(thing_name: str, certificate_arn: str) -> None:
    iot_client.attach_thing_principal(
        thingName=thing_name,
        principal=certificate_arn
    )


def register_certificate(ca_certificate: str, certificate: str) -> str:
    response = iot_client.register_certificate(
        caCertificatePem=ca_certificate,
        certificatePem=certificate,
        setAsActive=True
    )
    return response['certificateArn']


def delete_certificate(certificate_arn: str) -> None:
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    iot_client.delete_certificate(certificateId=certificate_id)


def get_ca_certificate(certificate_arn: str) -> str:
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    response = iot_client.describe_ca_certificate(certificateId=certificate_id)
    return response['certificateDescription']['certificatePem']
