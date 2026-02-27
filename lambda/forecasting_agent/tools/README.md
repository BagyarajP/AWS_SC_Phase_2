# Forecasting Agent Lambda Tools

This directory contains Lambda tools that are invoked by the Forecasting Bedrock Agent as part of the demand forecasting workflow.

## Tools

### get_historical_sales.py

**Purpose**: Retrieve historical sales data for time series analysis

**Requirements**: 3.3, 8.4

**Input Parameters**:
- `product_id` (required): Product identifier (e.g., "PROD-00001")
- `months_back` (optional): Number of months of historical data (default: 12)

**Output**:
```json
{
  "product_id": "PROD-00001",
  "months_back": 12,
  "data_points": 365,
  "time_series": [
    {
      "order_date": "2023-01-01",
      "quantity": 45
    },
    ...
  ],
  "summary": {
    "total_quantity": 16425,
    "average_daily_quantity": 45.0,
    "date_range": {
      "start": "2023-01-01",
      "end": "2023-12-31"
    }
  }
}
```

**Environment Variables**:
- `REDSHIFT_WORKGROUP`: Redshift Serverless workgroup name (e.g., "supply-chain-workgroup")
- `REDSHIFT_DATABASE`: Database name (e.g., "supply_chain")

**IAM Permissions Required**:
- `redshift-data:ExecuteStatement`
- `redshift-data:DescribeStatement`
- `redshift-data:GetStatementResult`
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

**Usage by Bedrock Agent**:
The Forecasting Bedrock Agent invokes this tool to retrieve historical sales data before generating forecasts. The agent passes the product_id and receives time series data that it uses for statistical modeling.

**Error Handling**:
- Returns 200 with empty time_series if no data found
- Returns 500 with error details if query fails
- Logs all errors to CloudWatch
- Implements query timeout (60 seconds max)

**Testing**:
```bash
# Set environment variables
export REDSHIFT_WORKGROUP=supply-chain-workgroup
export REDSHIFT_DATABASE=supply_chain

# Run local test
python get_historical_sales.py
```

## Deployment

These tools are deployed as separate Lambda functions in us-east-1 and configured as action groups for the Forecasting Bedrock Agent.

**Deployment Steps**:
1. Package each tool with dependencies (boto3 is included in Lambda runtime)
2. Create Lambda function in AWS Console
3. Configure environment variables
4. Attach IAM role with Redshift Data API permissions
5. Add as action group to Forecasting Bedrock Agent

## Architecture

```
Forecasting Bedrock Agent (Claude 3.5 Sonnet)
    |
    ├─> get_historical_sales (Lambda Tool)
    |       └─> Redshift Serverless (Data API)
    |
    ├─> calculate_forecast (Lambda Tool)
    |       └─> Statistical models (Holt-Winters, ARIMA)
    |
    ├─> store_forecast (Lambda Tool)
    |       └─> Redshift Serverless (Data API)
    |
    └─> calculate_accuracy (Lambda Tool)
            └─> Redshift Serverless (Data API)
```

## Notes

- All tools use Redshift Data API for serverless connectivity (no connection pooling needed)
- Tools are stateless and can be invoked concurrently
- CloudWatch logging is enabled for all executions
- Error handling follows graceful degradation pattern
- Tools return JSON responses compatible with Bedrock Agent expectations
