"""
Supply Chain AI Platform - AWS Glue ETL Job for Redshift Serverless

This Glue job extracts synthetic data from S3, transforms it to match
the Redshift schema, and loads it into Redshift Serverless using the Data API.

Requirements:
- 6.1: Extract data from S3 buckets
- 6.2: Transform data to match Redshift schema
- 6.3: Load transformed data into Redshift Serverless using Data API with retry logic
- 6.5: Error handling with CloudWatch logging
- 6.6: Track ingestion metrics
"""

import sys
import logging
from datetime import datetime
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import col, lit, current_timestamp, when
from pyspark.sql.types import *
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'S3_BUCKET',
    'S3_PREFIX',
    'REDSHIFT_WORKGROUP',
    'REDSHIFT_DATABASE',
    'REDSHIFT_TEMP_DIR',
    'REDSHIFT_IAM_ROLE'
])

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# S3 client for file operations
s3_client = boto3.client('s3')

# Tables to process
TABLES = [
    'product',
    'warehouse',
    'supplier',
    'inventory',
    'purchase_order_header',
    'purchase_order_line',
    'sales_order_header',
    'sales_order_line'
]

# Metrics tracking
metrics = {
    'job_start_time': datetime.now().isoformat(),
    'tables_processed': 0,
    'total_records_read': 0,
    'total_records_written': 0,
    'total_records_failed': 0,
    'errors': []
}


def check_s3_file_exists(bucket, key):
    """
    Check if a file exists in S3
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        bool: True if file exists, False otherwise
    """
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        logger.warning(f"File not found: s3://{bucket}/{key} - {str(e)}")
        return False


# Schema definitions for each table
TABLE_SCHEMAS = {
    'product': {
        'product_id': StringType(),
        'sku': StringType(),
        'product_name': StringType(),
        'category': StringType(),
        'unit_cost': DecimalType(10, 2),
        'reorder_point': IntegerType(),
        'reorder_quantity': IntegerType(),
        'created_at': TimestampType()
    },
    'warehouse': {
        'warehouse_id': StringType(),
        'warehouse_name': StringType(),
        'location': StringType(),
        'capacity': IntegerType(),
        'created_at': TimestampType()
    },
    'supplier': {
        'supplier_id': StringType(),
        'supplier_name': StringType(),
        'contact_email': StringType(),
        'reliability_score': DecimalType(3, 2),
        'avg_lead_time_days': IntegerType(),
        'defect_rate': DecimalType(5, 4),
        'created_at': TimestampType()
    },
    'inventory': {
        'inventory_id': StringType(),
        'product_id': StringType(),
        'warehouse_id': StringType(),
        'quantity_on_hand': IntegerType(),
        'last_updated': TimestampType()
    },
    'purchase_order_header': {
        'po_id': StringType(),
        'supplier_id': StringType(),
        'order_date': DateType(),
        'expected_delivery_date': DateType(),
        'total_amount': DecimalType(12, 2),
        'status': StringType(),
        'created_by': StringType(),
        'approved_by': StringType(),
        'approved_at': TimestampType(),
        'created_at': TimestampType()
    },
    'purchase_order_line': {
        'po_line_id': StringType(),
        'po_id': StringType(),
        'product_id': StringType(),
        'quantity': IntegerType(),
        'unit_price': DecimalType(10, 2),
        'line_total': DecimalType(12, 2),
        'created_at': TimestampType()
    },
    'sales_order_header': {
        'so_id': StringType(),
        'order_date': DateType(),
        'warehouse_id': StringType(),
        'status': StringType(),
        'created_at': TimestampType()
    },
    'sales_order_line': {
        'so_line_id': StringType(),
        'so_id': StringType(),
        'product_id': StringType(),
        'quantity': IntegerType(),
        'created_at': TimestampType()
    }
}


