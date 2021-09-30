from aws_cdk import aws_cloudfront
from aws_cdk import aws_s3
from aws_cdk import core

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    s3_bucket: aws_s3.CfnBucket = cdk.find_resource(stack, 'Bucket')

    origin_access_identity = aws_cloudfront.CfnCloudFrontOriginAccessIdentity(
        stack, 'WebOriginAccessIdentity',
        cloud_front_origin_access_identity_config=aws_cloudfront.CfnCloudFrontOriginAccessIdentity.CloudFrontOriginAccessIdentityConfigProperty(
            comment=f'Access Identity for {s3_bucket.ref}'
        )
    )

    # the s3 bucket policy lazy loads this reference since it gets called first
    cdk.lazy_values['WebOriginAccessIdentity'] = origin_access_identity.ref

    distribution = aws_cloudfront.CfnDistribution(
        stack, 'WebDistribution',
        distribution_config=aws_cloudfront.CfnDistribution.DistributionConfigProperty(
            enabled=True,
            origins=[
                aws_cloudfront.CfnDistribution.OriginProperty(
                    id=f'S3-{s3_bucket.ref}',
                    domain_name=s3_bucket.attr_domain_name,
                    s3_origin_config=aws_cloudfront.CfnDistribution.S3OriginConfigProperty(
                        origin_access_identity=f'origin-access-identity/cloudfront/{origin_access_identity.ref}'
                    ),
                    origin_path='/web'
                )
            ],
            default_root_object='index.html',
            custom_error_responses=[
                aws_cloudfront.CfnDistribution.CustomErrorResponseProperty(
                    error_code=403,
                    response_code=200,
                    response_page_path='/index.html'
                )
            ],
            default_cache_behavior=aws_cloudfront.CfnDistribution.DefaultCacheBehaviorProperty(
                target_origin_id=f'S3-{s3_bucket.ref}',
                viewer_protocol_policy='redirect-to-https',
                forwarded_values=aws_cloudfront.CfnDistribution.ForwardedValuesProperty(
                    query_string=False
                ),
                compress=True
            ),
            ipv6_enabled=True
        )
    )

    distribution.add_depends_on(s3_bucket)
