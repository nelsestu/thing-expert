import json

from aws_cdk import aws_apigateway
from aws_cdk import aws_lambda
from aws_cdk import core

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> aws_apigateway.CfnResource:
    rest_api: aws_apigateway.CfnRestApi = cdk.find_resource(stack, 'ApiGateway/RestApi')

    v1 = create_root(rest_api, 'v1')

    v1_authenticate = create_resource(v1, 'authenticate')
    v1_authenticate_options = create_method_options(v1_authenticate)
    v1_authenticate_get = create_method(v1_authenticate, 'GET')
    v1_authenticate_get.authorization_type = 'NONE'
    v1_authenticate_get.authorizer_id = None

    v1_things = create_resource(v1, 'things')
    v1_things_options = create_method_options(v1_things)
    v1_things_get = create_method(v1_things, 'GET')

    return v1


def create_root(rest_api: aws_apigateway.CfnRestApi, path_part: str) -> aws_apigateway.CfnResource:
    logical_id = path_part.replace('_', ' ').title().replace(' ', '')  # example_of_path_part => ExampleOfPathPart
    return aws_apigateway.CfnResource(
        rest_api.node.scope, logical_id,
        rest_api_id=rest_api.ref,
        parent_id=rest_api.attr_root_resource_id,
        path_part=path_part
    )


def create_resource(parent: aws_apigateway.CfnResource, path_part: str) -> aws_apigateway.CfnResource:
    logical_id = path_part.replace('_', ' ').title().replace(' ', '')  # example_of_path_part => ExampleOfPathPart
    return aws_apigateway.CfnResource(
        parent, logical_id,
        rest_api_id=parent.rest_api_id,
        parent_id=parent.ref,
        path_part=path_part
    )


def create_method_options(resource: aws_apigateway.CfnResource) -> aws_apigateway.CfnMethod:
    return aws_apigateway.CfnMethod(
        resource, 'Options',
        rest_api_id=resource.rest_api_id,
        resource_id=resource.ref,
        authorization_type='NONE',
        http_method='OPTIONS',
        integration=aws_apigateway.CfnMethod.IntegrationProperty(
            type='MOCK',
            request_templates={
                'application/json': json.dumps({
                    'statusCode': 200
                })
            },
            integration_http_method='OPTIONS',
            integration_responses=[
                aws_apigateway.CfnMethod.IntegrationResponseProperty(
                    status_code='200',
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Headers': "'*'",
                        'method.response.header.Access-Control-Allow-Methods': "'GET,PUT,POST,PATCH,DELETE,HEAD,OPTIONS'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    },
                    response_templates={
                        'application/json': '$input.json("$")'
                    }
                )
            ]
        ),
        method_responses=[
            aws_apigateway.CfnMethod.MethodResponseProperty(
                status_code='200',
                response_parameters={
                    'method.response.header.Access-Control-Allow-Headers': False,
                    'method.response.header.Access-Control-Allow-Methods': False,
                    'method.response.header.Access-Control-Allow-Origin': False
                }
            )
        ]
    )


def create_method(resource: aws_apigateway.CfnResource, http_method: str) -> aws_apigateway.CfnMethod:
    stack: core.Stack = resource.stack
    lambda_function: aws_lambda.CfnFunction = cdk.find_resource(stack, 'ApisLambda/Function')
    authorizer: aws_apigateway.CfnAuthorizer = cdk.find_resource(stack, 'ApiGateway/Authorizer')

    method = aws_apigateway.CfnMethod(
        resource, http_method.capitalize(),
        rest_api_id=resource.rest_api_id,
        resource_id=resource.ref,
        authorization_type='CUSTOM',
        authorizer_id=authorizer.ref,
        http_method=http_method,
        integration=aws_apigateway.CfnMethod.IntegrationProperty(
            type='AWS_PROXY',
            integration_http_method='POST',
            uri=f'arn:aws:apigateway:{cdk.region}:lambda:path/2015-03-31/functions/{lambda_function.attr_arn}/invocations'
        ),
        method_responses=[
            aws_apigateway.CfnMethod.MethodResponseProperty(
                status_code='200',
                response_parameters={
                    'method.response.header.Access-Control-Allow-Origin': False
                }
            )
        ]
    )

    method.add_depends_on(lambda_function)

    return method
