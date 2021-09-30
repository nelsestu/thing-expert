from aws_cdk import aws_secretsmanager
from aws_cdk import core

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    aws_secretsmanager.CfnSecret(
        stack, 'JwtSecretGenerator',
        name=f'/{cdk.app_name}/jwt-secret',
        generate_secret_string=aws_secretsmanager.CfnSecret.GenerateSecretStringProperty(
            password_length=256
        )
    )

    aws_secretsmanager.CfnSecret(
        stack, 'WebPasswordGenerator',
        name=f'/{cdk.app_name}/web-password',
        generate_secret_string=aws_secretsmanager.CfnSecret.GenerateSecretStringProperty(
            password_length=64
        )
    )
