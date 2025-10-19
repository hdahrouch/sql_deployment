"""
Unit tests for the Lambda SQL deployment function.

These tests use moto to mock AWS services for local testing.
"""

import os
import json
import pytest
from moto import mock_aws
import boto3
from botocore.exceptions import ClientError

# Import the Lambda function
import lambda_function


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def mock_env_vars():
    """Set up environment variables for testing."""
    os.environ['SQL_BUCKET'] = 'test-sql-bucket'
    os.environ['SQL_PREFIX'] = 'sql_queries/'
    os.environ['ATHENA_DATABASE'] = 'test_database'
    os.environ['ATHENA_OUTPUT_LOCATION'] = 's3://test-results-bucket/output/'


@pytest.fixture
def s3_setup(aws_credentials):
    """Set up S3 mock with test data."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        
        # Create test bucket
        s3.create_bucket(Bucket='test-sql-bucket')
        
        # Add test SQL files
        s3.put_object(
            Bucket='test-sql-bucket',
            Key='sql_queries/01_create_table.sql',
            Body=b'CREATE TABLE test_table (id INT, name STRING);'
        )
        s3.put_object(
            Bucket='test-sql-bucket',
            Key='sql_queries/02_create_another.sql',
            Body=b'CREATE TABLE another_table (id INT, value STRING);'
        )
        
        yield s3


def test_list_sql_files(s3_setup):
    """Test listing SQL files from S3."""
    files = lambda_function.list_sql_files('test-sql-bucket', 'sql_queries/')
    
    assert len(files) == 2
    assert 'sql_queries/01_create_table.sql' in files
    assert 'sql_queries/02_create_another.sql' in files


def test_list_sql_files_empty(s3_setup):
    """Test listing SQL files from empty prefix."""
    files = lambda_function.list_sql_files('test-sql-bucket', 'empty/')
    
    assert len(files) == 0


def test_read_sql_file(s3_setup):
    """Test reading SQL file content from S3."""
    content = lambda_function.read_sql_file(
        'test-sql-bucket',
        'sql_queries/01_create_table.sql'
    )
    
    assert 'CREATE TABLE test_table' in content
    assert content == 'CREATE TABLE test_table (id INT, name STRING);'


def test_read_sql_file_not_found(s3_setup):
    """Test reading non-existent SQL file."""
    with pytest.raises(ClientError):
        lambda_function.read_sql_file(
            'test-sql-bucket',
            'sql_queries/nonexistent.sql'
        )


def test_extract_table_name_basic():
    """Test extracting table name from basic CREATE TABLE statement."""
    sql = "CREATE TABLE users (id INT, name STRING);"
    table_name = lambda_function.extract_table_name(sql)
    assert table_name == "users"


def test_extract_table_name_external():
    """Test extracting table name from CREATE EXTERNAL TABLE statement."""
    sql = "CREATE EXTERNAL TABLE IF NOT EXISTS orders (id INT);"
    table_name = lambda_function.extract_table_name(sql)
    assert table_name == "orders"


def test_extract_table_name_with_comments():
    """Test extracting table name from SQL with comments."""
    sql = """
    -- This is a comment
    /* Multi-line
       comment */
    CREATE TABLE products (id INT, name STRING);
    """
    table_name = lambda_function.extract_table_name(sql)
    assert table_name == "products"


def test_extract_table_name_with_backticks():
    """Test extracting table name with backticks."""
    sql = "CREATE TABLE `my_table` (id INT);"
    table_name = lambda_function.extract_table_name(sql)
    assert table_name == "my_table"


def test_extract_table_name_not_create():
    """Test extracting table name from non-CREATE statement."""
    sql = "SELECT * FROM users;"
    table_name = lambda_function.extract_table_name(sql)
    assert table_name is None


def test_lambda_handler_missing_env_vars():
    """Test Lambda handler with missing environment variables."""
    # Clear environment variables
    for var in ['SQL_BUCKET', 'ATHENA_DATABASE', 'ATHENA_OUTPUT_LOCATION']:
        if var in os.environ:
            del os.environ[var]
    
    result = lambda_function.lambda_handler({}, None)
    
    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert 'error' in body


def test_lambda_handler_no_files(s3_setup, mock_env_vars):
    """Test Lambda handler when no SQL files are found."""
    # Override prefix to empty location
    os.environ['SQL_PREFIX'] = 'empty/'
    
    result = lambda_function.lambda_handler({}, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['files_processed'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
