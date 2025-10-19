# SQL Deployment - AWS Glue Table Manager

A Python utility for managing AWS Glue tables with automatic recreation capabilities. This tool ensures that if a table exists in AWS Glue, it is deleted before creating it again.

## Features

- **Check if table exists**: Verify whether a table exists in a Glue database
- **Delete table if exists**: Safely delete a table if it exists
- **Create table**: Create a new Glue table with custom schema
- **Recreate table**: Delete and recreate a table in one operation (main feature)

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from glue_table_manager import GlueTableManager

# Initialize the manager
manager = GlueTableManager(database_name="my_database", region_name="us-east-1")

# Define your table schema
table_input = {
    'Name': 'my_table',
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

# Recreate the table (deletes if exists, then creates)
manager.recreate_table('my_table', table_input)
```

### Available Methods

#### `table_exists(table_name)`
Check if a table exists in the Glue database.

```python
if manager.table_exists('my_table'):
    print("Table exists")
```

#### `delete_table(table_name)`
Delete a table from the Glue database.

```python
manager.delete_table('my_table')
```

#### `delete_table_if_exists(table_name)`
Delete a table only if it exists.

```python
manager.delete_table_if_exists('my_table')
```

#### `create_table(table_name, table_input)`
Create a new table in the Glue database.

```python
manager.create_table('my_table', table_input)
```

#### `recreate_table(table_name, table_input)`
Delete the table if it exists and create it again. This is the main method that implements the requirement.

```python
manager.recreate_table('my_table', table_input)
```

## AWS Credentials

This tool uses boto3 to interact with AWS Glue. Ensure you have AWS credentials configured either through:
- AWS credentials file (`~/.aws/credentials`)
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- IAM role (when running on EC2 or ECS)

Required IAM permissions:
- `glue:GetTable`
- `glue:DeleteTable`
- `glue:CreateTable`

## Running Tests

Run the unit tests using:

```bash
python -m pytest test_glue_table_manager.py
```

Or using unittest:

```bash
python -m unittest test_glue_table_manager.py
```

## Requirements

- Python 3.7+
- boto3 >= 1.28.0
- botocore >= 1.31.0

## License

This project is open source and available under the MIT License.