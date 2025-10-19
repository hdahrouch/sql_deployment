#!/usr/bin/env python3
"""
Simple validation script to check the Lambda function structure.
This script validates that all required functions are defined and importable.
"""

import sys
import ast
import os


def validate_lambda_function():
    """Validate the Lambda function structure."""
    print("Validating Lambda function structure...")
    
    # Read the Lambda function file
    with open('lambda_function.py', 'r') as f:
        content = f.read()
    
    # Parse the AST
    try:
        tree = ast.parse(content)
        print("✓ Python syntax is valid")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        return False
    
    # Check for required functions
    required_functions = [
        'lambda_handler',
        'list_sql_files',
        'read_sql_file',
        'execute_athena_query',
        'wait_for_query_completion'
    ]
    
    defined_functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined_functions.append(node.name)
    
    missing_functions = set(required_functions) - set(defined_functions)
    if missing_functions:
        print(f"✗ Missing required functions: {missing_functions}")
        return False
    
    for func in required_functions:
        print(f"✓ Function '{func}' is defined")
    
    # Check for required imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    
    required_imports = ['os', 'json', 'logging', 'time', 'boto3']
    missing_imports = set(required_imports) - set(imports)
    if missing_imports:
        print(f"✗ Missing required imports: {missing_imports}")
        return False
    
    for imp in required_imports:
        print(f"✓ Import '{imp}' found")
    
    print("\n✓ All validations passed!")
    return True


def check_files_exist():
    """Check that all required files exist."""
    print("\nChecking for required files...")
    
    required_files = [
        'lambda_function.py',
        'requirements.txt',
        'README.md',
        'config.env.template',
        'deploy.sh',
        'iam-policy.json'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} is missing")
            all_exist = False
    
    return all_exist


def check_example_sql_files():
    """Check that example SQL files exist."""
    print("\nChecking for example SQL files...")
    
    example_dir = 'example_sql_queries'
    if not os.path.exists(example_dir):
        print(f"✗ {example_dir} directory is missing")
        return False
    
    sql_files = [f for f in os.listdir(example_dir) if f.endswith('.sql')]
    if len(sql_files) == 0:
        print(f"✗ No SQL files found in {example_dir}")
        return False
    
    print(f"✓ Found {len(sql_files)} example SQL files:")
    for sql_file in sorted(sql_files):
        print(f"  - {sql_file}")
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("AWS Lambda SQL Deployment - Validation Script")
    print("=" * 60)
    print()
    
    # Run all validations
    validations = [
        validate_lambda_function(),
        check_files_exist(),
        check_example_sql_files()
    ]
    
    print()
    print("=" * 60)
    if all(validations):
        print("✓ ALL VALIDATIONS PASSED!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("=" * 60)
        sys.exit(1)
