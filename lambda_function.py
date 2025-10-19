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
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
athena_client = boto3.client('athena')


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
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        sql_content = response['Body'].read().decode('utf-8')
        return sql_content
    except ClientError as e:
        logger.error(f"Error reading SQL file {key}: {e}")
        raise


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
                    'query_status': execution_result['status']
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
