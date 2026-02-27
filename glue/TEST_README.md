# ETL Property Tests

This directory contains property-based tests for the AWS Glue ETL job, specifically testing schema conformance and data transformation correctness.

## Overview

The tests verify **Property 23: ETL schema conformance** which states:

> For any data record transformed by the Glue ETL job, the transformed record should conform to the target Redshift table schema (correct column names, data types, and constraints).

**Validates: Requirements 6.2**

## Test Framework

- **pytest**: Test runner and framework
- **hypothesis**: Property-based testing library for generating test cases
- **pyspark**: For testing Spark transformations locally

## Installation

### Prerequisites

1. Python 3.9 or higher
2. Java 8 or 11 (required for PySpark)

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Property Tests

```bash
cd glue
pytest test_etl_properties.py -v
```

### Run Specific Test

```bash
pytest test_etl_properties.py::test_property_etl_schema_conformance_all_tables -v
```

### Run with Hypothesis Statistics

```bash
pytest test_etl_properties.py -v --hypothesis-show-statistics
```

### Run with Coverage

```bash
pytest test_etl_properties.py --cov=etl_job --cov-report=html
```

## Test Cases

### 1. Schema Conformance for All Tables

**Test**: `test_property_etl_schema_conformance_all_tables`

Verifies that for any table and any number of records:
- All required columns are present
- Column data types match the expected Redshift schema
- No extra columns are added
- Primary key columns are not NULL

**Hypothesis Strategy**: Generates random table names and record counts (1-50 records)

**Iterations**: 100 examples per test run

### 2. Invalid Data Filtering

**Test**: `test_property_etl_schema_conformance_filters_invalid`

Verifies that the ETL job correctly filters out invalid records (with NULL primary keys) while preserving valid records.

**Hypothesis Strategy**: Generates a mix of valid and invalid records

**Iterations**: 50 examples per test run

### 3. Column Order Preservation

**Test**: `test_property_etl_schema_column_order`

Verifies that transformed data maintains the exact column order specified in the target Redshift schema.

**Hypothesis Strategy**: Tests each table type

**Iterations**: 50 examples per test run

## Expected Output

### Successful Test Run

```
============================= test session starts ==============================
collected 3 items

test_etl_properties.py::test_property_etl_schema_conformance_all_tables PASSED [33%]
test_etl_properties.py::test_property_etl_schema_conformance_filters_invalid PASSED [66%]
test_etl_properties.py::test_property_etl_schema_column_order PASSED [100%]

============================== 3 passed in 45.23s ===============================
```

### Test Failure Example

If schema conformance is violated, you'll see output like:

```
FAILED test_etl_properties.py::test_property_etl_schema_conformance_all_tables
AssertionError: Column mismatch for product: expected {'product_id', 'sku', ...}, got {'product_id', 'extra_column', ...}
```

## Troubleshooting

### Java Not Found Error

If you see `JAVA_HOME is not set`, install Java and set the environment variable:

```bash
# On Ubuntu/Debian
sudo apt-get install openjdk-11-jdk
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# On macOS
brew install openjdk@11
export JAVA_HOME=/usr/local/opt/openjdk@11
```

### PySpark Import Errors

Ensure PySpark is installed correctly:

```bash
pip install pyspark==3.3.0
```

### AWS Glue Library Not Found

The `awsglue` library is only available in the AWS Glue environment. For local testing, the tests mock the necessary components. If you encounter import errors, ensure you're using the mock classes provided in the test file.

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: ETL Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd glue
          pip install -r requirements.txt
      - name: Run property tests
        run: |
          cd glue
          pytest test_etl_properties.py -v --hypothesis-show-statistics
```

## Property-Based Testing Approach

Property-based testing differs from traditional unit testing:

- **Unit tests**: Test specific examples (e.g., "product with ID PROD-001 transforms correctly")
- **Property tests**: Test universal properties (e.g., "ANY product record transforms to match schema")

The hypothesis library generates hundreds of random test cases to verify the property holds across all inputs, catching edge cases that manual test cases might miss.

## Next Steps

After verifying Property 23 passes:

1. Implement Property 24: ETL data persistence (Task 2.5)
2. Implement Property 25: ETL error handling (Task 2.7)
3. Implement Property 26: ETL metrics tracking (Task 2.8)

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [PySpark Testing Guide](https://spark.apache.org/docs/latest/api/python/getting_started/testing_pyspark.html)
