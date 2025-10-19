"""
Example usage of the AWS Glue Table Manager.

This script demonstrates how to use the GlueTableManager to:
1. Check if a table exists
2. Delete a table if it exists
3. Create a new table
4. Recreate a table (delete if exists, then create)
"""

from glue_table_manager import GlueTableManager


def example_basic_usage():
    """Example of basic usage patterns."""
    # Initialize the manager with your database name
    database_name = "my_glue_database"
    region_name = "us-east-1"  # Change to your AWS region
    
    manager = GlueTableManager(database_name, region_name)
    
    # Example 1: Check if a table exists
    table_name = "example_table"
    if manager.table_exists(table_name):
        print(f"Table {table_name} exists")
    else:
        print(f"Table {table_name} does not exist")
    
    # Example 2: Delete a table if it exists
    manager.delete_table_if_exists(table_name)
    
    # Example 3: Create a table
    table_input = {
        'Name': table_name,
        'StorageDescriptor': {
            'Columns': [
                {'Name': 'id', 'Type': 'int', 'Comment': 'Unique identifier'},
                {'Name': 'name', 'Type': 'string', 'Comment': 'User name'},
                {'Name': 'email', 'Type': 'string', 'Comment': 'User email'},
                {'Name': 'created_at', 'Type': 'timestamp', 'Comment': 'Creation timestamp'}
            ],
            'Location': 's3://my-bucket/example-table/',
            'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
            'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
            'SerdeInfo': {
                'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                'Parameters': {
                    'field.delim': ',',
                    'serialization.format': ','
                }
            }
        },
        'TableType': 'EXTERNAL_TABLE'
    }
    
    manager.create_table(table_name, table_input)


def example_recreate_table():
    """
    Example of the main use case: recreate a table.
    
    This automatically handles the case where the table exists:
    - If the table exists, it is deleted first
    - Then the table is created with the new definition
    """
    database_name = "my_glue_database"
    region_name = "us-east-1"
    
    manager = GlueTableManager(database_name, region_name)
    
    table_name = "sales_data"
    
    # Define the table schema
    table_input = {
        'Name': table_name,
        'Description': 'Sales transaction data',
        'StorageDescriptor': {
            'Columns': [
                {'Name': 'transaction_id', 'Type': 'bigint', 'Comment': 'Transaction ID'},
                {'Name': 'customer_id', 'Type': 'bigint', 'Comment': 'Customer ID'},
                {'Name': 'product_id', 'Type': 'bigint', 'Comment': 'Product ID'},
                {'Name': 'amount', 'Type': 'decimal(10,2)', 'Comment': 'Transaction amount'},
                {'Name': 'transaction_date', 'Type': 'date', 'Comment': 'Transaction date'}
            ],
            'Location': 's3://my-data-bucket/sales/',
            'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
            'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
            'SerdeInfo': {
                'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                'Parameters': {
                    'field.delim': '|',
                    'serialization.format': '|'
                }
            },
            'Compressed': False,
            'StoredAsSubDirectories': False
        },
        'PartitionKeys': [
            {'Name': 'year', 'Type': 'string', 'Comment': 'Year partition'},
            {'Name': 'month', 'Type': 'string', 'Comment': 'Month partition'}
        ],
        'TableType': 'EXTERNAL_TABLE'
    }
    
    # This will delete the table if it exists, then create it
    manager.recreate_table(table_name, table_input)
    print(f"Table {table_name} has been successfully recreated")


def example_with_parquet_format():
    """Example of creating a table with Parquet format."""
    database_name = "my_glue_database"
    region_name = "us-east-1"
    
    manager = GlueTableManager(database_name, region_name)
    
    table_name = "parquet_table"
    
    table_input = {
        'Name': table_name,
        'Description': 'Table stored in Parquet format',
        'StorageDescriptor': {
            'Columns': [
                {'Name': 'id', 'Type': 'bigint'},
                {'Name': 'data', 'Type': 'string'},
                {'Name': 'timestamp', 'Type': 'timestamp'}
            ],
            'Location': 's3://my-bucket/parquet-data/',
            'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
            'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
            'SerdeInfo': {
                'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe',
                'Parameters': {
                    'serialization.format': '1'
                }
            },
            'Compressed': False
        },
        'TableType': 'EXTERNAL_TABLE'
    }
    
    # Recreate the table (delete if exists, then create)
    manager.recreate_table(table_name, table_input)
    print(f"Parquet table {table_name} has been successfully recreated")


if __name__ == "__main__":
    print("AWS Glue Table Manager - Example Usage")
    print("=" * 50)
    print("\nNote: Make sure you have AWS credentials configured before running these examples.")
    print("You will need to update the database_name, region_name, and S3 locations.\n")
    
    # Uncomment the example you want to run:
    # example_basic_usage()
    # example_recreate_table()
    # example_with_parquet_format()
    
    print("\nExamples are provided but commented out.")
    print("Please update the configuration values and uncomment the example you want to run.")
