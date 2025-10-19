#!/bin/bash

# AWS Lambda Deployment Script for SQL Deployment to Athena
# This script packages and deploys the Lambda function to AWS

set -e

# Configuration
FUNCTION_NAME="sql-deployment-athena"
RUNTIME="python3.9"
HANDLER="lambda_function.lambda_handler"
TIMEOUT=900
MEMORY_SIZE=512

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AWS Lambda SQL Deployment - Deployment Script${NC}"
echo "=============================================="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check if configuration file exists
if [ ! -f "config.env" ]; then
    echo -e "${YELLOW}Warning: config.env not found. Using config.env.template${NC}"
    if [ ! -f "config.env.template" ]; then
        echo -e "${RED}Error: config.env.template not found${NC}"
        exit 1
    fi
    cp config.env.template config.env
    echo -e "${YELLOW}Please edit config.env with your settings and run again${NC}"
    exit 1
fi

# Load configuration
source config.env

# Validate required environment variables
if [ -z "$SQL_BUCKET" ] || [ -z "$ATHENA_DATABASE" ] || [ -z "$ATHENA_OUTPUT_LOCATION" ]; then
    echo -e "${RED}Error: Required environment variables not set in config.env${NC}"
    echo "Required: SQL_BUCKET, ATHENA_DATABASE, ATHENA_OUTPUT_LOCATION"
    exit 1
fi

# Check if IAM role is provided
if [ -z "$LAMBDA_ROLE_ARN" ]; then
    echo -e "${YELLOW}Warning: LAMBDA_ROLE_ARN not set in config.env${NC}"
    echo "Please provide the Lambda execution role ARN:"
    read -r LAMBDA_ROLE_ARN
fi

echo "Configuration:"
echo "  Function Name: $FUNCTION_NAME"
echo "  SQL Bucket: $SQL_BUCKET"
echo "  SQL Prefix: ${SQL_PREFIX:-sql_queries/}"
echo "  Athena Database: $ATHENA_DATABASE"
echo "  Output Location: $ATHENA_OUTPUT_LOCATION"
echo ""

# Create package directory
echo "Creating deployment package..."
rm -rf package lambda_deployment.zip
mkdir -p package

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t package/ --quiet

# Copy Lambda function
echo "Copying Lambda function..."
cp lambda_function.py package/

# Create deployment package
echo "Creating ZIP file..."
cd package
zip -r ../lambda_deployment.zip . > /dev/null
cd ..

echo -e "${GREEN}Deployment package created: lambda_deployment.zip${NC}"
echo ""

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME 2>/dev/null; then
    echo "Lambda function exists. Updating..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_deployment.zip
    
    echo "Waiting for update to complete..."
    aws lambda wait function-updated --function-name $FUNCTION_NAME
    
    # Update configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --environment Variables="{
            SQL_BUCKET=$SQL_BUCKET,
            SQL_PREFIX=${SQL_PREFIX:-sql_queries/},
            ATHENA_DATABASE=$ATHENA_DATABASE,
            ATHENA_OUTPUT_LOCATION=$ATHENA_OUTPUT_LOCATION
        }"
    
    echo -e "${GREEN}Lambda function updated successfully!${NC}"
else
    echo "Lambda function does not exist. Creating..."
    
    # Create function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $LAMBDA_ROLE_ARN \
        --handler $HANDLER \
        --zip-file fileb://lambda_deployment.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --environment Variables="{
            SQL_BUCKET=$SQL_BUCKET,
            SQL_PREFIX=${SQL_PREFIX:-sql_queries/},
            ATHENA_DATABASE=$ATHENA_DATABASE,
            ATHENA_OUTPUT_LOCATION=$ATHENA_OUTPUT_LOCATION
        }"
    
    echo -e "${GREEN}Lambda function created successfully!${NC}"
fi

echo ""
echo "Next steps:"
echo "1. Upload your SQL files to s3://$SQL_BUCKET/${SQL_PREFIX:-sql_queries/}"
echo "2. Test the function: aws lambda invoke --function-name $FUNCTION_NAME response.json"
echo "3. View logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
