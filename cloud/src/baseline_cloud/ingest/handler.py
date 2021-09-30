import json
import re
import typing

import baseline_cloud.ingest.clients.log
import baseline_cloud.ingest.clients.provision
from baseline_cloud.ingest import clients

handlers: typing.Dict[str, typing.Callable[[dict, object], None]] = {
    clients.provision.RULE_PROVISION: clients.provision.provision,
    clients.provision.RULE_VERIFY: clients.provision.verify,
    clients.log.RULE: clients.log.handle
}


def handle(event: dict, context) -> None:
    print(json.dumps(event, indent=4))
    topic = event['topic']
    for rule, handler in handlers.items():
        if re.match(rule, topic):
            handler(event, context)
