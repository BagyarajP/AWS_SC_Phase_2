"""
Upload synthetic data CSV files to S3 bucket in us-east-1
"""

import boto3
import os
from pathlib import Path

# Configuration
REGION = 'us-east-1'
BUCKET_NAME = 'supply-chain-data-bucket'  # Update with your actual bucket name
DATA_DIR = 'data/synthetic'
S3_PREFIX = 'synthetic_data/'

def upload_files_to_s3():
    """Upload all CSV files from data/synthetic to S3"""
    
    # Initialize S3 client
    s3_client = boto3.client('s3', region_name=REGION)
    
    # Check if bucket exists, create if not
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"✓ Bucket '{BUCKET_NAME}' exists")
    except:
        print(f"Creating bucket '{BUCKET_NAME}' in {REGION}...")
        if REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3_client.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        print(f"✓ Bucket created")
    
    # Get all CSV files
    data_path = Path(DATA_DIR)
    csv_files = list(data_path.glob('*.csv'))
    
    if not csv_files:
        print(f"Error: No CSV files found in {DATA_DIR}")
        print("Please run 'python scripts/generate_synthetic_data.py' first")
        return
    
    print()
    print("=" * 60)
    print(f"Uploading {len(csv_files)} files to S3")
    print("=" * 60)
    print()
    
    # Upload each file
    for csv_file in csv_files:
        file_name = csv_file.name
        s3_key = f"{S3_PREFIX}{file_name}"
        
        print(f"Uploading {file_name}...", end=' ')
        
        try:
            s3_client.upload_file(
                str(csv_file),
                BUCKET_NAME,
                s3_key
            )
            print("✓")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print()
    print("=" * 60)
    print("Upload Complete!")
    print("=" * 60)
    print()
    print(f"Files uploaded to: s3://{BUCKET_NAME}/{S3_PREFIX}")
    print()
    print("Next steps:")
    print("  1. Create Redshift Serverless workgroup in AWS Console")
    print("  2. Run schema.sql to create tables")
    print("  3. Use AWS Glue or COPY commands to load data into Redshift")

if __name__ == '__main__':
    upload_files_to_s3()
