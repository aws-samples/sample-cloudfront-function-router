from urllib.parse import urlparse

from aws_cdk import (
    CfnOutput,
    Stack,
    aws_apigateway,
    aws_cloudfront,
    aws_cloudfront_origins,
    aws_iam,
    aws_lambda,
    aws_lambda_event_sources,
    aws_sqs,
)
from constructs import Construct

CFF_TENANT_ROUTER_CODE = """
import cf from 'cloudfront';

const kvsId = "{key_value_store_id}";
const kvsHandle = cf.kvs(kvsId);

async function handler(event) {{
    var request = event.request;
    var uri = request.uri;
    var tenantId = uri.split('/')[1];

    try {{
        var clusterDomainName = await kvsHandle.get(tenantId);
    }} catch (err) {{
        console.log(`Kvs key lookup failed for ${{tenantId}}: ${{err}}`);
        return request;
    }}
    
    console.log(`Routing ${{tenantId}} to ${{clusterDomainName}}`);
    cf.updateRequestOrigin({{'domainName': clusterDomainName}});
    return request;
}}
"""


class CloudFunctionRouterStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        cluster_1_api = self._create_api_cluster("cluster_1")
        cluster_2_api = self._create_api_cluster("cluster_2")
        tenant_cluster_store = aws_cloudfront.KeyValueStore(
            self,
            "tenant_cluster_store",
        )
        distribution = self._provision_distribution(tenant_cluster_store, cluster_1_api)
        distribution.add_behavior(
            "/cluster_1/*",
            aws_cloudfront_origins.RestApiOrigin(cluster_1_api),
        )
        distribution.add_behavior(
            "/cluster_2/*",
            aws_cloudfront_origins.RestApiOrigin(cluster_2_api),
        )
        self._provision_tenant_onboarding(
            tenant_cluster_store,
            {
                "CLUSTER_1": urlparse(cluster_1_api.url).netloc,
                "CLUSTER_2": urlparse(cluster_2_api.url).netloc,
            },
        )

    def _provision_tenant_onboarding(self, tenant_cluster_store, cluster_mappings):
        """Provision resources to onboard a new tenant to the system.
        Ingest onboarding requests via SQS queue which triggers a Lambda function to update KVS.
        """
        queue = aws_sqs.Queue(self, "tenant_onboarding_queue")
        env_vars = cluster_mappings | {
            "KVS_ARN": tenant_cluster_store.key_value_store_arn
        }
        function = aws_lambda.Function(
            self,
            "tenant_onboarding_function",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="tenant_onboarding.handler",
            code=aws_lambda.Code.from_asset("lambda"),
            environment=env_vars,
            events=[aws_lambda_event_sources.SqsEventSource(queue)],
        )
        # Add execution permissions to update CloudFront KVS and describe KVS
        function.add_to_role_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "cloudfront-keyvaluestore:PutKey",
                    "cloudfront-keyvaluestore:DescribeKeyValueStore",
                ],
                resources=[tenant_cluster_store.key_value_store_arn],
            )
        )

        CfnOutput(
            self,
            "tenant_onboarding_queue_url_export",
            value=queue.queue_url,
            export_name="TenantOnboardingQueueUrl",
            description="The URL of the tenant onboarding SQS queue",
        )

    def _provision_distribution(self, kvs_store, default_rest_origin):
        """Provision a CloudFront distribution with a tenant router CloudFront Function and KVS association."""
        cff_tenant_router = aws_cloudfront.Function(
            self,
            "tenant_router_function",
            code=aws_cloudfront.FunctionCode.from_inline(
                CFF_TENANT_ROUTER_CODE.format(
                    key_value_store_id=kvs_store.key_value_store_id
                )
            ),
            key_value_store=kvs_store,
        )
        function_association = aws_cloudfront.FunctionAssociation(
            event_type=aws_cloudfront.FunctionEventType.VIEWER_REQUEST,
            function=cff_tenant_router,
        )
        return aws_cloudfront.Distribution(
            self,
            "cf_distribution",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=aws_cloudfront_origins.RestApiOrigin(default_rest_origin),
                function_associations=[function_association],
            ),
        )

    def _create_api_cluster(self, name):
        """Provision an API Gateway + Lambda which represents a cluster API which hosts multiple tenants."""
        lambda_function = aws_lambda.Function(
            self,
            f"{name}_function",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="api.handler",
            code=aws_lambda.Code.from_asset("lambda"),
            environment={"CLUSTER": name},
        )

        return aws_apigateway.LambdaRestApi(
            self,
            f"{name}_api",
            handler=lambda_function,
        )
