#!/bin/bash

# Export name
EXPORT_NAME="TenantOnboardingQueueUrl"

# Retrieve the SQS URL from CloudFormation export
SQS_URL=$(aws cloudformation list-exports --query "Exports[?Name=='${EXPORT_NAME}'].Value" --output text)

if [ -z "${SQS_URL}" ]; then
    echo "Could not retrieve SQS URL from exports."
    exit 1
fi

echo "Retrieved SQS URL: ${SQS_URL}"

# Send message to SQS
aws sqs send-message --queue-url ${SQS_URL} --message-body '{"tenant_id": "tenant_1", "cluster_id": "cluster_a"}' --no-cli-pager
aws sqs send-message --queue-url ${SQS_URL} --message-body '{"tenant_id": "tenant_2", "cluster_id": "cluster_b"}' --no-cli-pager

echo "Message sent to SQS queue."
