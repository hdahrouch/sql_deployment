# Quick Start Guide

This guide will help you deploy the AWS Lambda SQL runner to Athena in minutes.

## Prerequisites

- AWS Account
- AWS CLI configured with credentials
- Python 3.9+
- An S3 bucket for SQL files
- An S3 bucket for Athena query results

## Step-by-Step Setup

### 1. Create IAM Role for Lambda

Create an IAM role with the policy from `iam-policy.json`:

```bash
# Create trust policy for Lambda
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name lambda-sql-deployment-role \
  --assume-role-policy-document file://trust-policy.json

# Attach the policy (update iam-policy.json with your bucket names first)
aws iam put-role-policy \
  --role-name lambda-sql-deployment-role \
  --policy-name lambda-sql-deployment-policy \
  --policy-document file://iam-policy.json

# Get the role ARN
aws iam get-role --role-name lambda-sql-deployment-role --query 'Role.Arn'
```

### 2. Configure Environment

Copy the configuration template and edit it:

```bash
cp config.env.template config.env
```

Edit `config.env` and set your values:

```bash
SQL_BUCKET=my-sql-queries-bucket
SQL_PREFIX=sql_queries/
ATHENA_DATABASE=my_database
ATHENA_OUTPUT_LOCATION=s3://my-athena-results-bucket/query-results/
LAMBDA_ROLE_ARN=arn:aws:iam::123456789012:role/lambda-sql-deployment-role
```

### 3. Upload SQL Files to S3

Upload your SQL files to the S3 bucket:

```bash
# Create the bucket if it doesn't exist
aws s3 mb s3://my-sql-queries-bucket

# Upload example SQL files
aws s3 cp example_sql_queries/ s3://my-sql-queries-bucket/sql_queries/ --recursive
```

### 4. Create Athena Results Bucket

```bash
# Create results bucket if it doesn't exist
aws s3 mb s3://my-athena-results-bucket
```

### 5. Deploy the Lambda Function

Run the deployment script:

```bash
./deploy.sh
```

Or deploy manually:

```bash
# Install dependencies and create package
pip install -r requirements.txt -t package/
cp lambda_function.py package/
cd package && zip -r ../lambda_deployment.zip . && cd ..

# Deploy (source your config.env first)
source config.env
aws lambda create-function \
  --function-name sql-deployment-athena \
  --runtime python3.9 \
  --role $LAMBDA_ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 900 \
  --memory-size 512 \
  --environment Variables="{
    SQL_BUCKET=$SQL_BUCKET,
    SQL_PREFIX=$SQL_PREFIX,
    ATHENA_DATABASE=$ATHENA_DATABASE,
    ATHENA_OUTPUT_LOCATION=$ATHENA_OUTPUT_LOCATION
  }"
```

### 6. Test the Lambda Function

Invoke the function:

```bash
aws lambda invoke \
  --function-name sql-deployment-athena \
  --payload '{}' \
  response.json

# View the response
cat response.json | python3 -m json.tool
```

### 7. View Logs

```bash
# Tail the logs in real-time
aws logs tail /aws/lambda/sql-deployment-athena --follow

# Or view recent logs
aws logs tail /aws/lambda/sql-deployment-athena --since 10m
```

## Verification

After deployment, verify that:

1. **Lambda function is created**: Check AWS Lambda Console
2. **Tables are created in Athena**: Check AWS Athena Console > Data > Tables
3. **Logs are generated**: Check CloudWatch Logs

```bash
# List tables in your Athena database
aws athena start-query-execution \
  --query-string "SHOW TABLES" \
  --query-execution-context Database=$ATHENA_DATABASE \
  --result-configuration OutputLocation=$ATHENA_OUTPUT_LOCATION
```

## Troubleshooting

### Issue: Lambda times out

**Solution**: Increase timeout in Lambda configuration (max 15 minutes):

```bash
aws lambda update-function-configuration \
  --function-name sql-deployment-athena \
  --timeout 900
```

### Issue: Permission denied errors

**Solution**: Verify IAM role has all required permissions. Check CloudWatch logs for specific permission errors.

### Issue: No SQL files found

**Solution**: 
- Verify S3 bucket name and prefix in environment variables
- Check that SQL files have `.sql` extension
- Ensure Lambda has `s3:ListBucket` and `s3:GetObject` permissions

### Issue: Athena query fails

**Solution**:
- Test the SQL query manually in Athena Console
- Check if the database exists
- Verify data bucket locations in CREATE TABLE statements
- Review query error details in CloudWatch logs

## Next Steps

1. **Schedule Regular Deployments**: Set up CloudWatch Events to trigger the Lambda on a schedule
2. **Add Monitoring**: Create CloudWatch alarms for failures
3. **CI/CD Integration**: Integrate with your deployment pipeline
4. **Version Control SQL**: Keep SQL files in version control and sync to S3 automatically

## Support

For issues or questions, refer to the main [README.md](README.md) or check CloudWatch Logs for detailed error messages.
