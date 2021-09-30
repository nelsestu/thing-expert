import os

from aws_cdk import aws_apigateway
from aws_cdk import aws_lambda
from aws_cdk import core

import baseline_cdk.resources.api_gateway_v1
import baseline_cdk.util.date
import baseline_cdk.util.hash
from baseline_cdk import resources
from baseline_cdk import util
from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    api_scope = core.Construct(stack, 'ApiGateway')

    authorizer_lambda: aws_lambda.CfnFunction = cdk.find_resource(stack, 'AuthorizerLambda/Function')
    apis_lambda: aws_lambda.CfnFunction = cdk.find_resource(stack, 'ApisLambda/Function')

    rest_api = aws_apigateway.CfnRestApi(
        api_scope, 'RestApi',
        name=cdk.app_name,
        description=f'Modified by {os.getlogin()} at {util.date.utcnow()}',
        endpoint_configuration=aws_apigateway.CfnRestApi.EndpointConfigurationProperty(
            types=['REGIONAL']
        )
    )

    authorizer = aws_apigateway.CfnAuthorizer(
        api_scope, 'Authorizer',
        rest_api_id=rest_api.ref,
        name=cdk.app_name,
        type='REQUEST',
        authorizer_uri=f'arn:aws:apigateway:{cdk.region}:lambda:path/2015-03-31/functions/{authorizer_lambda.attr_arn}/invocations',
        identity_source='method.request.header.Authorization'
    )

    authorizer.add_depends_on(authorizer_lambda)

    authorizer_lambda_permission = aws_lambda.CfnPermission(
        api_scope, 'AuthorizerLambdaPermission',
        action='lambda:InvokeFunction',
        function_name=authorizer_lambda.function_name,
        principal='apigateway.amazonaws.com',
        source_arn=f'arn:aws:execute-api:{cdk.region}:{cdk.account}:{rest_api.ref}/*'
    )

    authorizer_lambda_permission.add_depends_on(authorizer_lambda)

    apis_lambda_permission = aws_lambda.CfnPermission(
        api_scope, 'ApisLambdaPermission',
        action='lambda:InvokeFunction',
        function_name=apis_lambda.function_name,
        principal='apigateway.amazonaws.com',
        source_arn=f'arn:aws:execute-api:{cdk.region}:{cdk.account}:{rest_api.ref}/*'
    )

    apis_lambda_permission.add_depends_on(apis_lambda)

    aws_apigateway.CfnGatewayResponse(
        api_scope, 'Default4xxResponse',
        rest_api_id=rest_api.ref,
        response_type='DEFAULT_4XX',
        response_parameters={
            'gatewayresponse.header.Access-Control-Allow-Origin': "'*'"
        },
        response_templates={
            'application/json': '{"error":$context.error.messageString}'
        }
    )

    aws_apigateway.CfnGatewayResponse(
        api_scope, 'Default5xxResponse',
        rest_api_id=rest_api.ref,
        response_type='DEFAULT_5XX',
        response_parameters={
            'gatewayresponse.header.Access-Control-Allow-Origin': "'*'"
        },
        response_templates={
            'application/json': '{"error":$context.error.messageString}'
        }
    )

    v1 = resources.api_gateway_v1.create(stack)

    # use a hash of related resources to trigger re-deployments on updates
    deployment_hash = util.hash.str_sha1('\n'.join([
        util.hash.file_sha1(__file__),
        util.hash.file_sha1(resources.api_gateway_v1.__file__)
    ]))[:12].upper()

    deployment = aws_apigateway.CfnDeployment(
        api_scope, f'Deployment{deployment_hash}',
        rest_api_id=rest_api.ref
    )

    deployment.add_depends_on(v1)
    for method in cdk.find_resources(v1, aws_apigateway.CfnMethod):
        deployment.add_depends_on(method)

    aws_apigateway.CfnStage(
        api_scope, 'Stage',
        rest_api_id=rest_api.ref,
        deployment_id=deployment.ref,
        stage_name='live'
    )
