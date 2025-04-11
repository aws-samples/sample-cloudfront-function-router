#!/usr/bin/env python3
import os

import aws_cdk as cdk
from cloud_function_router.cloud_function_router_stack import CloudFunctionRouterStack

app = cdk.App()
CloudFunctionRouterStack(
    app,
    "CloudFunctionRouterStack",
)

app.synth()
