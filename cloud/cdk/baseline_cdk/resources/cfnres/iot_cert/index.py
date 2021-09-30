import json
import logging
import typing

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
    certificate_arn = None

    try:

        properties = event['ResourceProperties']

        try:
            return get_parameter(properties['ArnStore'])
        except ssm_client.exceptions.ParameterNotFound:
            pass

        cacert_arn = properties['CaCertificateArn']
        cacert_id = cacert_arn.rsplit(maxsplit=1, sep='/')[1]

        cacert_key_pem = read_secret(properties['KeyStore'] + cacert_id)
        cacert_key = openssl.load_privatekey(openssl.FILETYPE_PEM, cacert_key_pem)

        cacert_crt_pem = get_ca_certificate(cacert_arn)
        cacert_crt = openssl.load_certificate(openssl.FILETYPE_PEM, cacert_crt_pem)
        cacert_subject = cacert_crt.get_subject()

        client_key = openssl.PKey()
        client_key.generate_key(openssl.TYPE_RSA, 2048)
        client_key_pem = openssl.dump_privatekey(openssl.FILETYPE_PEM, client_key)
        client_key_pem = client_key_pem.decode('utf-8')

        client_csr = openssl.X509Req()
        client_subject = client_csr.get_subject()
        if cacert_subject.C: client_subject.C = cacert_subject.C
        if cacert_subject.ST: client_subject.ST = cacert_subject.ST
        if cacert_subject.L: client_subject.L = cacert_subject.L
        if cacert_subject.O: client_subject.O = cacert_subject.O
        if cacert_subject.CN: client_subject.CN = cacert_subject.CN
        client_csr.set_pubkey(client_key)
        client_csr.sign(client_key, 'sha256')
        client_csr.verify(client_key)

        client_crt = openssl.X509()
        client_crt.set_notBefore(cacert_crt.get_notBefore())
        client_crt.set_notAfter(cacert_crt.get_notAfter())
        client_crt.set_subject(client_subject)
        client_crt.set_pubkey(client_csr.get_pubkey())
        client_crt.set_issuer(cacert_subject)
        client_crt.sign(cacert_key, 'sha256')
        client_crt_pem = openssl.dump_certificate(openssl.FILETYPE_PEM, client_crt)
        client_crt_pem = client_crt_pem.decode('utf-8')

        certificate_arn = register_certificate(cacert_crt_pem, client_crt_pem)
        certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]

        attach_policy(certificate_arn, properties['CertificatePolicy'])

        tags = resource_tags(event)

        create_secret(
            name=properties['KeyStore'] + certificate_id,
            value=client_key_pem,
            tags=tags
        )

        put_parameter(
            name=properties['ArnStore'],
            value=certificate_arn,
            tags=tags
        )

        return certificate_arn

    except:

        if certificate_arn:
            event['PhysicalResourceId'] = certificate_arn
            delete(event, context)

        raise


@helper.update
def update(event: dict, context) -> str:
    properties_old = event['OldResourceProperties']
    properties = event['ResourceProperties']

    certificate_arn = event['PhysicalResourceId']
    if certificate_arn.find('arn:aws:iot:') != 0 or ':cert/' not in certificate_arn:
        return certificate_arn  # not a valid cert arn

    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]

    if properties['CertificatePolicy'] != properties_old['CertificatePolicy']:
        attach_policy(certificate_arn, properties['CertificatePolicy'])
        detach_policy(certificate_arn, properties_old['CertificatePolicy'])

    tags = resource_tags(event)

    if properties['KeyStore'] != properties_old['KeyStore']:
        replace_secret(
            old=properties_old['KeyStore'] + certificate_id,
            new=properties['KeyStore'] + certificate_id,
            tags=tags
        )
    else:
        tag_secret(
            name=properties['KeyStore'] + certificate_id,
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

    return certificate_arn


@helper.delete
def delete(event: dict, context) -> str:
    properties = event['ResourceProperties']

    certificate_arn = event['PhysicalResourceId']
    if certificate_arn.find('arn:aws:iot:') != 0 or ':cert/' not in certificate_arn:
        return certificate_arn  # not a valid cert arn

    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]

    try:
        delete_secret(properties['KeyStore'] + certificate_id)
    except secrets_client.exceptions.ResourceNotFoundException:
        pass

    try:
        deactivate_certificate(certificate_arn)
        detach_policies(certificate_arn)
        delete_certificate(certificate_arn)
    except iot_client.exceptions.ResourceNotFoundException:
        pass

    try:
        delete_parameter(properties['ArnStore'])
    except ssm_client.exceptions.ParameterNotFound:
        pass

    return certificate_arn


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


def register_certificate(ca_certificate: str, certificate: str) -> str:
    response = iot_client.register_certificate(
        caCertificatePem=ca_certificate,
        certificatePem=certificate,
        setAsActive=True
    )
    return response['certificateArn']


def deactivate_certificate(certificate_arn: str) -> None:
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    iot_client.update_certificate(
        certificateId=certificate_id,
        newStatus='INACTIVE'
    )


def delete_certificate(certificate_arn: str) -> None:
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    iot_client.delete_certificate(certificateId=certificate_id)


def attach_policy(certificate_arn: str, policy: str) -> None:
    iot_client.attach_policy(
        policyName=policy,
        target=certificate_arn
    )


def detach_policy(certificate_arn: str, policy: str) -> None:
    iot_client.detach_policy(
        policyName=policy,
        target=certificate_arn
    )


def detach_policies(certificate_arn: str) -> None:
    response = iot_client.list_attached_policies(target=certificate_arn)
    for policy in response.get('policies', []):
        policy_name = policy['policyName']
        iot_client.detach_policy(
            target=certificate_arn,
            policyName=policy_name
        )


def get_ca_certificate(certificate_arn: str) -> str:
    certificate_id = certificate_arn.rsplit(maxsplit=1, sep='/')[1]
    response = iot_client.describe_ca_certificate(certificateId=certificate_id)
    return response['certificateDescription']['certificatePem']


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


def handle(event: dict, context) -> None:
    logger.info(json.dumps(event))
    helper(event, context)
