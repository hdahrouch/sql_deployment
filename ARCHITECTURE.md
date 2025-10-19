# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS Architecture                            │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   S3 Bucket      │
│ (SQL Files)      │
│                  │
│ sql_queries/     │
│ ├── 01_*.sql     │
│ ├── 02_*.sql     │
│ └── 03_*.sql     │
└────────┬─────────┘
         │
         │ 1. List & Read
         │    SQL Files
         │
         ▼
┌──────────────────┐
│  AWS Lambda      │
│  Function        │
│                  │
│  Handler:        │
│  lambda_handler()│
│                  │
│  Functions:      │
│  • list_sql_     │
│    files()       │
│  • read_sql_     │
│    file()        │
│  • execute_      │
│    athena_query()│
└────────┬─────────┘
         │
         │ 2. Execute Queries
         │    One by One
         │
         ▼
┌──────────────────┐
│   AWS Athena     │
│                  │
│  Database:       │
│  - Creates       │
│    Tables        │
│  - Executes DDL  │
└────────┬─────────┘
         │
         │ 3. Store Results
         │
         ▼
┌──────────────────┐
│   S3 Bucket      │
│ (Query Results)  │
│                  │
│ query-results/   │
└──────────────────┘
         │
         │ 4. Log Events
         │
         ▼
┌──────────────────┐
│  CloudWatch      │
│  Logs            │
│                  │
│  /aws/lambda/    │
│  sql-deployment  │
└──────────────────┘
```

## Component Details

### 1. S3 Bucket (SQL Files)
- **Purpose**: Store SQL query files to be executed
- **Structure**: Organized by prefix/folder (default: `sql_queries/`)
- **File Format**: `.sql` files containing CREATE TABLE statements
- **Execution Order**: Alphabetical (use numbered prefixes like `01_`, `02_`)
- **Permissions Required**: `s3:ListBucket`, `s3:GetObject`

### 2. AWS Lambda Function
- **Runtime**: Python 3.9+
- **Timeout**: 900 seconds (15 minutes)
- **Memory**: 512 MB (configurable)
- **Handler**: `lambda_function.lambda_handler`
- **Dependencies**: `boto3`, `botocore`

#### Key Functions:

##### `lambda_handler(event, context)`
- Main entry point
- Reads configuration from environment variables
- Orchestrates the entire workflow
- Returns execution results

##### `list_sql_files(bucket_name, prefix)`
- Lists all `.sql` files from S3
- Sorts files alphabetically
- Returns list of S3 object keys

##### `read_sql_file(bucket_name, key)`
- Reads SQL content from S3
- Decodes UTF-8 content
- Returns SQL query string

##### `execute_athena_query(query, database, output_location)`
- Starts Athena query execution
- Waits for completion
- Returns execution ID and status

##### `wait_for_query_completion(query_execution_id)`
- Polls query status
- Handles success/failure states
- Raises exception on failure or timeout

### 3. AWS Athena
- **Purpose**: Execute SQL DDL statements
- **Target**: Glue Data Catalog
- **Operations**: CREATE TABLE, CREATE EXTERNAL TABLE
- **Query Results**: Stored in S3 output location
- **Permissions Required**: 
  - `athena:StartQueryExecution`
  - `athena:GetQueryExecution`
  - `glue:CreateTable`
  - `glue:UpdateTable`

### 4. S3 Bucket (Query Results)
- **Purpose**: Store Athena query results and metadata
- **Structure**: Organized by execution ID
- **Permissions Required**: `s3:PutObject`, `s3:GetObject`

### 5. CloudWatch Logs
- **Purpose**: Monitor and debug Lambda execution
- **Log Group**: `/aws/lambda/sql-deployment-athena`
- **Log Level**: INFO
- **Content**: 
  - SQL file names processed
  - Query execution IDs
  - Success/failure status
  - Error messages

## Data Flow

### Sequential Execution Flow:

1. **Initialization**
   - Lambda function is triggered (manual, scheduled, or event-based)
   - Environment variables are validated
   - AWS clients are initialized

2. **Discovery Phase**
   - List all `.sql` files from S3 bucket
   - Sort files alphabetically
   - Log count of files found

3. **Execution Phase** (for each SQL file)
   - Read SQL content from S3
   - Start Athena query execution
   - Wait for query to complete (polling every 2 seconds)
   - Log success or failure
   - Continue to next file (even on failure)

4. **Completion Phase**
   - Aggregate results
   - Count successful and failed queries
   - Return summary response
   - Log final statistics

### Error Handling:

- **File-Level Errors**: Logged and tracked, execution continues
- **System-Level Errors**: Lambda returns 500 error with details
- **Query Failures**: Captured with Athena error messages
- **Timeouts**: Configurable max attempts (default: 60 × 2s = 2 min per query)

## Security Architecture

### IAM Permissions:

```
Lambda Execution Role
├── S3 Read (SQL Bucket)
│   ├── s3:ListBucket
│   └── s3:GetObject
├── S3 Write (Results Bucket)
│   ├── s3:PutObject
│   └── s3:GetObject
├── Athena Execution
│   ├── athena:StartQueryExecution
│   ├── athena:GetQueryExecution
│   └── athena:GetQueryResults
├── Glue Data Catalog
│   ├── glue:GetDatabase
│   ├── glue:GetTable
│   ├── glue:CreateTable
│   └── glue:UpdateTable
└── CloudWatch Logs
    ├── logs:CreateLogGroup
    ├── logs:CreateLogStream
    └── logs:PutLogEvents
```

### Network Security:
- Lambda runs in AWS managed VPC (default)
- Can be configured to run in customer VPC if needed
- No public endpoints exposed
- All communication via AWS API endpoints

### Data Security:
- SQL files and results can be encrypted at rest (S3 encryption)
- Data in transit uses TLS
- No credentials stored in code
- IAM-based authentication and authorization

## Scalability Considerations

### Current Limitations:
- Sequential execution (one query at a time)
- 15-minute Lambda timeout limit
- Single Lambda invocation per deployment

### Scaling Options:
1. **Parallel Execution**: Modify to use Step Functions for parallel execution
2. **Batch Processing**: Process files in batches across multiple Lambda invocations
3. **Event-Driven**: Trigger Lambda per SQL file upload
4. **Queue-Based**: Use SQS for reliable, distributed processing

## Monitoring and Observability

### Metrics to Track:
- Number of SQL files processed
- Success/failure rates
- Query execution times
- Lambda duration and memory usage
- Error rates and types

### CloudWatch Dashboard:
- Lambda invocations
- Error count
- Duration
- Throttles
- Concurrent executions

### Alarms:
- Lambda errors > threshold
- Lambda duration > threshold
- Failed query count > threshold

## Cost Optimization

### AWS Service Costs:
- **Lambda**: Charged per request and execution time
- **Athena**: Charged per TB of data scanned
- **S3**: Storage and request costs
- **CloudWatch**: Log storage and API requests

### Cost Reduction Tips:
1. Use partitioning in Athena tables
2. Use columnar formats (Parquet, ORC)
3. Minimize query execution time
4. Clean up old query results
5. Adjust Lambda memory appropriately

## Deployment Options

### 1. Manual Deployment
- Use AWS Console
- Upload ZIP file
- Configure manually

### 2. AWS CLI Deployment
- Use provided `deploy.sh` script
- Automated configuration
- Version control friendly

### 3. Infrastructure as Code
- CloudFormation template
- Terraform configuration
- AWS SAM template

### 4. CI/CD Integration
- GitHub Actions
- AWS CodePipeline
- Jenkins pipeline
