# Calculate Forecast Lambda Tool

## Overview

The `calculate_forecast` Lambda tool generates demand forecasts using an ensemble of Holt-Winters exponential smoothing and ARIMA models. It's designed to be invoked by the Forecasting Bedrock Agent as part of the supply chain optimization platform.

## Features

- **Dual Model Ensemble**: Combines Holt-Winters and ARIMA forecasts for improved accuracy
- **Confidence Intervals**: Provides 80% and 95% confidence intervals for all predictions
- **Multiple Horizons**: Supports both 7-day and 30-day forecast horizons
- **Seasonality Handling**: Holt-Winters model captures weekly seasonal patterns
- **Trend Detection**: Both models handle trending time series data
- **Non-negative Forecasts**: Ensures all predictions are >= 0 (appropriate for demand forecasting)

## Requirements Addressed

- **3.3**: Uses historical sales data and seasonality for forecasting
- **3.4**: Provides confidence intervals at 80% and 95% levels
- **3.5**: Supports 7-day and 30-day forecast horizons

## Input Parameters

The Lambda function accepts the following parameters:

```json
{
  "product_id": "PROD-00001",           // Required: Product identifier
  "historical_data": [                   // Required: Time series data
    {
      "order_date": "2023-01-01",
      "quantity": 50
    },
    ...
  ],
  "horizon_days": 7                      // Required: 7 or 30
}
```

### Parameter Details

- **product_id** (string, required): Unique product identifier
- **historical_data** (array, required): 
  - Minimum 14 data points required
  - Each point must have `order_date` (YYYY-MM-DD) and `quantity` (number)
  - More data points (90+ days) improve forecast accuracy
- **horizon_days** (integer, required): Must be either 7 or 30

## Output Format

```json
{
  "statusCode": 200,
  "body": {
    "product_id": "PROD-00001",
    "horizon_days": 7,
    "forecast_generated_at": "2024-01-15T10:30:00",
    "forecast_data": [
      {
        "forecast_date": "2024-01-16",
        "predicted_demand": 54.23,
        "confidence_80_lower": 48.15,
        "confidence_80_upper": 60.31,
        "confidence_95_lower": 45.20,
        "confidence_95_upper": 63.26,
        "model_components": {
          "holt_winters": 55.10,
          "arima": 53.36
        }
      },
      ...
    ],
    "summary": {
      "total_predicted_demand": 379.61,
      "average_daily_demand": 54.23,
      "historical_average": 52.10
    }
  }
}
```

## Forecasting Models

### Holt-Winters Exponential Smoothing

The Holt-Winters model uses triple exponential smoothing with:
- **Level smoothing (α = 0.3)**: Captures the baseline demand level
- **Trend smoothing (β = 0.1)**: Captures upward/downward trends
- **Seasonal smoothing (γ = 0.2)**: Captures weekly seasonality (7-day cycle)

This model is particularly effective for:
- Data with clear seasonal patterns
- Trending time series
- Short to medium-term forecasts

### ARIMA (Simplified)

The ARIMA implementation uses a simplified ARIMA(1,1,1) approach:
- **First-order differencing**: Makes the series stationary
- **AR(1) component**: Captures autocorrelation in the data
- **MA(1) component**: Smooths random fluctuations

This model is effective for:
- Stationary or near-stationary series
- Data with autocorrelation
- Complementing Holt-Winters predictions

### Ensemble Method

The final forecast is the **simple average** of both models:
```
Ensemble Forecast = (Holt-Winters + ARIMA) / 2
```

This approach:
- Reduces individual model bias
- Improves overall forecast accuracy
- Provides more robust predictions

## Confidence Intervals

Confidence intervals are calculated using historical forecast error variance:

- **80% CI**: ±1.28 standard deviations
- **95% CI**: ±1.96 standard deviations

The intervals **widen with forecast horizon** to reflect increasing uncertainty:
```
Margin = Z-score × Historical_StdDev × sqrt(1 + horizon_index × 0.1)
```

## Usage Examples

### Direct Lambda Invocation

