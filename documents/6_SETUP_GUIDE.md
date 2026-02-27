# Supply Chain AI Platform - Setup Guide

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Target Audience**: Developers, QA Engineers, Technical Teams

---

## Table of Contents

1. [Overview](#overview)
2. [Local Development Setup](#local-development-setup)
3. [Testing Environment](#testing-environment)
4. [Running Tests](#running-tests)
5. [Development Workflow](#development-workflow)
6. [Debugging Guide](#debugging-guide)

---

## Overview

This guide helps developers set up a local development environment for the Supply Chain AI Platform. It covers installation, configuration, testing, and debugging procedures.

### What You'll Set Up

- Python development environment
- AWS CLI and credentials
- Local testing tools
- Property-based testing framework
- Database connection tools
- Code quality tools

---

## Local Development Setup

### Prerequisites

#### System Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux
- **RAM**: Minimum 8 GB (16 GB recommended)
- **Disk Space**: 10 GB free space
- **Internet**: Stable connection for AWS services

#### Required Software

```bash
# Python 3.9+
python --version  # Should show 3.9.x or higher

# pip package manager
pip --version

# Git
git --version

# AWS CLI v2
aws --version  # Should show aws-cli/2.x

# PostgreSQL client (for Redshift)
psql --version

# jq (JSON processor)
jq --version
```

### Installation Steps

#### Step 1: Install Python and Dependencies

**Windows**:
```powershell
# Download Python 3.9+ from python.org
# Install with "Add to PATH" option checked

# Verify installation
python --version
pip --version
```

**macOS**:
```bash
# Using Homebrew
brew install python@3.9

# Verify installation
python3 --version
pip3 --version
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install python3.9 python3-pip

# Verify installation
python3 --version
pip3 --version
```

#### Step 2: Install AWS CLI

**Windows**:
```powershell
# Download MSI installer from aws.amazon.com/cli
# Run installer and follow prompts

# Verify installation
aws --version
```

**macOS**:
```bash
# Using Homebrew
brew install awscli

# Verify installation
aws --version
```

**Linux**:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

#### Step 3: Install PostgreSQL Client

**Windows**:
```powershell
# Download from postgresql.org
# Install PostgreSQL (includes psql client)
```

**macOS**:
```bash
brew install postgresql
```

**Linux**:
```bash
sudo apt install postgresql-client
```

#### Step 4: Install Additional Tools

```bash
# jq (JSON processor)
# Windows: choco install jq
# macOS: brew install jq
# Linux: sudo apt install jq

# Git (if not already installed)
# Windows: Download from git-scm.com
# macOS: brew install git
# Linux: sudo apt install git
```

### Project Setup

#### Step 1: Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd supply-chain-ai-platform

# Verify structure
ls -la
```

#### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Verify activation (should show (venv) in prompt)
which python
```

#### Step 3: Install Python Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov hypothesis boto3 pandas numpy statsmodels

# Verify installations
pip list
```

#### Step 4: Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Enter when prompted:
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

#### Step 5: Set Environment Variables

Create `.env` file in project root:

```bash
# .env file
AWS_REGION=us-east-1
REDSHIFT_WORKGROUP=supply-chain-workgroup
REDSHIFT_DATABASE=supply_chain
S3_BUCKET=supply-chain-data-<account-id>

# Bedrock Agent IDs (after deployment)
FORECASTING_AGENT_ID=<agent-id>
PROCUREMENT_AGENT_ID=<agent-id>
INVENTORY_AGENT_ID=<agent-id>

# Development settings
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

Load environment variables:

```bash
# Windows (PowerShell)
Get-Content .env | ForEach-Object {
    $name, $value = $_.split('=')
    Set-Content env:\$name $value
}

# macOS/Linux
export $(cat .env | xargs)
```

---

## Testing Environment

### Local Testing Setup

#### Step 1: Install Testing Framework

```bash
# Install pytest and plugins
pip install pytest pytest-cov pytest-mock hypothesis

# Verify installation
pytest --version
```

#### Step 2: Configure pytest

Create `pytest.ini` in project root:

```ini
[pytest]
testpaths = glue lambda
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    property: Property-based tests
    slow: Slow-running tests
```

#### Step 3: Set Up Test Database Connection

```bash
# Test Redshift connection
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "SELECT 1"

# Get statement result
aws redshift-data get-statement-result --id <statement-id>
```

### Mock Data Setup

#### Generate Test Data

```bash
# Generate synthetic data for testing
cd scripts
python generate_synthetic_data.py --output-dir ../test_data --size small

# Verify generated files
ls -la ../test_data/
```

---

## Running Tests

### Unit Tests

#### Run All Unit Tests

```bash
# Run all unit tests
pytest -m unit

# Run with coverage
pytest -m unit --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

#### Run Specific Test Files

```bash
# Test Glue ETL
cd glue
pytest test_etl_properties.py -v

# Test Forecasting Agent tools
cd lambda/forecasting_agent/tools
pytest test_get_historical_sales.py -v
pytest test_calculate_forecast.py -v

# Test Procurement Agent tools
cd ../../procurement_agent/tools
pytest test_get_inventory_levels.py -v
pytest test_create_purchase_order.py -v
```

### Property-Based Tests

#### Understanding Property-Based Testing

Property-based tests use the Hypothesis framework to generate hundreds of test cases automatically:

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=1000))
def test_forecast_always_positive(quantity):
    """Property: Forecasts should always be non-negative"""
    forecast = calculate_forecast(quantity)
    assert forecast >= 0
```

#### Run Property Tests

```bash
# Run all property tests
pytest -m property -v --hypothesis-show-statistics

# Run with specific seed for reproducibility
pytest -m property --hypothesis-seed=12345

# Run with more examples
pytest -m property --hypothesis-max-examples=1000
```

#### Property Test Examples

**Glue ETL Properties**:
```bash
cd glue

# Property 23: Data persistence
pytest test_etl_persistence_pure.py -v

# Property 24: Error handling
pytest test_etl_error_handling_pure.py -v

# Property 25: Metrics tracking
pytest test_etl_metrics_tracking_pure.py -v
```

**Forecasting Agent Properties**:
```bash
cd lambda/forecasting_agent

# Property 8: Forecast completeness
pytest test_property_8_forecast_completeness.py -v

# Property 9: Historical data requirements
pytest test_property_9_historical_data.py -v

# Property 10: Confidence intervals
pytest test_property_10_confidence_intervals.py -v
```

**Procurement Agent Properties**:
```bash
cd lambda/procurement_agent

# Property 1: EOQ calculation
pytest test_property_1_eoq_calculation.py -v

# Property 2: Supplier selection
pytest test_property_2_supplier_selection.py -v

# Property 6: Approval routing
pytest test_property_6_approval_routing.py -v
```

### Integration Tests

#### Run Integration Tests

```bash
# Run all integration tests (requires AWS access)
pytest -m integration -v

# Run specific integration test
pytest tests/integration/test_end_to_end_workflow.py -v
```

#### Integration Test Checklist

Before running integration tests:
- [ ] AWS credentials configured
- [ ] Redshift Serverless deployed
- [ ] Lambda functions deployed
- [ ] Bedrock Agents created
- [ ] Test data loaded

### Test Reports

#### Generate Test Report

```bash
# Run tests with JUnit XML report
pytest --junitxml=test-results.xml

# Run tests with HTML report
pytest --html=test-report.html --self-contained-html

# Run tests with coverage
pytest --cov=. --cov-report=html --cov-report=term
```

---

## Development Workflow

### Daily Development Cycle

#### 1. Start Development Session

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Pull latest changes
git pull origin main

# Install any new dependencies
pip install -r requirements.txt
```

#### 2. Make Code Changes

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes to code
# Edit files in your IDE
```

#### 3. Run Tests Locally

```bash
# Run unit tests for changed files
pytest path/to/test_file.py -v

# Run all tests
pytest -v

# Check code coverage
pytest --cov=. --cov-report=term-missing
```

#### 4. Code Quality Checks

```bash
# Format code with black
pip install black
black .

# Lint code with flake8
pip install flake8
flake8 .

# Type checking with mypy
pip install mypy
mypy .
```

#### 5. Commit and Push

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add new forecasting algorithm"

# Push to remote
git push origin feature/your-feature-name
```

### Testing New Lambda Functions

#### Local Lambda Testing

```bash
# Test Lambda function locally
cd lambda/forecasting_agent/tools/get_historical_sales

# Create test event
cat > test_event.json << EOF
{
  "product_id": "PROD001",
  "months_back": 12
}
EOF

# Run function locally
python -c "
import lambda_function
import json

with open('test_event.json') as f:
    event = json.load(f)

result = lambda_function.lambda_handler(event, None)
print(json.dumps(result, indent=2))
"
```

#### Deploy and Test on AWS

```bash
# Package function
zip -r function.zip .

# Update Lambda function
aws lambda update-function-code \
  --function-name supply-chain-forecasting-get-historical-sales \
  --zip-file fileb://function.zip

# Invoke function
aws lambda invoke \
  --function-name supply-chain-forecasting-get-historical-sales \
  --payload file://test_event.json \
  response.json

# View response
cat response.json | jq
```

### Testing Bedrock Agents

#### Invoke Agent Locally

```bash
# Create test script
cat > test_agent.py << 'EOF'
import boto3
import json

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock_agent_runtime.invoke_agent(
    agentId='<agent-id>',
    agentAliasId='PROD',
    sessionId='test-session',
    inputText='Generate forecasts for all products'
)

# Parse streaming response
for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        print(chunk['bytes'].decode('utf-8'))
EOF

python test_agent.py
```

---

## Debugging Guide

### Common Issues and Solutions

#### Issue 1: Import Errors

**Problem**: `ModuleNotFoundError: No module named 'boto3'`

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install missing dependencies
pip install boto3

# Verify installation
python -c "import boto3; print(boto3.__version__)"
```

#### Issue 2: AWS Credentials Not Found

**Problem**: `NoCredentialsError: Unable to locate credentials`

**Solution**:
```bash
# Configure AWS credentials
aws configure

# Verify credentials
aws sts get-caller-identity

# Check credentials file
cat ~/.aws/credentials
```

#### Issue 3: Redshift Connection Timeout

**Problem**: Redshift Data API queries timing out

**Solution**:
```bash
# Check Redshift workgroup status
aws redshift-serverless get-workgroup \
  --workgroup-name supply-chain-workgroup

# Verify IAM permissions
aws iam get-role-policy \
  --role-name SupplyChainToolRole \
  --policy-name RedshiftDataAPIAccess

# Test simple query
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "SELECT 1"
```

#### Issue 4: Property Test Failures

**Problem**: Property tests failing with counterexamples

**Solution**:
```bash
# Run test with specific seed to reproduce
pytest test_property.py --hypothesis-seed=<seed-from-failure>

# Increase verbosity
pytest test_property.py -vv --hypothesis-verbosity=verbose

# Debug specific counterexample
pytest test_property.py --pdb
```

### Debugging Tools

#### Python Debugger (pdb)

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

**Common pdb commands**:
- `n` - Next line
- `s` - Step into function
- `c` - Continue execution
- `p variable` - Print variable
- `l` - List code around current line
- `q` - Quit debugger

#### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "AWS_REGION": "us-east-1",
        "REDSHIFT_WORKGROUP": "supply-chain-workgroup"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v", "${file}"],
      "console": "integratedTerminal"
    }
  ]
}
```

#### CloudWatch Logs

```bash
# Tail Lambda logs
aws logs tail /aws/lambda/supply-chain-forecasting-agent --follow

# Filter logs by pattern
aws logs filter-log-events \
  --log-group-name /aws/lambda/supply-chain-forecasting-agent \
  --filter-pattern "ERROR"

# Get recent log streams
aws logs describe-log-streams \
  --log-group-name /aws/lambda/supply-chain-forecasting-agent \
  --order-by LastEventTime \
  --descending \
  --max-items 5
```

### Performance Profiling

#### Profile Python Code

```python
import cProfile
import pstats

# Profile function
profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = calculate_forecast(data)

profiler.disable()

# Print stats
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

#### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile script
python -m memory_profiler script.py
```

---

## Best Practices

### Code Style

- Follow PEP 8 style guide
- Use type hints for function signatures
- Write docstrings for all functions
- Keep functions small and focused
- Use meaningful variable names

### Testing Best Practices

- Write tests before fixing bugs (TDD)
- Aim for 80%+ code coverage
- Test edge cases and error conditions
- Use property-based tests for universal properties
- Mock external dependencies in unit tests

### Git Workflow

- Create feature branches for new work
- Write descriptive commit messages
- Keep commits small and focused
- Rebase before merging to main
- Delete branches after merging

### Security Best Practices

- Never commit credentials to Git
- Use environment variables for secrets
- Rotate AWS credentials regularly
- Use least privilege IAM policies
- Enable MFA on AWS account

---

## Additional Resources

### Documentation

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

### Learning Resources

- [Property-Based Testing with Hypothesis](https://hypothesis.works/articles/intro/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Python Testing Best Practices](https://realpython.com/python-testing/)

### Support

- **Technical Issues**: Create GitHub issue
- **Questions**: Contact team lead
- **AWS Support**: Use AWS Support Center

---

**Document End**
