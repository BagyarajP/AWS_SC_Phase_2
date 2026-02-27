# Lambda Functions - Supply Chain AI Platform

This directory contains all AWS Lambda functions for the autonomous supply chain optimization platform.

## Overview

The platform uses three autonomous agent Lambda functions:

1. **Forecasting Agent** - Generates demand forecasts for all SKUs
2. **Procurement Agent** - Creates purchase orders based on inventory levels (to be implemented)
3. **Inventory Agent** - Recommends stock transfers between warehouses (to be implemented)

## Architecture

All Lambda functions follow a consistent architecture:

- **Runtime**: Python 3.9
- **Database**: Amazon Redshift (PostgreSQL-compatible)
- **Trigger**: EventBridge scheduled rules (daily execution)
- **Logging**: CloudWatch Logs
- **IAM**: Least-privilege roles with Redshift and CloudWatch permissions

### Common Patterns

Each Lambda function implements:

1. **Retry Logic**: Exponential backoff for Redshift connections (3 attempts)
2. **Error Handling**: Comprehensive try-catch with CloudWatch logging
3. **Environment Variables**: Configuration via Lambda environment
4. **Validation**: Input validation and data quality checks
5. **Audit Logging**: All decisions logged to Redshift audit_log table

## Directory Structure

```
lambda/
├── README.md                          # This file
├── forecasting_agent/                 # Forecasting Agent Lambda
│   ├── lambda_function.py            # Main handler
│   ├── requirements.txt              # Python dependencies
│   ├── config.json                   # Configuration reference
│   ├── deploy.sh                     # Deployment script
│   ├── test_connection.py            # Connection test script
│   └── README.md                     # Detailed documentation
├── procurement_agent/                 # Procurement Agent (to be implemented)
│   └── ...
└── inventory_agent/                   # Inventory Agent (to be implemented)
    └── ...
```

## Implementation Status

### Completed

- ✅ **Task 4.1**: Forecasting Agent structure and Redshift connection
  - Lambda handler function
  - Connection retry logic
  - Environment variable configuration
  - Error handling and logging
  - Product retrieval from database

### In Progress

- 🔄 **Task 4.2**: Forecasting Agent time series logic (next)

### Planned

- ⏳ **Task 5**: Procurement Agent implementation
- ⏳ **Task 6**: Inventory Agent implementation

## Common Environment Variables

All Lambda functions require these Redshift connection variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `REDSHIFT_HOST` | Yes | Redshift cluster endpoint |
| `REDSHIFT_PORT` | No | Port (default: 5439) |
| `REDSHIFT_DATABASE` | Yes | Database name |
| `REDSHIFT_USER` | Yes | Database user |
| `REDSHIFT_PASSWORD` | Yes | Database password |

## IAM Permissions

All Lambda functions require an IAM execution role with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement"
      ],
      "Resource": "arn:aws:redshift:eu-west-2:*:cluster:supply-chain-cluster"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:eu-west-2:*:log-group:/aws/lambda/supply-chain-*"
    }
  ]
}
```

### Creating the IAM Role

Via AWS Console:
1. Go to IAM → Roles → Create role
2. Select "Lambda" as trusted entity
3. Create custom policy with above permissions
4. Name the role: `SupplyChainAgentRole`

Via AWS CLI:
```bash
# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name SupplyChainAgentRole \
  --assume-role-policy-document file://trust-policy.json

# Create and attach policy
aws iam put-role-policy \
  --role-name SupplyChainAgentRole \
  --policy-name SupplyChainAgentPolicy \
  --policy-document file://agent-policy.json
```

## Deployment

Each Lambda function has its own deployment script. General process:

1. **Install dependencies**:
   ```bash
   cd lambda/[agent_name]
   pip install -r requirements.txt -t package/
   ```

2. **Package function**:
   ```bash
   cd package
   zip -r ../function.zip .
   cd ..
   zip -g function.zip lambda_function.py
   ```

3. **Deploy to AWS**:
   ```bash
   ./deploy.sh
   ```

See individual agent README files for detailed deployment instructions.

## Testing

### Local Testing

Each Lambda function includes a test script for local execution:

```bash
# Set environment variables
export REDSHIFT_HOST=your-cluster.redshift.amazonaws.com
export REDSHIFT_DATABASE=supply_chain
export REDSHIFT_USER=admin
export REDSHIFT_PASSWORD=YourPassword

