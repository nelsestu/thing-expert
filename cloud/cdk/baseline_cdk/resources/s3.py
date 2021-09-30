from aws_cdk import aws_s3
from aws_cdk import core

from baseline_cdk.resources import cfnres_str_random
from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    unique_id = cfnres_str_random.CfnStrRandom(
        stack, stack, 'BucketUniqueId',
        length=12
    )

    bucket = aws_s3.CfnBucket(
        stack, 'Bucket',
        bucket_name=f'{cdk.app_name}-{unique_id.ref}'
    )

    cloudfront_web_ref = cdk.lazy_string_value('WebOriginAccessIdentity')

    aws_s3.CfnBucketPolicy(
        stack, 'BucketPolicy',
        bucket=bucket.ref,
        policy_document={
            'Version': '2008-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Action': 's3:GetObject',
                'Principal': {
                    'AWS': f'arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity {cloudfront_web_ref}'
                },
                'Resource': f'arn:aws:s3:::{bucket.ref}/*'
            }]
        }
    )
