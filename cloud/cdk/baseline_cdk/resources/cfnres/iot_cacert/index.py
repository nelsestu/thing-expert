import json
import logging
import typing
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import OpenSSL.crypto as openssl
import boto3
from crhelper import CfnResource

helper = CfnResource(log_level='DEBUG')
logger = logging.getLogger(__name__)

iot_client = boto3.client('iot')
lambda_client = boto3.client('lambda')
secrets_client = boto3.client('secretsmanager')
ssm_client = boto3.client('ssm')


@helper.create
def create(event: dict, context) -> str:
    cacert_arn = None

    try:

        properties = event['ResourceProperties']

        try:
            return get_parameter(properties['ArnStore'])
        except ssm_client.exceptions.ParameterNotFound:
            pass

        cacert_info = properties['CertificateProperties']
        cacert_info_C = cacert_info.get('country')
        cacert_info_ST = cacert_info.get('state')
        cacert_info_L = cacert_info.get('locality')
        cacert_info_O = cacert_info.get('organization')
        cacert_info_OU = cacert_info.get('organizational_unit')

        now = datetime.utcnow()
        now = now.replace(tzinfo=timezone.utc)
        expires = now + timedelta(days=int(cacert_info.get('days', 365)))

        cacert_key = openssl.PKey()
        cacert_key.generate_key(openssl.TYPE_RSA, 2048)
        cacert_key_pem = openssl.dump_privatekey(openssl.FILETYPE_PEM, cacert_key)
        cacert_key_pem = cacert_key_pem.decode('utf-8')

        cacert_csr = openssl.X509Req()
        cacert_subject = cacert_csr.get_subject()
        if cacert_info_C: cacert_subject.C = cacert_info_C
        if cacert_info_ST: cacert_subject.ST = cacert_info_ST
        if cacert_info_L: cacert_subject.L = cacert_info_L
        if cacert_info_O: cacert_subject.O = cacert_info_O
        if cacert_info_OU: cacert_subject.OU = cacert_info_OU
        cacert_subject.CN = event['StackId'].rsplit(sep='/', maxsplit=2)[1]
        cacert_csr.set_pubkey(cacert_key)
        cacert_csr.sign(cacert_key, 'sha256')
        cacert_csr.verify(cacert_key)

        cacert_crt = openssl.X509()
        cacert_crt.set_notBefore(openssl_datetime(now))
        cacert_crt.set_notAfter(openssl_datetime(expires))
        cacert_crt.set_issuer(cacert_subject)
        cacert_crt.set_subject(cacert_subject)
        cacert_crt.set_pubkey(cacert_csr.get_pubkey())
        cacert_crt.add_extensions([openssl.X509Extension(b'basicConstraints', True, b'CA:TRUE,pathlen:0')])
        cacert_crt.sign(cacert_key, 'sha256')
        cacert_crt_pem = openssl.dump_certificate(openssl.FILETYPE_PEM, cacert_crt)
        cacert_crt_pem = cacert_crt_pem.decode('utf-8')

        client_key = openssl.PKey()
        client_key.generate_key(openssl.TYPE_RSA, 2048)

        client_csr = openssl.X509Req()
        client_subject = client_csr.get_subject()
        if cacert_info_C: client_subject.C = cacert_info_C
        if cacert_info_ST: client_subject.ST = cacert_info_ST
        if cacert_info_L: client_subject.L = cacert_info_L
        if cacert_info_O: client_subject.O = cacert_info_O
        if cacert_info_OU: client_subject.OU = cacert_info_OU
        client_subject.CN = get_registration_code()
        client_csr.set_pubkey(client_key)
        client_csr.sign(client_key, 'sha256')
        client_csr.verify(client_key)

        client_crt = openssl.X509()
        client_crt.set_notBefore(openssl_datetime(now))
        client_crt.set_notAfter(openssl_datetime(expires))
        client_crt.set_issuer(cacert_subject)
        client_crt.set_subject(client_subject)
        client_crt.set_pubkey(client_csr.get_pubkey())
        client_crt.sign(cacert_key, 'sha256')
        client_crt_pem = openssl.dump_certificate(openssl.FILETYPE_PEM, client_crt)
        client_crt_pem = client_crt_pem.decode('utf-8')

        cacert_arn = register_ca_certificate(cacert_crt_pem, client_crt_pem)
        cacert_id = cacert_arn.rsplit(maxsplit=1, sep='/')[1]

        tags = resource_tags(event)

        tag_ca_certificate(cacert_arn, tags)

        create_secret(
            name=properties['KeyStore'] + cacert_id,
            value=cacert_key_pem,
            tags=tags
        )

        put_parameter(
            name=properties['ArnStore'],
            value=cacert_arn,
            tags=tags
        )

        return cacert_arn

    except:

        if cacert_arn:
            event['PhysicalResourceId'] = cacert_arn
            delete(event, context)

        raise