# Run test
cd lambda/forecasting_agent
python test_connection.py
```

### Unit Testing

Unit tests will be added in subsequent tasks using pytest:

```bash
cd lambda/forecasting_agent
pytest tests/
```

### Property-Based Testing

Property tests verify universal correctness properties using Hypothesis:

```bash
cd lambda/forecasting_agent
pytest tests/test_properties.py
```

## Monitoring

### CloudWatch Logs

Each Lambda function logs to its own CloudWatch Logs group:
- `/aws/lambda/supply-chain-forecasting-agent`
- `/aws/lambda/supply-chain-procurement-agent`
- `/aws/lambda/supply-chain-inventory-agent`

View logs:
```bash
aws logs tail /aws/lambda/supply-chain-forecasting-agent --follow
```

### CloudWatch Metrics

Monitor these Lambda metrics:
- **Invocations**: Should match schedule (1/day for each agent)
- **Duration**: Track execution time trends
- **Errors**: Should be 0 for healthy operation
- **Throttles**: Should be 0

### CloudWatch Alarms

Recommended alarms:
- Lambda errors > 0
- Lambda duration > 10 minutes
- Lambda throttles > 0

## EventBridge Scheduling

Each agent runs on a daily schedule:

| Agent | Schedule | Cron Expression |
|-------|----------|-----------------|
| Forecasting | 1:00 AM UTC | `cron(0 1 * * ? *)` |
| Procurement | 2:00 AM UTC | `cron(0 2 * * ? *)` |
| Inventory | 3:00 AM UTC | `cron(0 3 * * ? *)` |

Create EventBridge rules:
```bash
# Forecasting Agent
aws events put-rule \
  --name supply-chain-forecasting-daily \
  --schedule-expression "cron(0 1 * * ? *)" \
  --region eu-west-2

aws events put-targets \
  --rule supply-chain-forecasting-daily \
  --targets "Id"="1","Arn"="arn:aws:lambda:eu-west-2:ACCOUNT_ID:function:supply-chain-forecasting-agent"
```

## Troubleshooting

### Connection Errors

If Lambda cannot connect to Redshift:
1. Check security group allows Lambda access
2. Verify Redshift cluster is in same VPC or publicly accessible
3. Check environment variables are correct
4. Review CloudWatch Logs for detailed error messages

### Timeout Errors

If Lambda times out:
1. Increase timeout (max 15 minutes)
2. Increase memory allocation (more memory = more CPU)
3. Optimize queries (add indexes, reduce data volume)
4. Consider batch processing for large datasets

### Permission Errors

If Lambda gets permission denied:
1. Verify IAM role has required permissions
2. Check Redshift user has database permissions
3. Ensure Lambda execution role is attached to function

## Best Practices

1. **Secrets Management**: Use AWS Secrets Manager for database passwords
2. **VPC Configuration**: Deploy Lambda in VPC for private Redshift access
3. **Error Handling**: Always log errors to CloudWatch
4. **Idempotency**: Design functions to be safely re-runnable
5. **Monitoring**: Set up CloudWatch alarms for failures
6. **Testing**: Test locally before deploying to AWS
7. **Versioning**: Use Lambda versions and aliases for production

## Related Documentation

- Design Document: `.kiro/specs/supply-chain-ai-platform/design.md`
- Requirements: `.kiro/specs/supply-chain-ai-platform/requirements.md`
- Task List: `.kiro/specs/supply-chain-ai-platform/tasks.md`
- Database Schema: `database/schema.sql`
- Glue ETL: `glue/README.md`

## Support

For issues or questions:
1. Check individual agent README files
2. Review CloudWatch Logs for error details
3. Consult design and requirements documents
4. Check AWS Lambda documentation: https://docs.aws.amazon.com/lambda/
