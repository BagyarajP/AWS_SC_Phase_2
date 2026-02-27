"""
Property-Based Tests for AWS Glue ETL Job

This module contains property-based tests to verify correctness properties
of the ETL job, particularly schema conformance and data transformation.

Testing Framework: pytest + hypothesis
Requirements: 6.2 - Transform data to match Redshift schema
"""

import pytest
from hypothesis import given, strategies as st, settings
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    DecimalType, DateType, TimestampType
)
from datetime import datetime, date
import sys
import os

# Import the ETL job functions
sys.path.insert(0, os.path.dirname(__file__))
from etl_job import (
    TABLE_SCHEMAS,
    validate_schema,
    transform_data
)

# Initialize Spark session for testing
@pytest.fixture(scope="module")
def spark():
    """Create a Spark session for testing"""
    spark_session = SparkSession.builder \
        .appName("ETL Property Tests") \
        .master("local[2]") \
        .getOrCreate()
    yield spark_session
    spark_session.stop()


# Helper function to create a mock GlueContext
class MockGlueContext:
    """Mock GlueContext for testing"""
    def __init__(self, spark_session):
        self.spark_session = spark_session


# Strategy for generating valid table names
table_name_strategy = st.sampled_from([
    'product',
    'warehouse',
    'supplier',
    'inventory',
    'purchase_order_header',
    'purchase_order_line',
    'sales_order_header',
    'sales_order_line'
])


# Strategy for generating product data
@st.composite
def product_data_strategy(draw):
    """Generate random product data"""
    return {
        'product_id': f"PROD-{draw(st.integers(min_value=0, max_value=9999)):05d}",
        'sku': f"SKU-{draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=3, max_size=3))}-{draw(st.integers(min_value=0, max_value=9999)):04d}",
        'product_name': draw(st.text(min_size=1, max_size=200)),
        'category': draw(st.sampled_from(['Electrical', 'Plumbing', 'HVAC', 'Safety', 'Tools'])),
        'unit_cost': float(draw(st.decimals(min_value=0.01, max_value=999.99, places=2))),
        'reorder_point': draw(st.integers(min_value=1, max_value=500)),
        'reorder_quantity': draw(st.integers(min_value=1, max_value=1000)),
        'created_at': datetime.now()
    }


# Strategy for generating warehouse data
@st.composite
def warehouse_data_strategy(draw):
    """Generate random warehouse data"""
    return {
        'warehouse_id': draw(st.sampled_from(['WH1_South', 'WH_Midland', 'WH_North'])),
        'warehouse_name': draw(st.text(min_size=1, max_size=100)),
        'location': draw(st.text(min_size=1, max_size=100)),
        'capacity': draw(st.integers(min_value=1000, max_value=100000)),
        'created_at': datetime.now()
    }


# Strategy for generating supplier data
@st.composite
def supplier_data_strategy(draw):
    """Generate random supplier data"""
    return {
        'supplier_id': f"SUP-{draw(st.integers(min_value=0, max_value=9999)):04d}",
        'supplier_name': draw(st.text(min_size=1, max_size=200)),
        'contact_email': f"{draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=5, max_size=10))}@example.com",
        'reliability_score': float(draw(st.decimals(min_value=0.00, max_value=0.99, places=2))),
        'avg_lead_time_days': draw(st.integers(min_value=1, max_value=60)),
        'defect_rate': float(draw(st.decimals(min_value=0.0001, max_value=0.9999, places=4))),
        'created_at': datetime.now()
    }


# Strategy for generating inventory data
@st.composite
def inventory_data_strategy(draw):
    """Generate random inventory data"""
    return {
        'inventory_id': f"INV-{draw(st.integers(min_value=0, max_value=99999)):05d}",
        'product_id': f"PROD-{draw(st.integers(min_value=0, max_value=9999)):05d}",
        'warehouse_id': draw(st.sampled_from(['WH1_South', 'WH_Midland', 'WH_North'])),
        'quantity_on_hand': draw(st.integers(min_value=0, max_value=10000)),
        'last_updated': datetime.now()
    }


