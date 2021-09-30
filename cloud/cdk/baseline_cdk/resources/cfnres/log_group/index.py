import json
import logging

import boto3
from crhelper import CfnResource

helper = CfnResource(log_level='DEBUG')
logger = logging.getLogger(__name__)

cloudwatch_client = boto3.client('logs')


@helper.create
def create(event: dict, context) -> str:
    properties = event['ResourceProperties']

    log_group_name = properties['LogGroupName']

    try:
        cloudwatch_client.create_log_group(logGroupName=log_group_name)
    except cloudwatch_client.exceptions.ResourceAlreadyExistsException:
        pass

    retention_in_days = int(properties['RetentionInDays'])
    cloudwatch_client.put_retention_policy(logGroupName=log_group_name, retentionInDays=retention_in_days)

    return log_group_arn(log_group_name)


@helper.update
def update(event: dict, context) -> str:
    properties_old = event['OldResourceProperties']
    properties = event['ResourceProperties']

    log_group_arn = event['PhysicalResourceId']
    if log_group_arn.find('arn:aws:logs:') != 0 or ':log-group:' not in log_group_arn:
        return log_group_arn  # not a valid log-group arn

    log_group_name = log_group_arn.rsplit(maxsplit=2, sep=':')[1]

    if properties['LogGroupName'] != properties_old['LogGroupName']:
        raise Exception(f'Renaming a LogGroup is not supported.')

    if properties['RetentionInDays'] != properties_old['RetentionInDays']:
        retention_in_days = int(properties['RetentionInDays'])
        cloudwatch_client.put_retention_policy(logGroupName=log_group_name, retentionInDays=retention_in_days)

    return log_group_arn


@helper.delete
def delete(event: dict, context) -> str:
    log_group_arn = event['PhysicalResourceId']
    if log_group_arn.find('arn:aws:logs:') != 0 or ':log-group:' not in log_group_arn:
        return log_group_arn  # not a valid log-group arn

    log_group_name = log_group_arn.rsplit(maxsplit=2, sep=':')[1]

    try:
        cloudwatch_client.delete_log_group(logGroupName=log_group_name)
    except cloudwatch_client.exceptions.ResourceNotFoundException:
        pass

    return log_group_arn


def log_group_arn(log_group_name: str) -> str:
    response = cloudwatch_client.describe_log_groups(logGroupNamePrefix=log_group_name, limit=1)
    return response['logGroups'][0]['arn']


def handle(event: dict, context) -> None:
    logger.info(json.dumps(event))
    helper(event, context)
