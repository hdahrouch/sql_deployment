"""
AWS Glue Table Manager

This module provides functionality to manage AWS Glue tables including:
- Checking if a table exists
- Deleting a table if it exists
- Creating a new table

The main use case is to ensure that if a table exists in Glue,
it is deleted before creating it again.
"""

import logging
import boto3
from botocore.exceptions import ClientError

# Get logger for this module (application should configure logging)
logger = logging.getLogger(__name__)


class GlueTableManager:
    """Manager class for AWS Glue table operations."""
    
    def __init__(self, database_name, region_name='us-east-1'):
        """
        Initialize the Glue Table Manager.
        
        Args:
            database_name (str): The name of the Glue database
            region_name (str): AWS region name (default: us-east-1)
        """
        self.database_name = database_name
        self.glue_client = boto3.client('glue', region_name=region_name)
        logger.info(f"Initialized GlueTableManager for database: {database_name}")
    
    def table_exists(self, table_name):
        """
        Check if a table exists in the Glue database.
        
        Args:
            table_name (str): The name of the table to check
            
        Returns:
            bool: True if the table exists, False otherwise
        """
        try:
            self.glue_client.get_table(
                DatabaseName=self.database_name,
                Name=table_name
            )
            logger.info(f"Table '{table_name}' exists in database '{self.database_name}'")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.info(f"Table '{table_name}' does not exist in database '{self.database_name}'")
                return False
            else:
                logger.error(f"Error checking if table exists: {e}")
                raise
    
    def delete_table(self, table_name):
        """
        Delete a table from the Glue database.
        
        Args:
            table_name (str): The name of the table to delete
            
        Returns:
            bool: True if the table was deleted, False if it didn't exist
        """
        try:
            self.glue_client.delete_table(
                DatabaseName=self.database_name,
                Name=table_name
            )
            logger.info(f"Successfully deleted table '{table_name}' from database '{self.database_name}'")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Table '{table_name}' not found, nothing to delete")
                return False
            else:
                logger.error(f"Error deleting table: {e}")
                raise
    
    def delete_table_if_exists(self, table_name):
        """
        Delete a table if it exists in the Glue database.
        
        This method calls delete_table directly, which handles EntityNotFoundException
        gracefully, avoiding an extra API call to check existence.
        
        Args:
            table_name (str): The name of the table to delete
            
        Returns:
            bool: True if the table was deleted, False if it didn't exist
        """
        return self.delete_table(table_name)
    
    def create_table(self, table_name, table_input):
        """
        Create a new table in the Glue database.
        
        Args:
            table_name (str): The name of the table to create
            table_input (dict): The table definition including columns, storage descriptor, etc.
            
        Returns:
            dict: The response from the create_table API call
        """
        try:
            response = self.glue_client.create_table(
                DatabaseName=self.database_name,
                TableInput=table_input
            )
            logger.info(f"Successfully created table '{table_name}' in database '{self.database_name}'")
            return response
        except ClientError as e:
            logger.error(f"Error creating table: {e}")
            raise
    
    def recreate_table(self, table_name, table_input):
        """
        Delete a table if it exists and create it again.
        
        This is the main method that implements the requirement:
        "if table exists in Glue, the table must be deleted before creating it again"
        
        This method calls delete_table directly without checking existence first,
        as delete_table handles EntityNotFoundException gracefully, reducing API calls.
        
        Args:
            table_name (str): The name of the table to recreate
            table_input (dict): The table definition including columns, storage descriptor, etc.
            
        Returns:
            dict: The response from the create_table API call
        """
        # Delete the table if it exists (handles EntityNotFoundException gracefully)
        was_deleted = self.delete_table(table_name)
        if was_deleted:
            logger.info(f"Table '{table_name}' existed and was deleted before recreation")
        
        # Create the table
        logger.info(f"Creating table '{table_name}'...")
        return self.create_table(table_name, table_input)


def main():
    """
    Example usage of the GlueTableManager.
    """
    # Example configuration
    database_name = "my_database"
    table_name = "my_table"
    
    # Initialize the manager
    manager = GlueTableManager(database_name)
    
    # Example table definition
    table_input = {
        'Name': table_name,
        'StorageDescriptor': {
            'Columns': [
                {'Name': 'id', 'Type': 'int'},
                {'Name': 'name', 'Type': 'string'},
                {'Name': 'created_at', 'Type': 'timestamp'}
            ],
            'Location': 's3://my-bucket/my-table/',
            'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
            'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
            'SerdeInfo': {
                'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
            }
        }
    }
    
    # Recreate the table (delete if exists, then create)
    manager.recreate_table(table_name, table_input)


if __name__ == "__main__":
    main()
