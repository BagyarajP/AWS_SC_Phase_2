#!/bin/bash

# Deployment script for get_historical_sales Lambda tool
# This script packages and deploys the Lambda function to AWS

set -e

FUNCTION_NAME="supply-chain-get-historical-sales"
REGION="us-east-1"
ROLE_ARN="arn:aws:iam::YOUR_ACCOUNT_ID:role/SupplyChainToolRole"

echo "Deploying get_historical_sales Lambda tool..."

# Create deployment package
echo "Creating deployment package..."
rm -f get_historical_sales.zip
zip get_historical_sales.zip get_historical_sales.py

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Function exists, updating code..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://get_historical_sales.zip \
        --region $REGION
    
    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables={REDSHIFT_WORKGROUP=supply-chain-workgroup,REDSHIFT_DATABASE=supply_chain}" \
        --timeout 60 \
        --memory-size 256 \
        --region $REGION
else
    echo "Function does not exist, creating..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler get_historical_sales.lambda_handler \
        --zip-file fileb://get_historical_sales.zip \
        --environment "Variables={REDSHIFT_WORKGROUP=supply-chain-workgroup,REDSHIFT_DATABASE=supply_chain}" \
        --timeout 60 \
        --memory-size 256 \
        --region $REGION
fi

echo "Deployment complete!"
echo "Function ARN: arn:aws:lambda:$REGION:YOUR_ACCOUNT_ID:function:$FUNCTION_NAME"

# Clean up
rm -f get_historical_sales.zip

echo ""
echo "Next steps:"
echo "1. Update ROLE_ARN in this script with your actual IAM role ARN"
echo "2. Add this Lambda function as an action group to the Forecasting Bedrock Agent"
echo "3. Test the function with: aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"product_id\":\"PROD-00001\"}' response.json"
