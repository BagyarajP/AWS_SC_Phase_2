# Lambda Tool: store_forecast

## Overview

The `store_forecast` Lambda tool stores demand forecast records into the Redshift Serverless `demand_forecast` table. It's designed to be called by the Forecasting Bedrock Agent after generating demand forecasts using the `calculate_forecast` tool.

## Requirements

- **Requirements**: 3.6
- **Task**: 4.3

## Functionality

This tool:
1. Accepts forecast data with predictions and confidence intervals
2. Generates unique forecast IDs for each record
3. Performs batch insert into Redshift Serverless via Data API
4. Returns confirmation with stored forecast IDs

## Input Parameters

The tool accepts the following parameters (from Bedrock Agent or direct invocation):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_id` | string | Yes | Product identifier (e.g., "PROD-00001") |
| `warehouse_id` | string | Yes | Warehouse identifier (e.g., "WH-SOUTH") |
| `forecast_data` | array | Yes | List of forecast records with dates and predictions |
| `horizon_days` | integer | Yes | Forecast horizon (7 or 30 days) |

### Forecast Data Structure

Each item in `forecast_data` should contain:

```json
{
  "forecast_date": "2024-01-15",
  "predicted_demand": 45.5,
  "confidence_80_lower": 38.2,
  "confidence_80_upper": 52.8,
  "confidence_95_lower": 34.1,
  "confidence_95_upper": 56.9
}
```

## Output

Returns a JSON response with:

```json
{
  "statusCode": 200,
  "body": {
    "product_id": "PROD-00001",
    "warehouse_id": "WH-SOUTH",
    "horizon_days": 7,
    "records_stored": 7,
    "forecast_ids": ["FCST-ABC123...", "FCST-DEF456...", ...],
    "stored_at": "2024-01-15T10:30:00",
    "message": "Successfully stored 7 forecast records"
  }
}
```

## Database Schema

Inserts into the `demand_forecast` table:

```sql
CREATE TABLE demand_forecast (
    forecast_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES product(product_id),
    warehouse_id VARCHAR(50) REFERENCES warehouse(warehouse_id),
    forecast_date DATE,
    forecast_horizon_days INTEGER,
    predicted_demand INTEGER,
    confidence_interval_lower INTEGER,
    confidence_interval_upper INTEGER,
    confidence_level DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Environment Variables

Required environment variables:

- `REDSHIFT_WORKGROUP`: Redshift Serverless workgroup name (e.g., "supply-chain-workgroup")
- `REDSHIFT_DATABASE`: Database name (e.g., "supply_chain")

## Error Handling

The tool handles the following error conditions:

1. **Missing Parameters**: Returns 500 error if required parameters are missing
2. **Environment Validation**: Returns 500 error if environment variables are not set
3. **Database Errors**: Returns 500 error if Redshift query fails
4. **Query Timeout**: Raises exception if query exceeds 60 seconds

## Usage Examples

### Direct Lambda Invocation

```python
import boto3
import json

lambda_client = boto3.client('lambda')

event = {
    'product_id': 'PROD-00001',
    'warehouse_id': 'WH-SOUTH',
    'forecast_data': [
        {
            'forecast_date': '2024-01-15',
            'predicted_demand': 45.5,
            'confidence_80_lower': 38.2,
            'confidence_80_upper': 52.8,
            'confidence_95_lower': 34.1,
            'confidence_95_upper': 56.9
        }
    ],
    'horizon_days': 7
}

response = lambda_client.invoke(
    FunctionName='store-forecast',
    InvocationType='RequestResponse',
    Payload=json.dumps(event)
)

result = json.loads(response['Payload'].read())
print(result)
```

### Bedrock Agent Invocation

The Bedrock Agent will call this tool automatically with the following action group configuration:

```json
{
  "actionGroupName": "ForecastingTools",
  "actionGroupExecutor": {
    "lambda": "arn:aws:lambda:us-east-1:ACCOUNT:function:store-forecast"
  },
  "apiSchema": {
    "payload": {
      "name": "store_forecast",
      "description": "Store forecast results in Redshift Serverless",
      "parameters": {
        "product_id": {"type": "string", "required": true},
        "warehouse_id": {"type": "string", "required": true},
        "forecast_data": {"type": "array", "required": true},
        "horizon_days": {"type": "integer", "required": true}
      }
    }
  }
}
```

## Testing

Run unit tests:

```bash
cd lambda/forecasting_agent/tools
python -m pytest test_store_forecast.py -v
```

Test coverage includes:
- Successful forecast storage
- Parameter validation
- Environment validation
- Bedrock Agent parameter format handling
- Empty forecast data handling
- Large forecast data (30-day horizon)
- Database error handling

## Deployment

### Package Dependencies

```bash
pip install -r requirements.txt -t package/
cp store_forecast.py package/
cd package
zip -r ../store_forecast.zip .
```

### Deploy to AWS Lambda

```bash
aws lambda create-function \
  --function-name store-forecast \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT:role/SupplyChainToolRole \
  --handler store_forecast.lambda_handler \
  --zip-file fileb://store_forecast.zip \
  --timeout 60 \
  --memory-size 256 \
  --environment Variables="{REDSHIFT_WORKGROUP=supply-chain-workgroup,REDSHIFT_DATABASE=supply_chain}" \
  --region us-east-1
```

## IAM Permissions

The Lambda execution role requires:

```json
{
  "Version": "2012-10-17",
  "Statement": [
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
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Performance Considerations

- **Batch Insert**: Uses single SQL statement for multiple records (efficient)
- **Timeout**: 60-second timeout for query completion
- **Memory**: 256 MB memory allocation (sufficient for typical workloads)
- **Concurrency**: Supports concurrent invocations (serverless scaling)

## Monitoring

Monitor the tool using CloudWatch:

- **Logs**: `/aws/lambda/store-forecast`
- **Metrics**: Invocations, Duration, Errors, Throttles
- **Alarms**: Set alarms for error rate > 5%

## Related Tools

- `calculate_forecast`: Generates forecast data that this tool stores
- `get_historical_sales`: Retrieves historical data for forecasting
- `calculate_accuracy`: Calculates accuracy of stored forecasts
