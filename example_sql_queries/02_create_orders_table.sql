-- Example SQL query to create an orders table in Athena
-- This demonstrates CREATE TABLE with PARTITIONED BY clause

CREATE EXTERNAL TABLE IF NOT EXISTS orders (
    order_id BIGINT,
    user_id BIGINT,
    product_id BIGINT,
    quantity INT,
    total_amount DECIMAL(10, 2),
    order_status STRING,
    created_at TIMESTAMP
)
COMMENT 'Orders table with transaction information'
PARTITIONED BY (order_date STRING)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://your-data-bucket/orders/'
TBLPROPERTIES (
    'skip.header.line.count'='1',
    'serialization.null.format'=''
);