@helper.update
def update(event: dict, context) -> str:
    properties_old = event['OldResourceProperties']
    properties = event['ResourceProperties']

    cacert_arn = event['PhysicalResourceId']
    if cacert_arn.find('arn:aws:iot:') != 0 or ':cacert/' not in cacert_arn:
        return cacert_arn  # not a valid cacert arn

    cacert_id = cacert_arn.rsplit(maxsplit=1, sep='/')[1]

    if properties['CertificateProperties'] != properties_old['CertificateProperties']:
        raise Exception('Changing CA Certificate properties is not supported.')

    tags = resource_tags(event)

    tag_ca_certificate(cacert_arn, tags)

    if properties['KeyStore'] != properties_old['KeyStore']:
        replace_secret(
            old=properties_old['KeyStore'] + cacert_id,
            new=properties['KeyStore'] + cacert_id,
            tags=tags
        )
    else:
        tag_secret(
            name=properties['KeyStore'] + cacert_id,
            tags=tags
        )

    if properties['ArnStore'] != properties_old['ArnStore']:
        replace_parameter(
            old=properties_old['ArnStore'],
            new=properties['ArnStore'],
            tags=tags
        )
    else:
        tag_parameter(
            name=properties['ArnStore'],
            tags=tags
        )

    return cacert_arn


@helper.delete
def delete(event: dict, context) -> str:
    properties = event['ResourceProperties']

    cacert_arn = event['PhysicalResourceId']
    if cacert_arn.find('arn:aws:iot:') != 0 or ':cacert/' not in cacert_arn:
        return cacert_arn  # not a valid cacert arn

    cacert_id = cacert_arn.rsplit(maxsplit=1, sep='/')[1]

    try:
        delete_secret(properties['KeyStore'] + cacert_id)
    except secrets_client.exceptions.ResourceNotFoundException:
        pass

    try:
        deactivate_ca_certificate(cacert_arn)
        delete_ca_certificate(cacert_arn)
    except iot_client.exceptions.ResourceNotFoundException:
        pass

    try:
        delete_parameter(properties['ArnStore'])
    except ssm_client.exceptions.ParameterNotFound:
        pass

    return cacert_arn


def resource_tags(event: dict) -> dict:
    lambda_tags = list_lambda_tags(event['ServiceToken'])
    return {
        **{f'x-{k}' if k.startswith('aws:') else k: v for k, v in lambda_tags.items()},
        'x-aws:cloudformation:stack-name': event['StackId'].rsplit(sep='/', maxsplit=2)[1],
        'x-aws:cloudformation:stack-id': event['StackId'],
        'x-aws:cloudformation:logical-id': event['LogicalResourceId']
    }


def list_lambda_tags(arn: str) -> dict:
    response = lambda_client.list_tags(Resource=arn)
    return response['Tags']


def get_registration_code() -> str:
    response = iot_client.get_registration_code()
    return response['registrationCode']


def register_ca_certificate(ca_certificate: str, verification_certificate: str) -> str:
    response = iot_client.register_ca_certificate(
        caCertificate=ca_certificate,
        verificationCertificate=verification_certificate,
        setAsActive=True,
        allowAutoRegistration=False
    )
    return response['certificateArn']


def deactivate_ca_certificate(certificate_arn: str) -> None:
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    iot_client.update_ca_certificate(
        certificateId=certificate_id,
        newStatus='INACTIVE'
    )


def delete_ca_certificate(certificate_arn: str) -> None:
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    iot_client.delete_ca_certificate(certificateId=certificate_id)


def tag_ca_certificate(arn: str, tags: dict) -> None:
    iot_client.tag_resource(
        resourceArn=arn,
        tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )


def create_secret(name: str, value: str, tags: dict) -> None:
    secrets_client.create_secret(
        Name=name,
        SecretString=value,
        Tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )


def replace_secret(old: str, new: str, tags: dict) -> None:
    create_secret(
        name=new,
        value=read_secret(old),
        tags=tags
    )
    delete_secret(old)


def read_secret(name: str) -> typing.Union[str, bytes]:
    response = secrets_client.get_secret_value(SecretId=name)
    if 'SecretBinary' in response: return response['SecretBinary']
    return response['SecretString']


def delete_secret(name: str) -> None:
    secrets_client.delete_secret(
        SecretId=name,
        ForceDeleteWithoutRecovery=True
    )


def tag_secret(name: str, tags: dict) -> None:
    secrets_client.tag_resource(
        SecretId=name,
        Tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )


def put_parameter(name: str, value: str, tags: dict) -> None:
    ssm_client.put_parameter(
        Name=name,
        Value=value,
        Type='String',
        Tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )


def replace_parameter(old: str, new: str, tags: dict) -> None:
    put_parameter(
        name=new,
        value=get_parameter(old),
        tags=tags
    )
    delete_parameter(old)


def get_parameter(name: str) -> str:
    response = ssm_client.get_parameter(Name=name)
    return response['Parameter']['Value']


def delete_parameter(name: str) -> None:
    ssm_client.delete_parameter(Name=name)


def tag_parameter(name: str, tags: dict) -> None:
    ssm_client.add_tags_to_resource(
        ResourceType='Parameter',
        ResourceId=name,
        Tags=[{
            'Key': k,
            'Value': v
        } for k, v in tags.items()]
    )


def openssl_datetime(d: datetime) -> bytes:
    return d.strftime('%Y%m%d%H%M%SZ').encode('utf-8')


def handle(event: dict, context) -> None:
    logger.info(json.dumps(event))
    helper(event, context)
