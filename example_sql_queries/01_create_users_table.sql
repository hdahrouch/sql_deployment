-- Example SQL query to create a users table in Athena
-- This demonstrates the CREATE TABLE syntax for AWS Athena

CREATE EXTERNAL TABLE IF NOT EXISTS users (
    user_id BIGINT,
    username STRING,
    email STRING,
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN
)
COMMENT 'Users table with basic user information'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://your-data-bucket/users/'
TBLPROPERTIES (
    'skip.header.line.count'='1',
    'serialization.null.format'=''
);