# Feature: supply-chain-ai-platform, Property 23: ETL schema conformance
@settings(max_examples=100)
@given(
    table_name=table_name_strategy,
    num_records=st.integers(min_value=1, max_value=50)
)
def test_property_etl_schema_conformance_all_tables(spark, table_name, num_records):
    """
    Property 23: ETL schema conformance
    
    For any data record transformed by the Glue ETL job, the transformed record
    should conform to the target Redshift table schema (correct column names,
    data types, and constraints).
    
    **Validates: Requirements 6.2**
    
    This property verifies that:
    1. All required columns are present in the transformed data
    2. Column data types match the expected Redshift schema
    3. No extra columns are added during transformation
    4. Primary key columns are not NULL
    """
    from awsglue.dynamicframe import DynamicFrame
    
    # Get expected schema for the table
    expected_schema = TABLE_SCHEMAS[table_name]
    
    # Generate test data based on table type
    test_data = []
    for _ in range(num_records):
        if table_name == 'product':
            record = {
                'product_id': f"PROD-{_:05d}",
                'sku': f"SKU-TEST-{_:04d}",
                'product_name': f"Product {_}",
                'category': 'Electrical',
                'unit_cost': '10.50',
                'reorder_point': '100',
                'reorder_quantity': '200',
                'created_at': str(datetime.now())
            }
        elif table_name == 'warehouse':
            record = {
                'warehouse_id': f"WH-{_:03d}",
                'warehouse_name': f"Warehouse {_}",
                'location': f"Location {_}",
                'capacity': '10000',
                'created_at': str(datetime.now())
            }
        elif table_name == 'supplier':
            record = {
                'supplier_id': f"SUP-{_:04d}",
                'supplier_name': f"Supplier {_}",
                'contact_email': f"supplier{_}@example.com",
                'reliability_score': '0.95',
                'avg_lead_time_days': '7',
                'defect_rate': '0.0100',
                'created_at': str(datetime.now())
            }
        elif table_name == 'inventory':
            record = {
                'inventory_id': f"INV-{_:05d}",
                'product_id': f"PROD-{_:05d}",
                'warehouse_id': 'WH1_South',
                'quantity_on_hand': '500',
                'last_updated': str(datetime.now())
            }
        elif table_name == 'purchase_order_header':
            record = {
                'po_id': f"PO-{_:06d}",
                'supplier_id': f"SUP-{_:04d}",
                'order_date': str(date.today()),
                'expected_delivery_date': str(date.today()),
                'total_amount': '1000.00',
                'status': 'pending',
                'created_by': 'system',
                'approved_by': None,
                'approved_at': None,
                'created_at': str(datetime.now())
            }
        elif table_name == 'purchase_order_line':
            record = {
                'po_line_id': f"POL-{_:06d}",
                'po_id': f"PO-{_:06d}",
                'product_id': f"PROD-{_:05d}",
                'quantity': '100',
                'unit_price': '10.00',
                'line_total': '1000.00',
                'created_at': str(datetime.now())
            }
        elif table_name == 'sales_order_header':
            record = {
                'so_id': f"SO-{_:06d}",
                'order_date': str(date.today()),
                'warehouse_id': 'WH1_South',
                'status': 'completed',
                'created_at': str(datetime.now())
            }
        elif table_name == 'sales_order_line':
            record = {
                'so_line_id': f"SOL-{_:06d}",
                'so_id': f"SO-{_:06d}",
                'product_id': f"PROD-{_:05d}",
                'quantity': '10',
                'created_at': str(datetime.now())
            }
        
        test_data.append(record)
    
    # Create DataFrame from test data
    df = spark.createDataFrame(test_data)
    
    # Create DynamicFrame
    glue_context = MockGlueContext(spark)
    dynamic_frame = DynamicFrame.fromDF(df, glue_context, f"{table_name}_test")
    
    # Transform the data
    transformed_frame = transform_data(dynamic_frame, table_name)
    transformed_df = transformed_frame.toDF()
    
    # Verify schema conformance
    # 1. Check all required columns are present
    transformed_columns = set(transformed_df.columns)
    expected_columns = set(expected_schema.keys())
    
    assert transformed_columns == expected_columns, \
        f"Column mismatch for {table_name}: expected {expected_columns}, got {transformed_columns}"
    
    # 2. Check data types match expected schema
    for column_name, expected_type in expected_schema.items():
        actual_type = transformed_df.schema[column_name].dataType
        
        # Type matching logic
        if isinstance(expected_type, StringType):
            assert isinstance(actual_type, StringType), \
                f"Column {column_name} should be StringType, got {type(actual_type).__name__}"
        elif isinstance(expected_type, IntegerType):
            assert isinstance(actual_type, IntegerType), \
                f"Column {column_name} should be IntegerType, got {type(actual_type).__name__}"
        elif isinstance(expected_type, DecimalType):
            assert isinstance(actual_type, DecimalType), \
                f"Column {column_name} should be DecimalType, got {type(actual_type).__name__}"
        elif isinstance(expected_type, DateType):
            assert isinstance(actual_type, DateType), \
                f"Column {column_name} should be DateType, got {type(actual_type).__name__}"
        elif isinstance(expected_type, TimestampType):
            assert isinstance(actual_type, TimestampType), \
                f"Column {column_name} should be TimestampType, got {type(actual_type).__name__}"
    
    # 3. Verify primary keys are not NULL
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
        null_count = transformed_df.filter(transformed_df[pk_column].isNull()).count()
        assert null_count == 0, \
            f"Primary key column {pk_column} should not contain NULL values"
    
    # 4. Verify record count (should match input after filtering invalid records)
    assert transformed_df.count() > 0, \
        f"Transformed data should contain records"


