import os


def handler(*_):
    cluster = os.environ["CLUSTER"]
    return {
        "statusCode": 200,
        "body": f"Hello from {cluster}!",
    }
