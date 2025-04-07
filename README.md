# Example project to implement a multi-cluster routing solution at edge, using Amazon CloudFront Functions and CloudFront KeyValueStore

This project demonstrates a dynamic request routing solution for multi-tenant, multi-cluster, and multi-region applications using Amazon CloudFront's edge capabilities. By combining CloudFront Functions with CloudFront KeyValueStore, the solution enables custom request routing at the edge based on predefined rules stored in KeyValueStore. This allows organizations to serve different users or tenants from specific clusters or regions while maintaining a single domain name. The routing logic is configurable through KeyValueStore entries, making it easy to update routing rules without code changes, and executes at CloudFront edge locations for optimal performance.

## Overview

This solution utilizes CloudFront Functions to intercept incoming HTTP requests at the edge and modify their behavior based on routing rules stored in CloudFront KeyValueStore. When a request arrives, the CloudFront Function extracts relevant information (such as headers, cookies, or query parameters) to identify the user or tenant. It then queries KeyValueStore to retrieve the corresponding routing configuration, which maps the user/tenant identifier to a specific origin or cluster. Based on this mapping, the Function modifies the request's target origin to route the traffic to the appropriate destination. All routing logic executes at CloudFront edge locations, ensuring minimal latency impact while maintaining the flexibility to route requests across multiple clusters or regions under a unified domain name.

## Architecture

The following resources are included in the Cloud Development Kit (CDK) app:

- **Amazon CloudFront Distribution**
  - Handles incoming requests
  - Contains configuration for CloudFront Function and origin groups
- **Amazon CloudFront Function**
  - Edge function that implements the routing logic
  - Executes on viewer request events
- **Amazon CloudFront KeyValueStore**
  - Stores routing configuration mappings
  - Used by the CloudFront Function to determine target origins
- **Amazon Simple Queue Service (SQS)**
  - Handles asynchronous updates to KeyValueStore configurations
- **Amazon API Gateway (Cluster A)**
  - REST API endpoint for Cluster A
  - Handles requests for Tenant 1
- **Amazon API Gateway (Cluster B)**
  - REST API endpoint for Cluster B
  - Handles requests for Tenant 2
- **AWS Lambda (Cluster A)**
  - Backend function processing Tenant 1 requests
  - Integrated with API Gateway (Cluster A)
- **AWS Lambda (Cluster B)**
  - Backend function processing Tenant 2 requests
  - Integrated with API Gateway (Cluster B)

### Example

In this example, a user belonging to Tenant 1 sends an HTTP request to the CloudFront distribution. The CloudFront Function intercepts this request and retrieves the tenant's assigned cluster information from CloudFront KeyValueStore. Based on this mapping, the function modifies the target origin to API Cluster A, causing CloudFront to route the request to the appropriate destination. This routing happens transparently - CloudFront does not issue a redirect, but rather forwards the original request directly to the determined origin.

![Tenant Router](cff-tenant-router.png)

## Deployment

These deployment instructions are optimized to best work on Mac. Deployment in another OS may require additional steps.

### Deploy using CDK

1. [Install CDK](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html):
   Install and configure CDK on your location machine. CDK is used to generate the CloudFormation template which is deployed in your AWS account.

2. Navigate to the `cdk` directory:

```
cd cdk
```

3. Create and activate a Python virtualenv:

```
python3 -m venv .venv
source .venv/bin/activate
```

4. Install the required dependencies:

```
pip install -r requirements.txt
```

5. Deploy the CDK app:

```
cdk deploy
```

Review the proposed changes and type "y" to confirm.
Wait for the deployment to complete; this usually takes 5 to 10 minutes.

## Testing

### Populate CloudFront KeyValueStore

After deploying the infrastructure, we need to configure the tenant-to-cluster mappings in CloudFront KeyValueStore. These mappings determine which cluster will serve requests for each tenant.

The included `bin/onboard_tenants.sh` script demonstrates this process by creating mappings for:

- Tenant 1 → Cluster A
- Tenant 2 → Cluster B

The script works by sending messages to SQS, which triggers a Lambda function that updates the KeyValueStore configurations. This asynchronous approach ensures reliable updates to the routing rules.

1. Execute the script:

```
chmod +x bin/onboard_tenants.sh  # Add execute permissions
bin/onboard_tenants.sh
```

### Send HTTP Requests

Now that the infrastructure is deployed and KeyValueStore holds the tenant-to-cluster mappings, we can send HTTP requests for each tenant to verify the routing behavior.

1. Retrieve the CloudFront distribution URL from CloudFormation exports:

```
export URL=$(aws cloudformation list-exports --query "Exports[?Name=='MultiClusterRoutingDistributionUrl'].Value" --output text)
```

2. Send a request for Tenant 1:

```
curl ${URL}/tenant_1
```

The API should respond with "Hello from cluster_a".

3. Send a request for Tenant 2:

```
curl ${URL}/tenant_2
```

The API should respond with "Hello from cluster_b".

## Clean Up

Delete the CloudFormation stacks deployed by CDK:

```
cdk destroy
```
