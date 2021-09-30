from aws_cdk import aws_cognito
from aws_cdk import core

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    cognito_scope = core.Construct(stack, 'Cognito')

    user_pool = aws_cognito.CfnUserPool(
        cognito_scope, 'UserPool',
        user_pool_name=cdk.app_name
    )

    user_pool_client = aws_cognito.CfnUserPoolClient(
        user_pool, 'Client',
        client_name=cdk.app_name,
        user_pool_id=user_pool.ref,
        refresh_token_validity=3650,
        supported_identity_providers=['COGNITO']
    )

    aws_cognito.CfnIdentityPool(
        cognito_scope, 'IdentityPool',
        identity_pool_name=cdk.app_name,
        allow_unauthenticated_identities=False,
        cognito_identity_providers=[{
            'clientId': user_pool_client.ref,
            'providerName': user_pool.attr_provider_name
        }]
    )