def validate_schema(df, table_name):
    """
    Validate that DataFrame has all required columns
    
    Args:
        df: Spark DataFrame
        table_name: Name of the table
        
    Returns:
        bool: True if schema is valid
        
    Requirement 6.2: Schema validation
    """
    expected_schema = TABLE_SCHEMAS.get(table_name, {})
    df_columns = set(df.columns)
    expected_columns = set(expected_schema.keys())
    
    missing_columns = expected_columns - df_columns
    extra_columns = df_columns - expected_columns
    
    if missing_columns:
        logger.error(f"Table '{table_name}' missing columns: {missing_columns}")
        return False
    
    if extra_columns:
        logger.warning(f"Table '{table_name}' has extra columns (will be ignored): {extra_columns}")
    
    return True


def transform_data(dynamic_frame, table_name):
    """
    Transform data to match Redshift schema
    
    Args:
        dynamic_frame: Input DynamicFrame from S3
        table_name: Name of the table
        
    Returns:
        DynamicFrame with transformed data
        
    Requirement 6.2: Transform data with schema validation, type conversions, and null handling
    """
    logger.info(f"Transforming data for table '{table_name}'")
    
    try:
        # Convert to Spark DataFrame for easier manipulation
        df = dynamic_frame.toDF()
        
        # Validate schema
        if not validate_schema(df, table_name):
            raise ValueError(f"Schema validation failed for table '{table_name}'")
        
        # Get expected schema
        expected_schema = TABLE_SCHEMAS[table_name]
        
        # Apply data type conversions and null handling
        for column_name, column_type in expected_schema.items():
            if column_name in df.columns:
                # Handle null values
                if isinstance(column_type, StringType):
                    # Replace empty strings with NULL
                    df = df.withColumn(
                        column_name,
                        col(column_name).cast(column_type)
                    )
                    df = df.withColumn(
                        column_name,
                        when(col(column_name) == "", None).otherwise(col(column_name))
                    )
                elif isinstance(column_type, (IntegerType, DecimalType)):
                    # Cast numeric types, invalid values become NULL
                    df = df.withColumn(
                        column_name,
                        col(column_name).cast(column_type)
                    )
                elif isinstance(column_type, (DateType, TimestampType)):
                    # Cast date/timestamp types
                    df = df.withColumn(
                        column_name,
                        col(column_name).cast(column_type)
                    )
                else:
                    # Default cast
                    df = df.withColumn(
                        column_name,
                        col(column_name).cast(column_type)
                    )
        
        # Select only expected columns in correct order
        df = df.select(*expected_schema.keys())
        
        # Filter out records with NULL primary keys
        primary_keys = {
            'product': 'product_id',
            'warehouse': 'warehouse_id',
            'supplier': 'supplier_id',
            'inventory': 'inventory_id',
            'purchase_order_header': 'po_id',
            'purchase_order_line': 'po_line_id',
            'sales_order_header': 'so_id',
            'sales_order_line': 'so_line_id'
        }
        
        pk_column = primary_keys.get(table_name)
        if pk_column:
            initial_count = df.count()
            df = df.filter(col(pk_column).isNotNull())
            filtered_count = df.count()
            
            if initial_count > filtered_count:
                invalid_count = initial_count - filtered_count
                logger.warning(f"Filtered {invalid_count} records with NULL primary key from '{table_name}'")
                metrics['total_records_failed'] += invalid_count
        
        # Convert back to DynamicFrame
        transformed_frame = DynamicFrame.fromDF(df, glueContext, f"{table_name}_transformed")
        
        logger.info(f"Successfully transformed {transformed_frame.count()} records for '{table_name}'")
        
        return transformed_frame
        
    except Exception as e:
        error_msg = f"Error transforming data for table '{table_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        metrics['errors'].append({
            'table': table_name,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        raise


