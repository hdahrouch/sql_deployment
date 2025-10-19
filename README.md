# SQL Deployment to AWS Athena

This project contains an AWS Lambda function that automatically lists SQL query files from an S3 bucket and executes them one by one in AWS Athena. It's designed to handle CREATE TABLE statements and other DDL operations for database schema deployment.

## Features

- **Automatic SQL File Discovery**: Lists all `.sql` files from a specified S3 bucket and prefix
- **Sequential Execution**: Executes SQL queries one by one in alphabetical order
- **Athena Integration**: Runs queries directly in AWS Athena
- **Error Handling**: Continues execution even if individual queries fail
- **Detailed Logging**: Comprehensive logging for monitoring and debugging
- **Status Reporting**: Returns detailed results for each executed query

## Architecture

```
S3 Bucket (SQL Files) → Lambda Function → AWS Athena → Tables Created
```

## Prerequisites

- AWS Account with appropriate permissions
- S3 bucket for SQL query files
- S3 bucket for Athena query results
- Athena database (existing or will be created)
- IAM role for Lambda with necessary permissions

## Required IAM Permissions

The Lambda function requires the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-sql-bucket/*",
        "arn:aws:s3:::your-sql-bucket"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::your-athena-results-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:CreateTable",
        "glue:UpdateTable",
        "glue:DeleteTable"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Setup Instructions

### 1. Prepare Your SQL Files

Place your SQL files in an S3 bucket. Files will be executed in alphabetical order, so consider using numbered prefixes:

```
s3://your-bucket/sql_queries/
├── 01_create_users_table.sql
├── 02_create_orders_table.sql
└── 03_create_products_table.sql
```

### 2. Package the Lambda Function

```bash
# Install dependencies
pip install -r requirements.txt -t package/

# Copy Lambda function to package directory
cp lambda_function.py package/

# Create deployment package
cd package
zip -r ../lambda_deployment.zip .
cd ..
```

### 3. Create the Lambda Function

Using AWS CLI:

```bash
aws lambda create-function \
  --function-name sql-deployment-athena \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-athena-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 900 \
  --memory-size 512 \
  --environment Variables="{
    SQL_BUCKET=your-sql-bucket,
    SQL_PREFIX=sql_queries/,
    ATHENA_DATABASE=your_database,
    ATHENA_OUTPUT_LOCATION=s3://your-athena-results-bucket/query-results/
  }"
```

Or using the AWS Console:
1. Go to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. Configure function name and runtime (Python 3.9 or later)
5. Upload the `lambda_deployment.zip` file
6. Configure environment variables (see below)
7. Set timeout to at least 15 minutes (900 seconds)

### 4. Configure Environment Variables

Set the following environment variables in your Lambda function:

| Variable | Description | Example |
|----------|-------------|---------|
| `SQL_BUCKET` | S3 bucket containing SQL files | `my-sql-queries-bucket` |
| `SQL_PREFIX` | Prefix/folder for SQL files | `sql_queries/` |
| `ATHENA_DATABASE` | Target Athena database name | `my_database` |
| `ATHENA_OUTPUT_LOCATION` | S3 location for query results | `s3://my-results-bucket/athena/` |

## Usage

### Manual Invocation

Invoke the Lambda function manually through the AWS Console or AWS CLI:

```bash
aws lambda invoke \
  --function-name sql-deployment-athena \
  --payload '{}' \
  response.json

cat response.json
```

### Scheduled Execution

Set up a CloudWatch Events rule to trigger the Lambda function on a schedule:

```bash
# Create a rule that runs every day at 2 AM UTC
aws events put-rule \
  --name daily-sql-deployment \
  --schedule-expression "cron(0 2 * * ? *)"

# Add Lambda as target
aws events put-targets \
  --rule daily-sql-deployment \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:sql-deployment-athena"
```

### Trigger on S3 Upload

Configure S3 event notification to trigger the Lambda when new SQL files are uploaded:

```bash
aws s3api put-bucket-notification-configuration \
  --bucket your-sql-bucket \
  --notification-configuration file://s3-notification.json
```

## Response Format

The Lambda function returns a JSON response with execution details:

```json
{
  "statusCode": 200,
  "body": {
    "message": "SQL deployment completed",
    "total_files": 3,
    "successful": 3,
    "failed": 0,
    "results": [
      {
        "file": "sql_queries/01_create_users_table.sql",
        "status": "success",
        "execution_id": "abc123...",
        "query_status": "SUCCEEDED"
      },
      {
        "file": "sql_queries/02_create_orders_table.sql",
        "status": "success",
        "execution_id": "def456...",
        "query_status": "SUCCEEDED"
      }
    ]
  }
}
```

## Example SQL Files

The `example_sql_queries/` directory contains sample CREATE TABLE statements:

- `01_create_users_table.sql` - Basic table with CSV format
- `02_create_orders_table.sql` - Partitioned table
- `03_create_products_table.sql` - Table with Parquet format

## SQL Query Best Practices

1. **Use IF NOT EXISTS**: Always use `CREATE TABLE IF NOT EXISTS` to make queries idempotent
2. **Number Your Files**: Use numeric prefixes to control execution order
3. **Test Queries**: Test queries in Athena console before deploying
4. **External Tables**: Use `CREATE EXTERNAL TABLE` for data in S3
5. **Specify Format**: Always specify the data format (CSV, Parquet, JSON, etc.)

## Monitoring and Debugging

### CloudWatch Logs

View execution logs in CloudWatch Logs:
- Log group: `/aws/lambda/sql-deployment-athena`
- Check for errors, query statuses, and execution times

### Athena Query History

Check the Athena console for query history and execution details:
1. Go to AWS Athena Console
2. Click "Recent queries"
3. View execution details, errors, and results

## Troubleshooting

### Common Issues

**Issue**: "SQL_BUCKET environment variable is required"
- **Solution**: Ensure all required environment variables are configured

**Issue**: Query fails with permission errors
- **Solution**: Verify IAM role has necessary permissions for S3, Athena, and Glue

**Issue**: Query times out
- **Solution**: Increase Lambda timeout (max 15 minutes) or optimize query

**Issue**: No SQL files found
- **Solution**: Verify S3 bucket name, prefix, and that .sql files exist

## Development

### Local Testing

You can test the Lambda function locally using the AWS SAM CLI or by mocking the AWS services.

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest moto boto3

# Run tests (if test suite is added)
pytest tests/
```

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Open an issue in the repository