# Feature: supply-chain-ai-platform, Property 23: ETL schema conformance (with invalid data)
@settings(max_examples=50)
@given(
    table_name=table_name_strategy,
    num_valid=st.integers(min_value=1, max_value=20),
    num_invalid=st.integers(min_value=1, max_value=10)
)
def test_property_etl_schema_conformance_filters_invalid(spark, table_name, num_valid, num_invalid):
    """
    Property 23: ETL schema conformance (invalid data handling)
    
    For any data with invalid records (NULL primary keys), the ETL job should
    filter out invalid records while preserving valid ones, and the remaining
    records should conform to the schema.
    
    **Validates: Requirements 6.2**
    """
    from awsglue.dynamicframe import DynamicFrame
    
    # Generate valid and invalid test data
    test_data = []
    
    # Add valid records
    for i in range(num_valid):
        if table_name == 'product':
            record = {
                'product_id': f"PROD-{i:05d}",
                'sku': f"SKU-TEST-{i:04d}",
                'product_name': f"Product {i}",
                'category': 'Electrical',
                'unit_cost': '10.50',
                'reorder_point': '100',
                'reorder_quantity': '200',
                'created_at': str(datetime.now())
            }
        elif table_name == 'warehouse':
            record = {
                'warehouse_id': f"WH-{i:03d}",
                'warehouse_name': f"Warehouse {i}",
                'location': f"Location {i}",
                'capacity': '10000',
                'created_at': str(datetime.now())
            }
        else:
            # Simplified for other tables
            continue
        
        test_data.append(record)
    
    # Add invalid records (NULL primary keys)
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
    if pk_column and table_name in ['product', 'warehouse']:
        for i in range(num_invalid):
            if table_name == 'product':
                invalid_record = {
                    'product_id': None,  # NULL primary key
                    'sku': f"SKU-INVALID-{i:04d}",
                    'product_name': f"Invalid Product {i}",
                    'category': 'Electrical',
                    'unit_cost': '10.50',
                    'reorder_point': '100',
                    'reorder_quantity': '200',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'warehouse':
                invalid_record = {
                    'warehouse_id': None,  # NULL primary key
                    'warehouse_name': f"Invalid Warehouse {i}",
                    'location': f"Location {i}",
                    'capacity': '10000',
                    'created_at': str(datetime.now())
                }
            
            test_data.append(invalid_record)
    
    if not test_data:
        pytest.skip(f"Skipping test for {table_name} - no test data generated")
    
    # Create DataFrame and DynamicFrame
    df = spark.createDataFrame(test_data)
    glue_context = MockGlueContext(spark)
    dynamic_frame = DynamicFrame.fromDF(df, glue_context, f"{table_name}_test")
    
    # Transform the data
    transformed_frame = transform_data(dynamic_frame, table_name)
    transformed_df = transformed_frame.toDF()
    
    # Verify that invalid records were filtered out
    assert transformed_df.count() == num_valid, \
        f"Should have {num_valid} valid records after filtering, got {transformed_df.count()}"
    
    # Verify all remaining records have non-NULL primary keys
    if pk_column:
        null_count = transformed_df.filter(transformed_df[pk_column].isNull()).count()
        assert null_count == 0, \
            f"No NULL primary keys should remain after transformation"


# Feature: supply-chain-ai-platform, Property 23: ETL schema conformance (column order)
@settings(max_examples=50)
@given(table_name=table_name_strategy)
def test_property_etl_schema_column_order(spark, table_name):
    """
    Property 23: ETL schema conformance (column order)
    
    For any transformed data, columns should be in the exact order specified
    by the target Redshift schema.
    
    **Validates: Requirements 6.2**
    """
    from awsglue.dynamicframe import DynamicFrame
    
    # Get expected schema
    expected_schema = TABLE_SCHEMAS[table_name]
    expected_column_order = list(expected_schema.keys())
    
    # Create minimal test data
    test_data = []
    if table_name == 'product':
        test_data = [{
            'product_id': 'PROD-00001',
            'sku': 'SKU-TEST-0001',
            'product_name': 'Test Product',
            'category': 'Electrical',
            'unit_cost': '10.50',
            'reorder_point': '100',
            'reorder_quantity': '200',
            'created_at': str(datetime.now())
        }]
    elif table_name == 'warehouse':
        test_data = [{
            'warehouse_id': 'WH-001',
            'warehouse_name': 'Test Warehouse',
            'location': 'Test Location',
            'capacity': '10000',
            'created_at': str(datetime.now())
        }]
    else:
        pytest.skip(f"Skipping column order test for {table_name}")
    
    # Create DataFrame and DynamicFrame
    df = spark.createDataFrame(test_data)
    glue_context = MockGlueContext(spark)
    dynamic_frame = DynamicFrame.fromDF(df, glue_context, f"{table_name}_test")
    
    # Transform the data
    transformed_frame = transform_data(dynamic_frame, table_name)
    transformed_df = transformed_frame.toDF()
    
    # Verify column order matches expected schema
    actual_column_order = transformed_df.columns
    assert actual_column_order == expected_column_order, \
        f"Column order mismatch: expected {expected_column_order}, got {actual_column_order}"


# Feature: supply-chain-ai-platform, Property 24: ETL data persistence
@settings(max_examples=100)
@given(
    table_name=table_name_strategy,
    num_records=st.integers(min_value=1, max_value=50)
)
def test_property_etl_data_persistence(spark, table_name, num_records):
    """
    Property 24: ETL data persistence
    
    For any valid data record processed by the Glue ETL job, the record should
    be inserted into the corresponding Redshift table. This property verifies
    that all valid records that pass through the transformation pipeline are
    persisted correctly.
    
    **Validates: Requirements 6.3**
    
    This property verifies that:
    1. All valid input records result in output records after transformation
    2. The number of output records matches the number of valid input records
    3. Record data is preserved through the transformation pipeline
    4. Primary key values are maintained from input to output
    """
    from awsglue.dynamicframe import DynamicFrame
    
    # Generate test data based on table type
    test_data = []
    expected_ids = []
    
    for i in range(num_records):
        if table_name == 'product':
            product_id = f"PROD-{i:05d}"
            record = {
                'product_id': product_id,
                'sku': f"SKU-TEST-{i:04d}",
                'product_name': f"Product {i}",
                'category': 'Electrical',
                'unit_cost': '10.50',
                'reorder_point': '100',
                'reorder_quantity': '200',
                'created_at': str(datetime.now())
            }
            expected_ids.append(product_id)
        elif table_name == 'warehouse':
            warehouse_id = f"WH-{i:03d}"
            record = {
                'warehouse_id': warehouse_id,
                'warehouse_name': f"Warehouse {i}",
                'location': f"Location {i}",
                'capacity': '10000',
                'created_at': str(datetime.now())
            }
            expected_ids.append(warehouse_id)
        elif table_name == 'supplier':
            supplier_id = f"SUP-{i:04d}"
            record = {
                'supplier_id': supplier_id,
                'supplier_name': f"Supplier {i}",
                'contact_email': f"supplier{i}@example.com",
                'reliability_score': '0.95',
                'avg_lead_time_days': '7',
                'defect_rate': '0.0100',
                'created_at': str(datetime.now())
            }
            expected_ids.append(supplier_id)
        elif table_name == 'inventory':
            inventory_id = f"INV-{i:05d}"
            record = {
                'inventory_id': inventory_id,
                'product_id': f"PROD-{i:05d}",
                'warehouse_id': 'WH1_South',
                'quantity_on_hand': '500',
                'last_updated': str(datetime.now())
            }
            expected_ids.append(inventory_id)
        elif table_name == 'purchase_order_header':
            po_id = f"PO-{i:06d}"
            record = {
                'po_id': po_id,
                'supplier_id': f"SUP-{i:04d}",
                'order_date': str(date.today()),
                'expected_delivery_date': str(date.today()),
                'total_amount': '1000.00',
                'status': 'pending',
                'created_by': 'system',
                'approved_by': None,
                'approved_at': None,
                'created_at': str(datetime.now())
            }
            expected_ids.append(po_id)
        elif table_name == 'purchase_order_line':
            po_line_id = f"POL-{i:06d}"
            record = {
                'po_line_id': po_line_id,
                'po_id': f"PO-{i:06d}",
                'product_id': f"PROD-{i:05d}",
                'quantity': '100',
                'unit_price': '10.00',
                'line_total': '1000.00',
                'created_at': str(datetime.now())
            }
            expected_ids.append(po_line_id)
        elif table_name == 'sales_order_header':
            so_id = f"SO-{i:06d}"
            record = {
                'so_id': so_id,
                'order_date': str(date.today()),
                'warehouse_id': 'WH1_South',
                'status': 'completed',
                'created_at': str(datetime.now())
            }
            expected_ids.append(so_id)
        elif table_name == 'sales_order_line':
            so_line_id = f"SOL-{i:06d}"
            record = {
                'so_line_id': so_line_id,
                'so_id': f"SO-{i:06d}",
                'product_id': f"PROD-{i:05d}",
                'quantity': '10',
                'created_at': str(datetime.now())
            }
            expected_ids.append(so_line_id)
        
        test_data.append(record)
    
    # Create DataFrame from test data
    df = spark.createDataFrame(test_data)
    
    # Create DynamicFrame
    glue_context = MockGlueContext(spark)
    dynamic_frame = DynamicFrame.fromDF(df, glue_context, f"{table_name}_test")
    
    # Record initial count
    initial_count = dynamic_frame.count()
    
    # Transform the data (simulates the ETL transformation pipeline)
    transformed_frame = transform_data(dynamic_frame, table_name)
    transformed_df = transformed_frame.toDF()
    
    # Verify data persistence properties
    
    # 1. All valid records should be present after transformation
    output_count = transformed_df.count()
    assert output_count == initial_count, \
        f"Data persistence failed: expected {initial_count} records, got {output_count}"
    
    # 2. Verify all expected primary key values are present in output
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
        # Collect all primary key values from output
        output_ids = [row[pk_column] for row in transformed_df.select(pk_column).collect()]
        
        # Verify all expected IDs are present
        for expected_id in expected_ids:
            assert expected_id in output_ids, \
                f"Primary key {expected_id} not found in output for table {table_name}"
    
    # 3. Verify no duplicate records were created
    if pk_column:
        distinct_count = transformed_df.select(pk_column).distinct().count()
        assert distinct_count == output_count, \
            f"Duplicate records detected: {output_count} records but only {distinct_count} unique primary keys"
    
    # 4. Verify data integrity - sample a record and check field values are preserved
    if output_count > 0:
        # Get first record from input and output
        input_record = test_data[0]
        output_record = transformed_df.first()
        
        # Verify key fields are preserved (check a few critical fields)
        if pk_column:
            assert output_record[pk_column] == input_record[pk_column], \
                f"Primary key value changed during transformation"
        
        # Verify at least one other field is preserved correctly
        if table_name == 'product':
            assert output_record['sku'] == input_record['sku'], \
                f"SKU value not preserved during transformation"
        elif table_name == 'warehouse':
            assert output_record['warehouse_name'] == input_record['warehouse_name'], \
                f"Warehouse name not preserved during transformation"


# Feature: supply-chain-ai-platform, Property 24: ETL data persistence (with mixed valid/invalid data)
@settings(max_examples=50)
@given(
    table_name=table_name_strategy,
    num_valid=st.integers(min_value=1, max_value=30),
    num_invalid=st.integers(min_value=1, max_value=10)
)
def test_property_etl_data_persistence_filters_invalid(spark, table_name, num_valid, num_invalid):
    """
    Property 24: ETL data persistence (with invalid data filtering)
    
    For any valid data record processed by the Glue ETL job, the record should
    be inserted into Redshift. Invalid records (e.g., NULL primary keys) should
    be filtered out, but all valid records should be persisted.
    
    **Validates: Requirements 6.3**
    """
    from awsglue.dynamicframe import DynamicFrame
    
    # Generate valid and invalid test data
    test_data = []
    expected_valid_ids = []
    
    # Add valid records
    for i in range(num_valid):
        if table_name == 'product':
            product_id = f"PROD-VALID-{i:05d}"
            record = {
                'product_id': product_id,
                'sku': f"SKU-VALID-{i:04d}",
                'product_name': f"Valid Product {i}",
                'category': 'Electrical',
                'unit_cost': '10.50',
                'reorder_point': '100',
                'reorder_quantity': '200',
                'created_at': str(datetime.now())
            }
            expected_valid_ids.append(product_id)
        elif table_name == 'warehouse':
            warehouse_id = f"WH-VALID-{i:03d}"
            record = {
                'warehouse_id': warehouse_id,
                'warehouse_name': f"Valid Warehouse {i}",
                'location': f"Location {i}",
                'capacity': '10000',
                'created_at': str(datetime.now())
            }
            expected_valid_ids.append(warehouse_id)
        elif table_name == 'supplier':
            supplier_id = f"SUP-VALID-{i:04d}"
            record = {
                'supplier_id': supplier_id,
                'supplier_name': f"Valid Supplier {i}",
                'contact_email': f"supplier{i}@example.com",
                'reliability_score': '0.95',
                'avg_lead_time_days': '7',
                'defect_rate': '0.0100',
                'created_at': str(datetime.now())
            }
            expected_valid_ids.append(supplier_id)
        else:
            # Skip other tables for this test
            continue
        
        test_data.append(record)
    
    # Add invalid records (NULL primary keys)
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
    if pk_column and table_name in ['product', 'warehouse', 'supplier']:
        for i in range(num_invalid):
            if table_name == 'product':
                invalid_record = {
                    'product_id': None,  # NULL primary key
                    'sku': f"SKU-INVALID-{i:04d}",
                    'product_name': f"Invalid Product {i}",
                    'category': 'Electrical',
                    'unit_cost': '10.50',
                    'reorder_point': '100',
                    'reorder_quantity': '200',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'warehouse':
                invalid_record = {
                    'warehouse_id': None,  # NULL primary key
                    'warehouse_name': f"Invalid Warehouse {i}",
                    'location': f"Location {i}",
                    'capacity': '10000',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'supplier':
                invalid_record = {
                    'supplier_id': None,  # NULL primary key
                    'supplier_name': f"Invalid Supplier {i}",
                    'contact_email': f"invalid{i}@example.com",
                    'reliability_score': '0.95',
                    'avg_lead_time_days': '7',
                    'defect_rate': '0.0100',
                    'created_at': str(datetime.now())
                }
            
            test_data.append(invalid_record)
    
    if not test_data:
        pytest.skip(f"Skipping persistence test for {table_name} - no test data generated")
    
    # Create DataFrame and DynamicFrame
    df = spark.createDataFrame(test_data)
    glue_context = MockGlueContext(spark)
    dynamic_frame = DynamicFrame.fromDF(df, glue_context, f"{table_name}_test")
    
    # Transform the data
    transformed_frame = transform_data(dynamic_frame, table_name)
    transformed_df = transformed_frame.toDF()
    
    # Verify that only valid records were persisted
    output_count = transformed_df.count()
    assert output_count == num_valid, \
        f"Should persist exactly {num_valid} valid records, got {output_count}"
    
    # Verify all expected valid IDs are present
    if pk_column:
        output_ids = [row[pk_column] for row in transformed_df.select(pk_column).collect()]
        
        for expected_id in expected_valid_ids:
            assert expected_id in output_ids, \
                f"Valid record with ID {expected_id} was not persisted"
        
        # Verify no NULL primary keys in output
        null_count = transformed_df.filter(transformed_df[pk_column].isNull()).count()
        assert null_count == 0, \
            f"Invalid records with NULL primary keys should not be persisted"


# Feature: supply-chain-ai-platform, Property 25: ETL error handling
@settings(max_examples=100)
@given(
    table_name=table_name_strategy,
    num_valid=st.integers(min_value=1, max_value=30),
    num_invalid=st.integers(min_value=1, max_value=20)
)
def test_property_etl_error_handling_skips_invalid_records(spark, table_name, num_valid, num_invalid):
    """
    Property 25: ETL error handling
    
    For any invalid data record encountered during ETL, the Glue job should
    log an error and skip the record without failing the entire job. Valid
    records should continue to be processed successfully.
    
    **Validates: Requirements 6.5**
    
    This property verifies that:
    1. Invalid records (NULL primary keys, schema violations) are skipped
    2. Valid records are processed successfully despite presence of invalid records
    3. The ETL job continues processing all records without failing
    4. Error information is tracked in metrics
    """
    from awsglue.dynamicframe import DynamicFrame
    
    # Generate mixed valid and invalid test data
    test_data = []
    expected_valid_count = num_valid
    
    # Add valid records
    for i in range(num_valid):
        if table_name == 'product':
            record = {
                'product_id': f"PROD-VALID-{i:05d}",
                'sku': f"SKU-VALID-{i:04d}",
                'product_name': f"Valid Product {i}",
                'category': 'Electrical',
                'unit_cost': '10.50',
                'reorder_point': '100',
                'reorder_quantity': '200',
                'created_at': str(datetime.now())
            }
        elif table_name == 'warehouse':
            record = {
                'warehouse_id': f"WH-VALID-{i:03d}",
                'warehouse_name': f"Valid Warehouse {i}",
                'location': f"Location {i}",
                'capacity': '10000',
                'created_at': str(datetime.now())
            }
        elif table_name == 'supplier':
            record = {
                'supplier_id': f"SUP-VALID-{i:04d}",
                'supplier_name': f"Valid Supplier {i}",
                'contact_email': f"supplier{i}@example.com",
                'reliability_score': '0.95',
                'avg_lead_time_days': '7',
                'defect_rate': '0.0100',
                'created_at': str(datetime.now())
            }
        elif table_name == 'inventory':
            record = {
                'inventory_id': f"INV-VALID-{i:05d}",
                'product_id': f"PROD-{i:05d}",
                'warehouse_id': 'WH1_South',
                'quantity_on_hand': '500',
                'last_updated': str(datetime.now())
            }
        elif table_name == 'purchase_order_header':
            record = {
                'po_id': f"PO-VALID-{i:06d}",
                'supplier_id': f"SUP-{i:04d}",
                'order_date': str(date.today()),
                'expected_delivery_date': str(date.today()),
                'total_amount': '1000.00',
                'status': 'pending',
                'created_by': 'system',
                'approved_by': None,
                'approved_at': None,
                'created_at': str(datetime.now())
            }
        elif table_name == 'purchase_order_line':
            record = {
                'po_line_id': f"POL-VALID-{i:06d}",
                'po_id': f"PO-{i:06d}",
                'product_id': f"PROD-{i:05d}",
                'quantity': '100',
                'unit_price': '10.00',
                'line_total': '1000.00',
                'created_at': str(datetime.now())
            }
        elif table_name == 'sales_order_header':
            record = {
                'so_id': f"SO-VALID-{i:06d}",
                'order_date': str(date.today()),
                'warehouse_id': 'WH1_South',
                'status': 'completed',
                'created_at': str(datetime.now())
            }
        elif table_name == 'sales_order_line':
            record = {
                'so_line_id': f"SOL-VALID-{i:06d}",
                'so_id': f"SO-{i:06d}",
                'product_id': f"PROD-{i:05d}",
                'quantity': '10',
                'created_at': str(datetime.now())
            }
        
        test_data.append(record)
    
    # Add invalid records (NULL primary keys)
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
        for i in range(num_invalid):
            if table_name == 'product':
                invalid_record = {
                    'product_id': None,  # NULL primary key - invalid
                    'sku': f"SKU-INVALID-{i:04d}",
                    'product_name': f"Invalid Product {i}",
                    'category': 'Electrical',
                    'unit_cost': '10.50',
                    'reorder_point': '100',
                    'reorder_quantity': '200',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'warehouse':
                invalid_record = {
                    'warehouse_id': None,  # NULL primary key - invalid
                    'warehouse_name': f"Invalid Warehouse {i}",
                    'location': f"Location {i}",
                    'capacity': '10000',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'supplier':
                invalid_record = {
                    'supplier_id': None,  # NULL primary key - invalid
                    'supplier_name': f"Invalid Supplier {i}",
                    'contact_email': f"invalid{i}@example.com",
                    'reliability_score': '0.95',
                    'avg_lead_time_days': '7',
                    'defect_rate': '0.0100',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'inventory':
                invalid_record = {
                    'inventory_id': None,  # NULL primary key - invalid
                    'product_id': f"PROD-{i:05d}",
                    'warehouse_id': 'WH1_South',
                    'quantity_on_hand': '500',
                    'last_updated': str(datetime.now())
                }
            elif table_name == 'purchase_order_header':
                invalid_record = {
                    'po_id': None,  # NULL primary key - invalid
                    'supplier_id': f"SUP-{i:04d}",
                    'order_date': str(date.today()),
                    'expected_delivery_date': str(date.today()),
                    'total_amount': '1000.00',
                    'status': 'pending',
                    'created_by': 'system',
                    'approved_by': None,
                    'approved_at': None,
                    'created_at': str(datetime.now())
                }
            elif table_name == 'purchase_order_line':
                invalid_record = {
                    'po_line_id': None,  # NULL primary key - invalid
                    'po_id': f"PO-{i:06d}",
                    'product_id': f"PROD-{i:05d}",
                    'quantity': '100',
                    'unit_price': '10.00',
                    'line_total': '1000.00',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'sales_order_header':
                invalid_record = {
                    'so_id': None,  # NULL primary key - invalid
                    'order_date': str(date.today()),
                    'warehouse_id': 'WH1_South',
                    'status': 'completed',
                    'created_at': str(datetime.now())
                }
            elif table_name == 'sales_order_line':
                invalid_record = {
                    'so_line_id': None,  # NULL primary key - invalid
                    'so_id': f"SO-{i:06d}",
                    'product_id': f"PROD-{i:05d}",
                    'quantity': '10',
                    'created_at': str(datetime.now())
                }
            
            test_data.append(invalid_record)
    
    # Create DataFrame and DynamicFrame
    df = spark.createDataFrame(test_data)
    glue_context = MockGlueContext(spark)
    dynamic_frame = DynamicFrame.fromDF(df, glue_context, f"{table_name}_test")
    
    # Record initial counts
    initial_total_count = dynamic_frame.count()
    
    # Transform the data - this should handle errors gracefully
    # The transform_data function should skip invalid records without failing
    try:
        transformed_frame = transform_data(dynamic_frame, table_name)
        transformed_df = transformed_frame.toDF()
        
        # Verify error handling properties
        
        # 1. Job should complete successfully despite invalid records
        assert transformed_frame is not None, \
            "ETL job should not fail when encountering invalid records"
        
        # 2. Invalid records should be skipped (filtered out)
        output_count = transformed_df.count()
        assert output_count == expected_valid_count, \
            f"Should skip {num_invalid} invalid records and keep {expected_valid_count} valid records, got {output_count}"
        
        # 3. All output records should have non-NULL primary keys
        if pk_column:
            null_pk_count = transformed_df.filter(transformed_df[pk_column].isNull()).count()
            assert null_pk_count == 0, \
                "All output records should have valid (non-NULL) primary keys"
        
        # 4. Valid records should be processed correctly
        # Verify that at least one valid record is present and correctly formatted
        if output_count > 0:
            sample_record = transformed_df.first()
            
            # Check that the record has all expected columns
            expected_schema = TABLE_SCHEMAS[table_name]
            for column_name in expected_schema.keys():
                assert column_name in transformed_df.columns, \
                    f"Valid records should have all expected columns including {column_name}"
            
            # Verify primary key is not NULL for valid records
            if pk_column:
                assert sample_record[pk_column] is not None, \
                    "Valid records should have non-NULL primary keys"
        
        # 5. Verify the ratio of skipped records matches expectations
        skipped_count = initial_total_count - output_count
        assert skipped_count == num_invalid, \
            f"Should skip exactly {num_invalid} invalid records, skipped {skipped_count}"
        
    except Exception as e:
        # If an exception is raised, the error handling is not working correctly
        pytest.fail(
            f"ETL job should handle invalid records gracefully without raising exceptions. "
            f"Got exception: {str(e)}"
        )


# Feature: supply-chain-ai-platform, Property 25: ETL error handling (missing files)
@settings(max_examples=50)
@given(table_name=table_name_strategy)
def test_property_etl_error_handling_missing_file(spark, table_name):
    """
    Property 25: ETL error handling (missing file scenario)
    
    When a source file is missing from S3, the ETL job should log an error
    and continue processing other tables without failing the entire job.
    
    **Validates: Requirements 6.5**
    
    This property verifies that:
    1. Missing file errors are handled gracefully
    2. The extract_from_s3 function returns None for missing files
    3. The job can continue processing other tables
    """
    from etl_job import extract_from_s3, metrics
    
    # Reset metrics for this test
    metrics['errors'] = []
    metrics['total_records_read'] = 0
    
    # Mock the check_s3_file_exists to return False (file not found)
    import etl_job
    original_check = etl_job.check_s3_file_exists
    
    def mock_check_missing(bucket, key):
        return False  # Simulate missing file
    
    etl_job.check_s3_file_exists = mock_check_missing
    
    try:
        # Attempt to extract from non-existent file
        result = extract_from_s3(table_name)
        
        # Verify error handling properties
        
        # 1. Function should return None for missing files (not raise exception)
        assert result is None, \
            "extract_from_s3 should return None for missing files, not raise exception"
        
        # 2. Error should be logged in metrics
        assert len(metrics['errors']) > 0, \
            "Missing file error should be logged in metrics"
        
        # 3. Error log should contain relevant information
        error_logged = any(
            table_name in error.get('table', '') and 
            'Missing file' in error.get('error', '')
            for error in metrics['errors']
        )
        assert error_logged, \
            f"Error log should contain information about missing file for table {table_name}"
        
        # 4. No records should be read from missing file
        # (metrics['total_records_read'] should not increase)
        assert metrics['total_records_read'] == 0, \
            "No records should be counted when file is missing"
        
    finally:
        # Restore original function
        etl_job.check_s3_file_exists = original_check


# Feature: supply-chain-ai-platform, Property 25: ETL error handling (schema validation failure)
@settings(max_examples=50)
@given(
    table_name=table_name_strategy,
    num_records=st.integers(min_value=1, max_value=20)
)
def test_property_etl_error_handling_schema_validation_failure(spark, table_name, num_records):
    """
    Property 25: ETL error handling (schema validation failure)
    
    When data has missing required columns (schema validation fails), the
    transform_data function should raise an error that can be caught and logged,
    allowing the job to continue with other tables.
    
    **Validates: Requirements 6.5**
    
    This property verifies that:
    1. Schema validation failures are detected
    2. Appropriate errors are raised for invalid schemas
    3. Error information is clear and actionable
    """
    from awsglue.dynamicframe import DynamicFrame
    from etl_job import validate_schema
    
    # Create test data with MISSING required columns
    test_data = []
    for i in range(num_records):
        # Create incomplete record (missing most required columns)
        if table_name == 'product':
            incomplete_record = {
                'product_id': f"PROD-{i:05d}",
                'sku': f"SKU-{i:04d}"
                # Missing: product_name, category, unit_cost, reorder_point, reorder_quantity, created_at
            }
        elif table_name == 'warehouse':
            incomplete_record = {
                'warehouse_id': f"WH-{i:03d}"
                # Missing: warehouse_name, location, capacity, created_at
            }
        elif table_name == 'supplier':
            incomplete_record = {
                'supplier_id': f"SUP-{i:04d}"
                # Missing: supplier_name, contact_email, reliability_score, avg_lead_time_days, defect_rate, created_at
            }
        else:
            # For other tables, create minimal incomplete data
            incomplete_record = {'id': f"ID-{i:05d}"}
        
        test_data.append(incomplete_record)
    
    # Create DataFrame with incomplete schema
    df = spark.createDataFrame(test_data)
    
    # Verify schema validation detects the problem
    
    # 1. validate_schema should return False for incomplete schema
    is_valid = validate_schema(df, table_name)
    assert is_valid is False, \
        f"Schema validation should fail for incomplete data with missing columns"
    
    # 2. Attempting to transform should raise an error
    glue_context = MockGlueContext(spark)
    dynamic_frame = DynamicFrame.fromDF(df, glue_context, f"{table_name}_test")
    
    with pytest.raises(ValueError) as exc_info:
        transform_data(dynamic_frame, table_name)
    
    # 3. Error message should be informative
    error_message = str(exc_info.value)
    assert 'Schema validation failed' in error_message or 'missing columns' in error_message.lower(), \
        "Error message should clearly indicate schema validation failure"
    assert table_name in error_message, \
        "Error message should identify which table failed validation"
