# AWS Glue ETL Job - Supply Chain AI Platform (Redshift Serverless)

This directory contains the AWS Glue ETL job for ingesting synthetic data from S3 into Redshift Serverless using the Data API.

## Overview

The ETL job performs the following operations:
1. **Extract**: Reads CSV files from S3 bucket
2. **Transform**: Validates schema, converts data types, handles null values
3. **Load**: Writes data to Redshift Serverless using Data API and COPY command with retry logic
4. **Monitor**: Logs metrics to CloudWatch and tracks success rates

## Key Features

- **Serverless Connectivity**: Uses Redshift Data API (no connection pooling required)
- **Automatic Retry Logic**: Exponential backoff for connection failures (up to 3 attempts)
- **Comprehensive Error Handling**: Logs errors to CloudWatch and continues processing
- **Metrics Tracking**: Records count, success rate, and error tracking

## Requirements

- AWS Glue service access
- S3 bucket with synthetic data CSV files
- Redshift Serverless workgroup with database schema created
- IAM role with appropriate permissions (Glue, S3, Redshift Data API)

## Files

- `etl_job.py` - Main Glue ETL job script with Redshift Serverless Data API integration

## Deployment Steps

### 1. Upload Script to S3

```bash
aws s3 cp etl_job.py s3://your-glue-scripts-bucket/supply-chain-ai/
```

### 2. Create Glue Job (Redshift Serverless)

In AWS Console:
1. Go to AWS Glue → ETL Jobs
2. Click "Create job"
3. Configure:
   - Name: `supply-chain-etl-job`
   - IAM Role: Select role with Glue, S3, and Redshift Data API permissions
   - Type: Spark
   - Glue version: 4.0
   - Language: Python 3
   - Script location: `s3://your-glue-scripts-bucket/supply-chain-ai/etl_job.py`

4. Add job parameters:
   - `--S3_BUCKET`: Your S3 bucket name (e.g., `supply-chain-data-bucket`)
   - `--S3_PREFIX`: S3 prefix for data files (e.g., `synthetic_data/`)
   - `--REDSHIFT_WORKGROUP`: Redshift Serverless workgroup name (e.g., `supply-chain-workgroup`)
   - `--REDSHIFT_DATABASE`: `supply_chain`
   - `--REDSHIFT_TEMP_DIR`: `s3://your-bucket/temp/`
   - `--REDSHIFT_IAM_ROLE`: IAM role ARN for Redshift to access S3 (e.g., `arn:aws:iam::123456789012:role/RedshiftS3AccessRole`)

5. Configure job properties:
   - Max capacity: 2 DPU (for MVP)
   - Timeout: 60 minutes
   - Max retries: 1

### 3. IAM Permissions

The Glue job IAM role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket/*",
        "arn:aws:s3:::your-bucket"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-serverless:GetWorkgroup",
        "redshift-serverless:GetNamespace"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

Additionally, the Redshift IAM role (specified in `REDSHIFT_IAM_ROLE` parameter) needs S3 read access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket/*",
        "arn:aws:s3:::your-bucket"
      ]
    }
  ]
}
```

### 4. Run the Job

#### Manual Trigger (AWS Console)
1. Go to AWS Glue → ETL Jobs
2. Select `supply-chain-etl-job`
3. Click "Run job"

#### Manual Trigger (AWS CLI)
```bash
aws glue start-job-run --job-name supply-chain-etl-job
```

#### Scheduled Trigger (Optional)
For recurring data loads, create a trigger:
```bash
aws glue create-trigger \
  --name supply-chain-daily-etl \
  --type SCHEDULED \
  --schedule "cron(0 0 * * ? *)" \
  --actions JobName=supply-chain-etl-job
```

## Monitoring

### CloudWatch Logs
View job execution logs:
1. Go to AWS Glue → ETL Jobs
2. Select `supply-chain-etl-job`
3. Click "Logs" tab
4. View CloudWatch log streams

### CloudWatch Metrics
Custom metrics are published to namespace `SupplyChainAI/ETL`:
- `TablesProcessed` - Number of tables successfully processed
- `RecordsRead` - Total records extracted from S3
- `RecordsWritten` - Total records loaded to Redshift
- `RecordsFailed` - Total records that failed validation
- `SuccessRate` - Percentage of successful record loads
- `ErrorCount` - Number of errors encountered

### View Metrics in Console
1. Go to CloudWatch → Metrics
2. Select namespace: `SupplyChainAI/ETL`
3. View metric graphs

## Error Handling

The ETL job implements comprehensive error handling:

1. **Missing Files**: Logs warning and skips table
2. **Schema Validation Errors**: Logs error and skips table
3. **Data Type Conversion Errors**: Invalid records filtered out
4. **Redshift Connection Errors**: Retries up to 3 times with exponential backoff
5. **Load Failures**: Logs error and continues with next table

All errors are logged to CloudWatch with detailed context.

## Data Validation

The job validates:
- All required columns are present
- Data types match Redshift schema
- Primary keys are not NULL
- Numeric values are within valid ranges

Invalid records are filtered out and counted in metrics.

## Tables Processed

The ETL job processes the following tables:
1. `product` - Product catalog (2,000 SKUs)
2. `warehouse` - Warehouse locations (3 warehouses)
3. `supplier` - Supplier information (500 suppliers)
4. `inventory` - Current inventory levels
5. `purchase_order_header` - Purchase order headers
6. `purchase_order_line` - Purchase order line items
7. `sales_order_header` - Sales order headers
8. `sales_order_line` - Sales order line items

## Troubleshooting

### Job Fails with "Connection Timeout"
- Check that Redshift Serverless workgroup is in AVAILABLE state
- Verify IAM role has `redshift-data:ExecuteStatement` permission
- Ensure the workgroup name in job parameters is correct
- Check CloudWatch logs for detailed error messages

### Job Fails with "Access Denied" on Redshift Data API
- Verify Glue IAM role has `redshift-data:*` permissions
- Check that the Redshift IAM role (for COPY command) has S3 read access
- Ensure the workgroup allows access from the Glue job's IAM role

### Job Fails with "Access Denied" on S3
- Verify IAM role has `s3:GetObject` permission on source bucket
- Verify IAM role has `s3:PutObject` permission on temp directory

### Records Not Loading to Redshift
- Check CloudWatch logs for validation errors
- Verify Redshift schema matches expected schema in `etl_job.py`
- Check for NULL primary keys in source data

### Low Success Rate
- Review CloudWatch logs for specific validation errors
- Check source CSV files for data quality issues
- Verify data types in CSV match expected schema

## Performance Tuning

For larger datasets:
- Increase DPU allocation (currently 2 DPU)
- Enable job bookmarks to process only new data
- Partition large tables by date
- Use Redshift COPY command optimizations

## Next Steps

After successful ETL job execution:
1. Verify data in Redshift tables
2. Run data quality checks
3. Configure Lambda agents to use loaded data
4. Set up scheduled triggers for recurring loads
