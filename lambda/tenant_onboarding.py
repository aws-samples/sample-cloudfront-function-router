import json
import os

import boto3
from botocore.config import Config

CLUSTER_ORIGIN_MAP = {
    "cluster_1": os.environ["CLUSTER_1"],
    "cluster_2": os.environ["CLUSTER_2"],
}
KVS_ARN = os.environ["KVS_ARN"]

my_config = Config(signature_version="v4")
kvs_client = boto3.client(
    "cloudfront-keyvaluestore", config=my_config, region_name="us-east-1"
)


def handler(event, _):
    for record in event["Records"]:
        print(f"Message body: {record['body']}")
        body = json.loads(record["body"])
        tenant_id = body["tenant_id"]
        target_cluster = CLUSTER_ORIGIN_MAP[body["cluster_id"]]
        kvs_e_tag = kvs_client.describe_key_value_store(KvsARN=KVS_ARN)["ETag"]
        print(f"Current KVS ETag: {kvs_e_tag}")
        kvs_client.put_key(
            Key=tenant_id,
            Value=target_cluster,
            KvsARN=KVS_ARN,
            IfMatch=kvs_e_tag,
        )
        print(f"Updated KVS with tenant {tenant_id} to cluster {target_cluster}")


if __name__ == "__main__":
    event = {
        "Records": [
            {
                "body": {
                    "tenant_id": "tenant_1",
                    "cluster_id": "cluster_2",
                }
            },
        ]
    }
    handler(event, None)