def extract_from_s3(table_name):
    """
    Extract data from S3 CSV file
    
    Args:
        table_name: Name of the table (matches CSV filename)
        
    Returns:
        DynamicFrame or None if file not found
        
    Requirement 6.1: Extract data from S3 buckets with error handling
    """
    bucket = args['S3_BUCKET']
    s3_key = f"{args['S3_PREFIX']}{table_name}.csv"
    s3_path = f"s3://{bucket}/{s3_key}"
    
    logger.info(f"Extracting data for table '{table_name}' from {s3_path}")
    
    # Check if file exists
    if not check_s3_file_exists(bucket, s3_key):
        error_msg = f"Missing file for table '{table_name}': {s3_path}"
        logger.error(error_msg)
        metrics['errors'].append({
            'table': table_name,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        return None
    
    try:
        # Read CSV from S3 using Glue DynamicFrame
        dynamic_frame = glueContext.create_dynamic_frame.from_options(
            connection_type="s3",
            connection_options={
                "paths": [s3_path]
            },
            format="csv",
            format_options={
                "withHeader": True,
                "separator": ","
            }
        )
        
        record_count = dynamic_frame.count()
        logger.info(f"Successfully extracted {record_count} records from {table_name}")
        metrics['total_records_read'] += record_count
        
        return dynamic_frame
        
    except Exception as e:
        error_msg = f"Error extracting data from {s3_path}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        metrics['errors'].append({
            'table': table_name,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        return None


def load_to_redshift(dynamic_frame, table_name, retry_count=3):
    """
    Load transformed data into Redshift Serverless table using Redshift Data API
    
    Args:
        dynamic_frame: Transformed DynamicFrame
        table_name: Target Redshift table name
        retry_count: Number of retry attempts for connection failures
        
    Requirement 6.3: Load data to Redshift Serverless using Data API with retry logic
    """
    logger.info(f"Loading data to Redshift Serverless table '{table_name}' using Data API")
    
    # Initialize Redshift Data API client
    redshift_data = boto3.client('redshift-data', region_name='us-east-1')
    
    for attempt in range(retry_count):
        try:
            # First, write data to S3 as staging (required for COPY command)
            staging_path = f"{args['REDSHIFT_TEMP_DIR']}/staging/{table_name}/"
            logger.info(f"Writing data to staging location: {staging_path}")
            
            # Convert DynamicFrame to DataFrame and write to S3 as Parquet
            df = dynamic_frame.toDF()
            df.write.mode('overwrite').parquet(staging_path)
            
            record_count = dynamic_frame.count()
            logger.info(f"Staged {record_count} records to S3")
            
            # Construct COPY command for Redshift Serverless
            # Using Parquet format for better performance
            copy_command = f"""
            COPY {table_name}
            FROM '{staging_path}'
            IAM_ROLE '{args.get('REDSHIFT_IAM_ROLE', 'default')}'
            FORMAT AS PARQUET;
            """
            
            logger.info(f"Executing COPY command via Redshift Data API for table '{table_name}'")
            
            # Execute COPY command using Redshift Data API (serverless connectivity)
            response = redshift_data.execute_statement(
                WorkgroupName=args.get('REDSHIFT_WORKGROUP', 'supply-chain-workgroup'),
                Database=args['REDSHIFT_DATABASE'],
                Sql=copy_command
            )
            
            statement_id = response['Id']
            logger.info(f"COPY statement submitted with ID: {statement_id}")
            
            # Poll for statement completion with timeout
            import time
            max_wait_time = 300  # 5 minutes timeout
            poll_interval = 2  # Poll every 2 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                status_response = redshift_data.describe_statement(Id=statement_id)
                status = status_response['Status']
                
                if status == 'FINISHED':
                    logger.info(f"Successfully loaded {record_count} records to '{table_name}'")
                    metrics['total_records_written'] += record_count
                    return True
                    
                elif status == 'FAILED':
                    error_msg = status_response.get('Error', 'Unknown error')
                    raise Exception(f"COPY command failed: {error_msg}")
                    
                elif status == 'ABORTED':
                    raise Exception("COPY command was aborted")
                
                # Status is SUBMITTED or STARTED, continue polling
                time.sleep(poll_interval)
                elapsed_time += poll_interval
            
            # Timeout reached
            raise Exception(f"COPY command timed out after {max_wait_time} seconds")
            
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(
                    f"Attempt {attempt + 1}/{retry_count} failed for table '{table_name}'. "
                    f"Retrying in {wait_time} seconds... Error: {str(e)}"
                )
                import time
                time.sleep(wait_time)
            else:
                error_msg = f"Failed to load data to Redshift Serverless table '{table_name}' after {retry_count} attempts: {str(e)}"
                logger.error(error_msg, exc_info=True)
                metrics['errors'].append({
                    'table': table_name,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                metrics['total_records_failed'] += dynamic_frame.count()
                raise


def log_metrics_to_cloudwatch():
    """
    Log ETL metrics to CloudWatch
    
    Requirement 6.6: Track ingestion metrics including record count and success rate
    """
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        # Prepare metrics
        metric_data = [
            {
                'MetricName': 'TablesProcessed',
                'Value': metrics['tables_processed'],
                'Unit': 'Count',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'RecordsRead',
                'Value': metrics['total_records_read'],
                'Unit': 'Count',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'RecordsWritten',
                'Value': metrics['total_records_written'],
                'Unit': 'Count',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'RecordsFailed',
                'Value': metrics['total_records_failed'],
                'Unit': 'Count',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'SuccessRate',
                'Value': metrics['success_rate'],
                'Unit': 'Percent',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'ErrorCount',
                'Value': len(metrics['errors']),
                'Unit': 'Count',
                'Timestamp': datetime.now()
            }
        ]
        
        # Put metrics to CloudWatch
        cloudwatch.put_metric_data(
            Namespace='SupplyChainAI/ETL',
            MetricData=metric_data
        )
        
        logger.info("Successfully logged metrics to CloudWatch")
        
    except Exception as e:
        logger.error(f"Failed to log metrics to CloudWatch: {str(e)}", exc_info=True)


def main():
    """Main ETL execution"""
    logger.info("=" * 60)
    logger.info("Starting AWS Glue ETL Job for Redshift Serverless")
    logger.info(f"Job Name: {args['JOB_NAME']}")
    logger.info(f"S3 Bucket: {args['S3_BUCKET']}")
    logger.info(f"S3 Prefix: {args['S3_PREFIX']}")
    logger.info(f"Redshift Workgroup: {args['REDSHIFT_WORKGROUP']}")
    logger.info(f"Redshift Database: {args['REDSHIFT_DATABASE']}")
    logger.info(f"Using Redshift Data API for serverless connectivity")
    logger.info("=" * 60)
    
    # Process each table
    for table_name in TABLES:
        logger.info(f"\nProcessing table: {table_name}")
        
        try:
            # Extract from S3
            dynamic_frame = extract_from_s3(table_name)
            
            if dynamic_frame is None:
                logger.warning(f"Skipping table '{table_name}' due to extraction failure")
                continue
            
            # Transform data (Requirement 6.2)
            transformed_frame = transform_data(dynamic_frame, table_name)
            
            # Load to Redshift (Requirement 6.3)
            load_to_redshift(transformed_frame, table_name)
            
            metrics['tables_processed'] += 1
            
        except Exception as e:
            # Requirement 6.5: Log errors to CloudWatch and skip invalid records
            error_msg = f"Unexpected error processing table '{table_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            metrics['errors'].append({
                'table': table_name,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            # Continue processing other tables instead of failing entire job
            logger.info(f"Continuing with next table after error in '{table_name}'")
    
    # Log final metrics
    metrics['job_end_time'] = datetime.now().isoformat()
    metrics['success_rate'] = (
        metrics['total_records_written'] / metrics['total_records_read'] * 100
        if metrics['total_records_read'] > 0 else 0
    )
    
    logger.info("\n" + "=" * 60)
    logger.info("ETL Job Complete")
    logger.info(f"Tables Processed: {metrics['tables_processed']}/{len(TABLES)}")
    logger.info(f"Total Records Read: {metrics['total_records_read']}")
    logger.info(f"Total Records Written: {metrics['total_records_written']}")
    logger.info(f"Total Records Failed: {metrics['total_records_failed']}")
    logger.info(f"Success Rate: {metrics['success_rate']:.2f}%")
    logger.info(f"Errors: {len(metrics['errors'])}")
    
    # Log detailed errors if any
    if metrics['errors']:
        logger.info("\nDetailed Errors:")
        for i, error in enumerate(metrics['errors'], 1):
            logger.info(f"  {i}. Table: {error['table']}")
            logger.info(f"     Error: {error['error']}")
            logger.info(f"     Time: {error['timestamp']}")
    
    logger.info("=" * 60)
    
    # Requirement 6.6: Log metrics to CloudWatch
    log_metrics_to_cloudwatch()
    
    # Commit job
    job.commit()


if __name__ == '__main__':
    main()
