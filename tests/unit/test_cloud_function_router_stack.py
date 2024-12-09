import aws_cdk as core
import aws_cdk.assertions as assertions

from cloud_function_router.cloud_function_router_stack import CloudFunctionRouterStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cloud_function_router/cloud_function_router_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CloudFunctionRouterStack(app, "cloud-function-router")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
