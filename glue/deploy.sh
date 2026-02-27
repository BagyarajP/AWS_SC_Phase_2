#!/bin/bash

# AWS Glue ETL Job Deployment Script
# This script uploads the Glue job script to S3 and creates/updates the Glue job

set -e

# Configuration
SCRIPT_NAME="etl_job.py"
JOB_NAME="supply-chain-etl-job"
GLUE_VERSION="4.0"
PYTHON_VERSION="3"
MAX_CAPACITY="2"
TIMEOUT="60"

# Required parameters (set via environment variables or command line)
S3_SCRIPTS_BUCKET="${S3_SCRIPTS_BUCKET:-}"
S3_DATA_BUCKET="${S3_DATA_BUCKET:-}"
S3_DATA_PREFIX="${S3_DATA_PREFIX:-synthetic_data/}"
REDSHIFT_CONNECTION="${REDSHIFT_CONNECTION:-supply-chain-redshift}"
REDSHIFT_DATABASE="${REDSHIFT_DATABASE:-supply_chain}"
IAM_ROLE_ARN="${IAM_ROLE_ARN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check required parameters
check_parameters() {
    print_info "Checking required parameters..."
    
    local missing_params=0
    
    if [ -z "$S3_SCRIPTS_BUCKET" ]; then
        print_error "S3_SCRIPTS_BUCKET is not set"
        missing_params=1
    fi
    
    if [ -z "$S3_DATA_BUCKET" ]; then
        print_error "S3_DATA_BUCKET is not set"
        missing_params=1
    fi
    
    if [ -z "$IAM_ROLE_ARN" ]; then
        print_error "IAM_ROLE_ARN is not set"
        missing_params=1
    fi
    
    if [ $missing_params -eq 1 ]; then
        print_error "Missing required parameters. Please set:"
        echo "  export S3_SCRIPTS_BUCKET=your-glue-scripts-bucket"
        echo "  export S3_DATA_BUCKET=your-data-bucket"
        echo "  export IAM_ROLE_ARN=arn:aws:iam::ACCOUNT:role/GlueRole"
        exit 1
    fi
    
    print_info "All required parameters are set"
}

# Upload script to S3
upload_script() {
    print_info "Uploading Glue script to S3..."
    
    local s3_path="s3://${S3_SCRIPTS_BUCKET}/supply-chain-ai/${SCRIPT_NAME}"
    
    aws s3 cp "$SCRIPT_NAME" "$s3_path" \
        --sse AES256
    
    if [ $? -eq 0 ]; then
        print_info "Script uploaded successfully to: $s3_path"
    else
        print_error "Failed to upload script"
        exit 1
    fi
}

# Create or update Glue job
create_or_update_job() {
    print_info "Creating/updating Glue job..."
    
    local script_location="s3://${S3_SCRIPTS_BUCKET}/supply-chain-ai/${SCRIPT_NAME}"
    local temp_dir="s3://${S3_DATA_BUCKET}/temp/"
    
    # Check if job exists
    if aws glue get-job --job-name "$JOB_NAME" &>/dev/null; then
        print_info "Job exists, updating..."
        
        aws glue update-job \
            --job-name "$JOB_NAME" \
            --job-update "{
                \"Role\": \"${IAM_ROLE_ARN}\",
                \"Command\": {
                    \"Name\": \"glueetl\",
                    \"ScriptLocation\": \"${script_location}\",
                    \"PythonVersion\": \"${PYTHON_VERSION}\"
                },
                \"DefaultArguments\": {
                    \"--S3_BUCKET\": \"${S3_DATA_BUCKET}\",
                    \"--S3_PREFIX\": \"${S3_DATA_PREFIX}\",
                    \"--REDSHIFT_CONNECTION\": \"${REDSHIFT_CONNECTION}\",
                    \"--REDSHIFT_DATABASE\": \"${REDSHIFT_DATABASE}\",
                    \"--REDSHIFT_TEMP_DIR\": \"${temp_dir}\",
                    \"--enable-metrics\": \"true\",
                    \"--enable-continuous-cloudwatch-log\": \"true\",
                    \"--enable-spark-ui\": \"true\",
                    \"--spark-event-logs-path\": \"s3://${S3_DATA_BUCKET}/spark-logs/\"
                },
                \"MaxCapacity\": ${MAX_CAPACITY},
                \"Timeout\": ${TIMEOUT},
                \"GlueVersion\": \"${GLUE_VERSION}\"
            }"
        
        print_info "Job updated successfully"
    else
        print_info "Job does not exist, creating..."
        
        aws glue create-job \
            --name "$JOB_NAME" \
            --role "$IAM_ROLE_ARN" \
            --command "Name=glueetl,ScriptLocation=${script_location},PythonVersion=${PYTHON_VERSION}" \
            --default-arguments "{
                \"--S3_BUCKET\": \"${S3_DATA_BUCKET}\",
                \"--S3_PREFIX\": \"${S3_DATA_PREFIX}\",
                \"--REDSHIFT_CONNECTION\": \"${REDSHIFT_CONNECTION}\",
                \"--REDSHIFT_DATABASE\": \"${REDSHIFT_DATABASE}\",
                \"--REDSHIFT_TEMP_DIR\": \"${temp_dir}\",
                \"--enable-metrics\": \"true\",
                \"--enable-continuous-cloudwatch-log\": \"true\",
                \"--enable-spark-ui\": \"true\",
                \"--spark-event-logs-path\": \"s3://${S3_DATA_BUCKET}/spark-logs/\"
            }" \
            --max-capacity "$MAX_CAPACITY" \
            --timeout "$TIMEOUT" \
            --glue-version "$GLUE_VERSION"
        
        print_info "Job created successfully"
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "AWS Glue ETL Job Deployment"
    echo "=========================================="
    echo ""
    
    check_parameters
    upload_script
    create_or_update_job
    
    echo ""
    echo "=========================================="
    print_info "Deployment complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Verify Glue connection '${REDSHIFT_CONNECTION}' is configured"
    echo "  2. Ensure data files are in s3://${S3_DATA_BUCKET}/${S3_DATA_PREFIX}"
    echo "  3. Run the job:"
    echo "     aws glue start-job-run --job-name ${JOB_NAME}"
    echo ""
}

main
