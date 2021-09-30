import json
import logging
import random

from crhelper import CfnResource

helper = CfnResource(log_level='DEBUG')
logger = logging.getLogger(__name__)


@helper.create
def create(event: dict, context) -> str:
    properties = event['ResourceProperties']
    length = properties['Length']
    return ''.join(random.choices('0123456789abcdef', k=int(length)))


def handle(event: dict, context) -> None:
    logger.info(json.dumps(event))
    helper(event, context)
