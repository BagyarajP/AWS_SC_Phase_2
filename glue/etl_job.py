"""
Supply Chain AI Platform - AWS Glue Python Shell ETL Job for Redshift Serverless

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
import time
import csv
import io
from datetime import datetime
import boto3
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Job parameters - using getResolvedOptions for Glue compatibility
def get_job_parameters():
    """Get job parameters from Glue job arguments"""
    params = {}
    
    # Parse command line arguments
    for arg in sys.argv[1:]:  # Skip script name
        if arg.startswith('--'):
            if '=' in arg:
                key, value = arg[2:].split('=', 1)
                params[key] = value
            else:
                # Handle --key value format
                key = arg[2:]
                params[key] = None
    
    return params

# Get all parameters
job_params = get_job_parameters()

# Extract specific parameters with defaults
# TEMPORARY FIX: Hardcode your bucket name here
S3_BUCKET = job_params.get('S3_BUCKET', 'supply-chain-data-193871648423')  # Changed default
S3_PREFIX = job_params.get('S3_PREFIX', 'synthetic_data/')
REDSHIFT_WORKGROUP = job_params.get('REDSHIFT_WORKGROUP', 'supply-chain-workgroup')
REDSHIFT_DATABASE = job_params.get('REDSHIFT_DATABASE', 'supply_chain')
AWS_REGION = job_params.get('AWS_REGION', 'us-east-1')

# Log parameters for debugging
logger.info(f"Job Parameters Received:")
logger.info(f"  S3_BUCKET: {S3_BUCKET}")
logger.info(f"  S3_PREFIX: {S3_PREFIX}")
logger.info(f"  REDSHIFT_WORKGROUP: {REDSHIFT_WORKGROUP}")
logger.info(f"  REDSHIFT_DATABASE: {REDSHIFT_DATABASE}")
logger.info(f"  AWS_REGION: {AWS_REGION}")

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=AWS_REGION)
redshift_data = boto3.client('redshift-data', region_name=AWS_REGION)
cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)

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


def extract_from_s3(table_name):
    """
    Extract data from S3 CSV file
    
    Args:
        table_name: Name of the table (matches CSV filename)
        
    Returns:
        pandas DataFrame or None if file not found
        
    Requirement 6.1: Extract data from S3 buckets with error handling
    """
    s3_key = f"{S3_PREFIX}{table_name}.csv"
    s3_path = f"s3://{S3_BUCKET}/{s3_key}"
    
    logger.info(f"Extracting data for table '{table_name}' from {s3_path}")
    
    # Check if file exists
    if not check_s3_file_exists(S3_BUCKET, s3_key):
        error_msg = f"Missing file for table '{table_name}': {s3_path}"
        logger.error(error_msg)
        metrics['errors'].append({
            'table': table_name,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        return None
    
    try:
        # Read CSV from S3
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        csv_content = response['Body'].read().decode('utf-8')
        
        # Parse CSV into pandas DataFrame
        df = pd.read_csv(io.StringIO(csv_content))
        
        record_count = len(df)
        logger.info(f"Successfully extracted {record_count} records from {table_name}")
        metrics['total_records_read'] += record_count
        
        return df
        
    except Exception as e:
        error_msg = f"Error extracting data from {s3_path}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        metrics['errors'].append({
            'table': table_name,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        return None


def transform_data(df, table_name):
    """
    Transform data to match Redshift schema
    
    Args:
        df: pandas DataFrame
        table_name: Name of the table
        
    Returns:
        Transformed pandas DataFrame
        
    Requirement 6.2: Transform data with schema validation, type conversions, and null handling
    """
    logger.info(f"Transforming data for table '{table_name}'")
    
    try:
        # Remove rows with NULL primary keys
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
        if pk_column and pk_column in df.columns:
            initial_count = len(df)
            df = df[df[pk_column].notna()]
            filtered_count = len(df)
            
            if initial_count > filtered_count:
                invalid_count = initial_count - filtered_count
                logger.warning(f"Filtered {invalid_count} records with NULL primary key from '{table_name}'")
                metrics['total_records_failed'] += invalid_count
        
        # Replace empty strings with None (NULL in SQL)
        df = df.replace('', None)
        
        # Handle NaN values
        df = df.where(pd.notna(df), None)
        
        logger.info(f"Successfully transformed {len(df)} records for '{table_name}'")
        
        return df
        
    except Exception as e:
        error_msg = f"Error transforming data for table '{table_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        metrics['errors'].append({
            'table': table_name,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        raise


def execute_redshift_statement(sql, wait_for_completion=True, timeout=300):
    """
    Execute SQL statement using Redshift Data API
    
    Args:
        sql: SQL statement to execute
        wait_for_completion: Whether to wait for statement to complete
        timeout: Maximum wait time in seconds
        
    Returns:
        Statement ID if successful
        
    Requirement 6.3: Use Redshift Data API for serverless connectivity
    """
    try:
        # Execute statement
        response = redshift_data.execute_statement(
            WorkgroupName=REDSHIFT_WORKGROUP,
            Database=REDSHIFT_DATABASE,
            Sql=sql
        )
        
        statement_id = response['Id']
        logger.info(f"Statement submitted with ID: {statement_id}")
        
        if not wait_for_completion:
            return statement_id
        
        # Poll for completion
        elapsed_time = 0
        poll_interval = 2
        
        while elapsed_time < timeout:
            status_response = redshift_data.describe_statement(Id=statement_id)
            status = status_response['Status']
            
            if status == 'FINISHED':
                logger.info(f"Statement completed successfully")
                return statement_id
                
            elif status == 'FAILED':
                error_msg = status_response.get('Error', 'Unknown error')
                raise Exception(f"Statement failed: {error_msg}")
                
            elif status == 'ABORTED':
                raise Exception("Statement was aborted")
            
            # Continue polling
            time.sleep(poll_interval)
            elapsed_time += poll_interval
        
        raise Exception(f"Statement timed out after {timeout} seconds")
        
    except Exception as e:
        logger.error(f"Error executing Redshift statement: {str(e)}", exc_info=True)
        raise


def load_to_redshift(df, table_name, retry_count=3):
    """
    Load transformed data into Redshift Serverless table using INSERT statements
    
    Args:
        df: pandas DataFrame with transformed data
        table_name: Target Redshift table name
        retry_count: Number of retry attempts for connection failures
        
    Requirement 6.3: Load data to Redshift Serverless using Data API with retry logic
    """
    logger.info(f"Loading data to Redshift Serverless table '{table_name}' using Data API")
    
    if df.empty:
        logger.warning(f"No data to load for table '{table_name}'")
        return
    
    record_count = len(df)
    
    for attempt in range(retry_count):
        try:
            # Clear existing data (for MVP - in production, use UPSERT logic)
            truncate_sql = f"TRUNCATE TABLE {table_name};"
            logger.info(f"Truncating table '{table_name}'")
            execute_redshift_statement(truncate_sql)
            
            # Batch insert records (500 at a time to avoid statement size limits)
            batch_size = 500
            total_batches = (record_count + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, record_count)
                batch_df = df.iloc[start_idx:end_idx]
                
                # Build INSERT statement
                columns = ', '.join(batch_df.columns)
                
                # Build VALUES clauses
                values_list = []
                for _, row in batch_df.iterrows():
                    values = []
                    for val in row:
                        if pd.isna(val) or val is None:
                            values.append('NULL')
                        elif isinstance(val, str):
                            # Escape single quotes
                            escaped_val = val.replace("'", "''")
                            values.append(f"'{escaped_val}'")
                        else:
                            values.append(str(val))
                    values_list.append(f"({', '.join(values)})")
                
                values_clause = ',\n'.join(values_list)
                
                insert_sql = f"""
                INSERT INTO {table_name} ({columns})
                VALUES {values_clause};
                """
                
                logger.info(f"Inserting batch {batch_num + 1}/{total_batches} ({len(batch_df)} records)")
                execute_redshift_statement(insert_sql)
            
            logger.info(f"Successfully loaded {record_count} records to '{table_name}'")
            metrics['total_records_written'] += record_count
            return
            
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(
                    f"Attempt {attempt + 1}/{retry_count} failed for table '{table_name}'. "
                    f"Retrying in {wait_time} seconds... Error: {str(e)}"
                )
                time.sleep(wait_time)
            else:
                error_msg = f"Failed to load data to Redshift Serverless table '{table_name}' after {retry_count} attempts: {str(e)}"
                logger.error(error_msg, exc_info=True)
                metrics['errors'].append({
                    'table': table_name,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                metrics['total_records_failed'] += record_count
                raise


def log_metrics_to_cloudwatch():
    """
    Log ETL metrics to CloudWatch
    
    Requirement 6.6: Track ingestion metrics including record count and success rate
    """
    try:
        # Calculate success rate
        success_rate = (
            metrics['total_records_written'] / metrics['total_records_read'] * 100
            if metrics['total_records_read'] > 0 else 0
        )
        
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
                'Value': success_rate,
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
    logger.info("Starting AWS Glue Python Shell ETL Job for Redshift Serverless")
    logger.info(f"Command line arguments: {sys.argv}")
    logger.info(f"S3 Bucket: {S3_BUCKET}")
    logger.info(f"S3 Prefix: {S3_PREFIX}")
    logger.info(f"Redshift Workgroup: {REDSHIFT_WORKGROUP}")
    logger.info(f"Redshift Database: {REDSHIFT_DATABASE}")
    logger.info(f"AWS Region: {AWS_REGION}")
    logger.info(f"Using Redshift Data API for serverless connectivity")
    logger.info("=" * 60)
    
    # Process each table
    for table_name in TABLES:
        logger.info(f"\nProcessing table: {table_name}")
        
        try:
            # Extract from S3
            df = extract_from_s3(table_name)
            
            if df is None:
                logger.warning(f"Skipping table '{table_name}' due to extraction failure")
                continue
            
            # Transform data (Requirement 6.2)
            transformed_df = transform_data(df, table_name)
            
            # Load to Redshift (Requirement 6.3)
            load_to_redshift(transformed_df, table_name)
            
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
    success_rate = (
        metrics['total_records_written'] / metrics['total_records_read'] * 100
        if metrics['total_records_read'] > 0 else 0
    )
    
    logger.info("\n" + "=" * 60)
    logger.info("ETL Job Complete")
    logger.info(f"Tables Processed: {metrics['tables_processed']}/{len(TABLES)}")
    logger.info(f"Total Records Read: {metrics['total_records_read']}")
    logger.info(f"Total Records Written: {metrics['total_records_written']}")
    logger.info(f"Total Records Failed: {metrics['total_records_failed']}")
    logger.info(f"Success Rate: {success_rate:.2f}%")
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
    
    logger.info("ETL job completed successfully")


if __name__ == '__main__':
    main()