```python
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

payload = {
    'product_id': 'PROD-00001',
    'historical_data': [
        {'order_date': '2023-01-01', 'quantity': 50},
        {'order_date': '2023-01-02', 'quantity': 52},
        # ... more data points
    ],
    'horizon_days': 7
}

response = lambda_client.invoke(
    FunctionName='calculate-forecast',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

### Bedrock Agent Invocation

The Bedrock Forecasting Agent will invoke this tool automatically:

```
Agent: "I need to generate a 7-day forecast for PROD-00001"
→ Agent calls get_historical_sales to retrieve data
→ Agent calls calculate_forecast with historical data
→ Agent interprets results and generates natural language explanation
```

## Testing

Run the comprehensive test suite:

```bash
cd lambda/forecasting_agent/tools
python -m pytest test_calculate_forecast.py -v
```

### Test Coverage

- ✅ Parameter validation (missing/invalid parameters)
- ✅ Both 7-day and 30-day horizons
- ✅ Bedrock Agent parameter format
- ✅ Holt-Winters model accuracy
- ✅ ARIMA model accuracy
- ✅ Ensemble forecasting logic
- ✅ Confidence interval calculation
- ✅ Confidence interval ordering (95% > 80%)
- ✅ Non-negative forecast constraint
- ✅ Edge cases (zero values, high variance)
- ✅ Date sequencing

## Performance Considerations

- **Execution Time**: ~100-500ms for typical forecasts
- **Memory**: 256 MB Lambda memory recommended
- **Data Requirements**: Minimum 14 days, optimal 90+ days
- **Timeout**: 30 seconds recommended

## Error Handling

The function handles various error conditions:

| Error | Status Code | Message |
|-------|-------------|---------|
| Missing product_id | 500 | "Missing required parameter: product_id" |
| Missing historical_data | 500 | "Missing required parameter: historical_data" |
| Invalid horizon_days | 500 | "Invalid horizon_days: X. Must be 7 or 30" |
| Insufficient data | 500 | "Insufficient historical data. Need at least 14 days" |
| Model failure | 500 | Falls back to simple moving average |

## Deployment

### Lambda Configuration

```yaml
Function Name: calculate-forecast
Runtime: Python 3.9+
Handler: calculate_forecast.lambda_handler
Memory: 256 MB
Timeout: 30 seconds
Environment Variables: None required
```

### Dependencies

Package the following with your Lambda deployment:
- `numpy>=1.24.0`
- `boto3>=1.26.0` (included in Lambda runtime)

### Deployment Package

```bash
# Create deployment package
cd lambda/forecasting_agent/tools
pip install -r requirements.txt -t package/
cp calculate_forecast.py package/
cd package
zip -r ../calculate_forecast.zip .
```

## Integration with Bedrock Agent

This tool is configured as an action group in the Forecasting Bedrock Agent:

**Action Group Configuration:**
```json
{
  "actionGroupName": "ForecastingTools",
  "description": "Tools for demand forecasting",
  "actionGroupExecutor": {
    "lambda": "arn:aws:lambda:us-east-1:ACCOUNT:function:calculate-forecast"
  },
  "apiSchema": {
    "payload": {
      "name": "calculate_forecast",
      "description": "Generate demand forecasts using Holt-Winters and ARIMA ensemble",
      "parameters": {
        "product_id": {
          "type": "string",
          "description": "Product identifier",
          "required": true
        },
        "historical_data": {
          "type": "array",
          "description": "Historical sales time series data",
          "required": true
        },
        "horizon_days": {
          "type": "integer",
          "description": "Forecast horizon (7 or 30 days)",
          "required": true
        }
      }
    }
  }
}
```

## Future Enhancements

Potential improvements for future iterations:
- Add support for external factors (promotions, holidays)
- Implement automatic model selection based on data characteristics
- Add support for multiple seasonality periods
- Implement Prophet or other advanced models
- Add forecast accuracy metrics (MAPE, RMSE)
- Support for probabilistic forecasting

## References

- Holt-Winters: [Exponential Smoothing](https://otexts.com/fpp2/holt-winters.html)
- ARIMA: [Time Series Analysis](https://otexts.com/fpp2/arima.html)
- AWS Lambda: [Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- AWS Bedrock: [Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
