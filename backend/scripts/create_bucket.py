#!/usr/bin/env python3
"""Create MinIO bucket for SampleTok"""

import boto3
from botocore.exceptions import ClientError

# MinIO configuration
endpoint_url = "http://localhost:9000"
access_key = "minioadmin"
secret_key = "minioadmin"
bucket_name = "sampletok-samples"

# Create S3 client for MinIO
s3_client = boto3.client(
    's3',
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name='us-east-1'
)

try:
    # Check if bucket exists
    s3_client.head_bucket(Bucket=bucket_name)
    print(f"✅ Bucket '{bucket_name}' already exists")
except ClientError as e:
    error_code = int(e.response['Error']['Code'])
    if error_code == 404:
        # Create bucket
        try:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"✅ Created bucket '{bucket_name}'")

            # Set bucket policy to allow public read
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }
                ]
            }

            import json
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print(f"✅ Set public read policy for bucket")

        except Exception as create_error:
            print(f"❌ Failed to create bucket: {create_error}")
    else:
        print(f"❌ Error checking bucket: {e}")

# List all buckets
print("\nAll buckets in MinIO:")
response = s3_client.list_buckets()
for bucket in response['Buckets']:
    print(f"  - {bucket['Name']}")