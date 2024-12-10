from aws_cdk import (
    Stack,
    aws_apigateway,
    aws_cloudfront,
    aws_cloudfront_origins,
    aws_lambda,
)
from constructs import Construct


class CloudFunctionRouterStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        cluster_1_api = self._create_api_cluster("cluster_1")
        cluster_2_api = self._create_api_cluster("cluster_2")
        tenant_cluster_store = aws_cloudfront.KeyValueStore(
            self,
            "TenantClusterStore",
        )

        # CloudFront function to extract the tenant from the request path
        cff_tenant_router = aws_cloudfront.Function(
            self,
            "TenantRouter",
            code=aws_cloudfront.FunctionCode.from_inline(
                f"""
import cf from 'cloudfront';

const kvsId = "{tenant_cluster_store.key_value_store_id}";
const kvsHandle = cf.kvs(kvsId);

async function handler(event) {{
    var request = event.request;
    var uri = request.uri;
    var tenantId = uri.split('/')[1];

    try {{
        const clusterDomainName = await kvsHandle.get(tenantId);    
    }} catch (err) {{
        console.log(`Kvs key lookup failed for ${{tenantId}}: ${{err}}`);
        return request;
    }}
    
    console.log(`Routing ${{tenantId}} to ${{clusterDomainName}}`);
    cf.updateRequestOrigin({{'domainName': clusterDomainName}});
    return request;
}}
"""
            ),
            key_value_store=tenant_cluster_store,
        )
        function_association = aws_cloudfront.FunctionAssociation(
            event_type=aws_cloudfront.FunctionEventType.VIEWER_REQUEST,
            function=cff_tenant_router,
        )

        distribution = aws_cloudfront.Distribution(
            self,
            "cf_distribution",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=aws_cloudfront_origins.RestApiOrigin(cluster_1_api),
                function_associations=[function_association],
            ),
        )
        distribution.add_behavior(
            "/cluster_1/*",
            aws_cloudfront_origins.RestApiOrigin(cluster_1_api),
        )
        distribution.add_behavior(
            "/cluster_2/*",
            aws_cloudfront_origins.RestApiOrigin(cluster_2_api),
        )

    def _create_api_cluster(self, name):
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
