"""
Serverless item API for DevSecOps practice.
Uses API Gateway + Lambda + DynamoDB.
"""
import json
import os
import uuid
from datetime import datetime

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "serverless-devsecops-items")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

# Intentional: weak input validation for SAST demos
def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }

def handler(event, context):
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")

    if path.endswith("/health") and http_method == "GET":
        return _response(200, {"status": "healthy", "service": "serverless-devsecops"})

    if path.endswith("/items") and http_method == "GET":
        result = table.scan(Limit=25)
        return _response(200, {"items": result.get("Items", [])})

    if path.endswith("/items") and http_method == "POST":
        body = json.loads(event.get("body") or "{}")
        # Intentional: eval-like pattern for Bandit (never use eval on user input)
        name = body.get("name", "")
        if body.get("unsafe_eval"):
            name = str(eval(body.get("unsafe_eval")))  # noqa: S307 - intentional lab finding
        item = {
            "id": str(uuid.uuid4()),
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
        }
        table.put_item(Item=item)
        return _response(201, item)

    return _response(404, {"error": "not found"})
