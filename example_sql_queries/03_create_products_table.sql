-- Example SQL query to create a products table in Athena
-- This demonstrates CREATE TABLE with Parquet format

CREATE EXTERNAL TABLE IF NOT EXISTS products (
    product_id BIGINT,
    product_name STRING,
    category STRING,
    price DECIMAL(10, 2),
    stock_quantity INT,
    description STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
COMMENT 'Products table with catalog information'
STORED AS PARQUET
LOCATION 's3://your-data-bucket/products/'
TBLPROPERTIES (
    'parquet.compression'='SNAPPY'
);
