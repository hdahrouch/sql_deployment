"""
AWS Lambda function to list and execute SQL queries in Athena.

This function:
1. Lists SQL query files from an S3 bucket
2. Executes each query one by one in AWS Athena
3. Handles CREATE TABLE statements
"""

import os
import json
import logging
import time
import re
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients lazily
_s3_client = None
_athena_client = None
_glue_client = None


def get_s3_client():
    """Get or create S3 client."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def get_athena_client():
    """Get or create Athena client."""
    global _athena_client
    if _athena_client is None:
        _athena_client = boto3.client('athena')
    return _athena_client


def get_glue_client():
    """Get or create Glue client."""
    global _glue_client
    if _glue_client is None:
        _glue_client = boto3.client('glue')
    return _glue_client


def list_sql_files(bucket_name, prefix='sql_queries/'):
    """
    List all SQL files from the specified S3 bucket and prefix.
    
    Args:
        bucket_name (str): S3 bucket name
        prefix (str): Prefix path where SQL files are stored
        
    Returns:
        list: List of S3 object keys for SQL files
    """
    sql_files = []
    
    try:
        logger.info(f"Listing SQL files from s3://{bucket_name}/{prefix}")
        
        s3_client = get_s3_client()
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Filter for .sql files only
                    if key.endswith('.sql'):
                        sql_files.append(key)
                        logger.info(f"Found SQL file: {key}")
        
        # Sort files alphabetically for consistent execution order
        sql_files.sort()
        logger.info(f"Total SQL files found: {len(sql_files)}")
        
    except ClientError as e:
        logger.error(f"Error listing SQL files: {e}")
        raise
    
    return sql_files


def read_sql_file(bucket_name, key):
    """
    Read SQL query content from S3.
    
    Args:
        bucket_name (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        str: SQL query content
    """
    try:
        logger.info(f"Reading SQL file: s3://{bucket_name}/{key}")
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        sql_content = response['Body'].read().decode('utf-8')
        return sql_content
    except ClientError as e:
        logger.error(f"Error reading SQL file {key}: {e}")
        raise


def extract_table_name(sql_query):
    """
    Extract table name from a CREATE TABLE statement.
    
    Args:
        sql_query (str): SQL query containing CREATE TABLE statement
        
    Returns:
        str: Table name if found, None otherwise
    """
    try:
        # Remove comments
        sql_clean = re.sub(r'--.*?$', '', sql_query, flags=re.MULTILINE)
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
        
        # Pattern to match CREATE TABLE or CREATE EXTERNAL TABLE
        # Handles optional IF NOT EXISTS and both quoted and unquoted table names
        pattern = r'CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?'
        match = re.search(pattern, sql_clean, re.IGNORECASE | re.DOTALL)
        
        if match:
            table_name = match.group(1)
            logger.info(f"Extracted table name: {table_name}")
            return table_name
        else:
            logger.warning("Could not extract table name from SQL query")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting table name: {e}")
        return None


def check_table_exists(database, table_name):
    """
    Check if a table exists in AWS Glue Data Catalog.
    
    Args:
        database (str): Glue database name
        table_name (str): Table name to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        glue_client = get_glue_client()
        glue_client.get_table(DatabaseName=database, Name=table_name)
        logger.info(f"Table {database}.{table_name} exists")
        return True
    except glue_client.exceptions.EntityNotFoundException:
        logger.info(f"Table {database}.{table_name} does not exist")
        return False
    except ClientError as e:
        logger.error(f"Error checking if table exists: {e}")
        raise


def drop_table(table_name, database, output_location):
    """
    Drop a table using Athena DDL (does not delete S3 data).
    
    Args:
        table_name (str): Name of the table to drop
        database (str): Athena database name
        output_location (str): S3 location for query results
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Dropping table {database}.{table_name}")
        
        # Use DROP TABLE statement (does not delete S3 data for EXTERNAL tables)
        drop_query = f"DROP TABLE IF EXISTS {table_name}"
        
        # Execute the DROP TABLE query
        athena_client = get_athena_client()
        response = athena_client.start_query_execution(
            QueryString=drop_query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': output_location}
        )
        
        query_execution_id = response['QueryExecutionId']
        logger.info(f"Drop table query started with ID: {query_execution_id}")
        
        # Wait for query to complete
        status = wait_for_query_completion(query_execution_id)
        
        if status == 'SUCCEEDED':
            logger.info(f"Successfully dropped table {database}.{table_name}")
            return True
        else:
            logger.error(f"Failed to drop table {database}.{table_name}")
            return False
            
    except Exception as e:
        logger.error(f"Error dropping table {database}.{table_name}: {e}")
        # Don't raise the exception - we want to continue even if drop fails
        return False


def execute_athena_query(query, database, output_location):
    """
    Execute a SQL query in AWS Athena.
    
    Args:
        query (str): SQL query to execute
        database (str): Athena database name
        output_location (str): S3 location for query results
        
    Returns:
        dict: Query execution details including execution ID and status
    """
    try:
        logger.info(f"Starting Athena query execution in database: {database}")
        logger.info(f"Query: {query[:100]}...")  # Log first 100 chars
        
        # Start query execution
        athena_client = get_athena_client()
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': output_location}
        )
        
        query_execution_id = response['QueryExecutionId']
        logger.info(f"Query execution started with ID: {query_execution_id}")
        
        # Wait for query to complete
        status = wait_for_query_completion(query_execution_id)
        
        return {
            'execution_id': query_execution_id,
            'status': status
        }
        
    except ClientError as e:
        logger.error(f"Error executing Athena query: {e}")
        raise


def wait_for_query_completion(query_execution_id, max_attempts=60, delay=2):
    """
    Wait for an Athena query to complete.
    
    Args:
        query_execution_id (str): Athena query execution ID
        max_attempts (int): Maximum number of status check attempts
        delay (int): Delay in seconds between status checks
        
    Returns:
        str: Final query status
        
    Raises:
        Exception: If query fails or times out
    """
    attempts = 0
    
    while attempts < max_attempts:
        try:
            athena_client = get_athena_client()
            response = athena_client.get_query_execution(
                QueryExecutionId=query_execution_id
            )
            
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                logger.info(f"Query {query_execution_id} completed successfully")
                return status
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get(
                    'StateChangeReason', 'No reason provided'
                )
                error_msg = f"Query {query_execution_id} failed with status {status}: {reason}"
                logger.error(error_msg)
                raise Exception(error_msg)
            else:
                logger.info(f"Query {query_execution_id} status: {status}")
                time.sleep(delay)
                attempts += 1
                
        except ClientError as e:
            logger.error(f"Error checking query status: {e}")
            raise
    
    raise Exception(f"Query {query_execution_id} timed out after {max_attempts * delay} seconds")


def lambda_handler(event, context):
    """
    Main Lambda handler function.
    
    Expected environment variables:
        - SQL_BUCKET: S3 bucket containing SQL files
        - SQL_PREFIX: S3 prefix/folder for SQL files (default: 'sql_queries/')
        - ATHENA_DATABASE: Athena database name
        - ATHENA_OUTPUT_LOCATION: S3 location for Athena query results
        
    Args:
        event (dict): Lambda event object
        context (object): Lambda context object
        
    Returns:
        dict: Execution results with status code and details
    """
    try:
        # Get configuration from environment variables
        sql_bucket = os.environ.get('SQL_BUCKET')
        sql_prefix = os.environ.get('SQL_PREFIX', 'sql_queries/')
        athena_database = os.environ.get('ATHENA_DATABASE')
        athena_output_location = os.environ.get('ATHENA_OUTPUT_LOCATION')
        
        # Validate required configuration
        if not sql_bucket:
            raise ValueError("SQL_BUCKET environment variable is required")
        if not athena_database:
            raise ValueError("ATHENA_DATABASE environment variable is required")
        if not athena_output_location:
            raise ValueError("ATHENA_OUTPUT_LOCATION environment variable is required")
        
        logger.info("Starting SQL deployment process")
        logger.info(f"Configuration: bucket={sql_bucket}, prefix={sql_prefix}, "
                   f"database={athena_database}, output={athena_output_location}")
        
        # List all SQL files
        sql_files = list_sql_files(sql_bucket, sql_prefix)
        
        if not sql_files:
            logger.warning("No SQL files found")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No SQL files found',
                    'files_processed': 0
                })
            }
        
        # Execute each SQL file
        results = []
        for sql_file in sql_files:
            try:
                logger.info(f"Processing file: {sql_file}")
                
                # Read SQL content
                sql_query = read_sql_file(sql_bucket, sql_file)
                
                # Check if this is a CREATE TABLE statement
                table_name = extract_table_name(sql_query)
                
                if table_name:
                    # Check if table exists and drop it if it does
                    if check_table_exists(athena_database, table_name):
                        logger.info(f"Table {table_name} exists, dropping it before creation")
                        drop_table(table_name, athena_database, athena_output_location)
                
                # Execute query in Athena
                execution_result = execute_athena_query(
                    sql_query,
                    athena_database,
                    athena_output_location
                )
                
                results.append({
                    'file': sql_file,
                    'status': 'success',
                    'execution_id': execution_result['execution_id'],
                    'query_status': execution_result['status'],
                    'table_name': table_name
                })
                
                logger.info(f"Successfully processed {sql_file}")
                
            except Exception as e:
                logger.error(f"Failed to process {sql_file}: {str(e)}")
                results.append({
                    'file': sql_file,
                    'status': 'failed',
                    'error': str(e)
                })
                # Continue with next file instead of stopping
        
        # Prepare response
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful
        
        logger.info(f"SQL deployment completed: {successful} succeeded, {failed} failed")
        
        return {
            'statusCode': 200 if failed == 0 else 207,  # 207 Multi-Status for partial success
            'body': json.dumps({
                'message': 'SQL deployment completed',
                'total_files': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            }, indent=2)
        }
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Lambda execution failed',
                'error': str(e)
            })
        }
