#!/usr/bin/env python3
"""Check MinIO for uploaded files"""

import boto3

# MinIO configuration
s3_client = boto3.client(
    's3',
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    region_name='us-east-1'
)

bucket_name = "sampletok-samples"

try:
    # List all objects in bucket
    response = s3_client.list_objects_v2(Bucket=bucket_name)

    if 'Contents' in response:
        print(f"Files in '{bucket_name}' bucket:")
        for obj in response['Contents']:
            size_kb = obj['Size'] / 1024
            print(f"  - {obj['Key']} ({size_kb:.2f} KB)")
    else:
        print(f"No files found in '{bucket_name}' bucket")

except Exception as e:
    print(f"Error: {e}")