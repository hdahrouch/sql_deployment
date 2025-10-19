"""
Unit tests for the AWS Glue Table Manager.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from glue_table_manager import GlueTableManager


class TestGlueTableManager(unittest.TestCase):
    """Test cases for the GlueTableManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.database_name = "test_database"
        self.table_name = "test_table"
        self.region_name = "us-east-1"
        
        # Create a patcher for boto3.client
        self.boto_patcher = patch('glue_table_manager.boto3.client')
        self.mock_boto_client = self.boto_patcher.start()
        self.mock_glue = MagicMock()
        self.mock_boto_client.return_value = self.mock_glue
        
        # Initialize the manager
        self.manager = GlueTableManager(self.database_name, self.region_name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.boto_patcher.stop()
    
    def test_initialization(self):
        """Test that the manager initializes correctly."""
        self.assertEqual(self.manager.database_name, self.database_name)
        self.mock_boto_client.assert_called_once_with('glue', region_name=self.region_name)
    
    def test_table_exists_returns_true_when_table_found(self):
        """Test that table_exists returns True when the table is found."""
        self.mock_glue.get_table.return_value = {'Table': {'Name': self.table_name}}
        
        result = self.manager.table_exists(self.table_name)
        
        self.assertTrue(result)
        self.mock_glue.get_table.assert_called_once_with(
            DatabaseName=self.database_name,
            Name=self.table_name
        )
    
    def test_table_exists_returns_false_when_table_not_found(self):
        """Test that table_exists returns False when the table is not found."""
        error_response = {'Error': {'Code': 'EntityNotFoundException'}}
        self.mock_glue.get_table.side_effect = ClientError(error_response, 'get_table')
        
        result = self.manager.table_exists(self.table_name)
        
        self.assertFalse(result)
    
    def test_table_exists_raises_exception_for_other_errors(self):
        """Test that table_exists raises exception for non-EntityNotFound errors."""
        error_response = {'Error': {'Code': 'AccessDeniedException'}}
        self.mock_glue.get_table.side_effect = ClientError(error_response, 'get_table')
        
        with self.assertRaises(ClientError):
            self.manager.table_exists(self.table_name)
    
    def test_delete_table_success(self):
        """Test that delete_table successfully deletes a table."""
        self.mock_glue.delete_table.return_value = {}
        
        result = self.manager.delete_table(self.table_name)
        
        self.assertTrue(result)
        self.mock_glue.delete_table.assert_called_once_with(
            DatabaseName=self.database_name,
            Name=self.table_name
        )
    
    def test_delete_table_returns_false_when_not_found(self):
        """Test that delete_table returns False when table doesn't exist."""
        error_response = {'Error': {'Code': 'EntityNotFoundException'}}
        self.mock_glue.delete_table.side_effect = ClientError(error_response, 'delete_table')
        
        result = self.manager.delete_table(self.table_name)
        
        self.assertFalse(result)
    
    def test_delete_table_raises_exception_for_other_errors(self):
        """Test that delete_table raises exception for non-EntityNotFound errors."""
        error_response = {'Error': {'Code': 'AccessDeniedException'}}
        self.mock_glue.delete_table.side_effect = ClientError(error_response, 'delete_table')
        
        with self.assertRaises(ClientError):
            self.manager.delete_table(self.table_name)
    
    def test_delete_table_if_exists_deletes_when_table_exists(self):
        """Test that delete_table_if_exists deletes when table exists."""
        self.mock_glue.delete_table.return_value = {}
        
        result = self.manager.delete_table_if_exists(self.table_name)
        
        self.assertTrue(result)
        self.mock_glue.delete_table.assert_called_once()
    
    def test_delete_table_if_exists_returns_false_when_table_doesnt_exist(self):
        """Test that delete_table_if_exists returns False when table doesn't exist."""
        error_response = {'Error': {'Code': 'EntityNotFoundException'}}
        self.mock_glue.delete_table.side_effect = ClientError(error_response, 'delete_table')
        
        result = self.manager.delete_table_if_exists(self.table_name)
        
        self.assertFalse(result)
        self.mock_glue.delete_table.assert_called_once()
    
    def test_create_table_success(self):
        """Test that create_table successfully creates a table."""
        table_input = {
            'Name': self.table_name,
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}]
            }
        }
        expected_response = {'TableMetadata': {}}
        self.mock_glue.create_table.return_value = expected_response
        
        result = self.manager.create_table(self.table_name, table_input)
        
        self.assertEqual(result, expected_response)
        self.mock_glue.create_table.assert_called_once_with(
            DatabaseName=self.database_name,
            TableInput=table_input
        )
    
    def test_create_table_raises_exception_on_error(self):
        """Test that create_table raises exception on error."""
        table_input = {'Name': self.table_name}
        error_response = {'Error': {'Code': 'InvalidInputException'}}
        self.mock_glue.create_table.side_effect = ClientError(error_response, 'create_table')
        
        with self.assertRaises(ClientError):
            self.manager.create_table(self.table_name, table_input)
    
    def test_recreate_table_deletes_existing_table_before_creating(self):
        """Test that recreate_table deletes existing table before creating new one."""
        table_input = {
            'Name': self.table_name,
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}]
            }
        }
        # Table exists - delete_table succeeds
        self.mock_glue.delete_table.return_value = {}
        self.mock_glue.create_table.return_value = {'TableMetadata': {}}
        
        result = self.manager.recreate_table(self.table_name, table_input)
        
        # Verify delete_table and create_table are called
        self.mock_glue.delete_table.assert_called_once()
        self.mock_glue.create_table.assert_called_once()
        
        # Verify delete is called before create by checking call order
        calls = [call[0] for call in self.mock_glue.method_calls]
        delete_index = calls.index('delete_table')
        create_index = calls.index('create_table')
        self.assertLess(delete_index, create_index, "delete_table should be called before create_table")
    
    def test_recreate_table_creates_when_table_doesnt_exist(self):
        """Test that recreate_table creates table when it doesn't exist."""
        table_input = {
            'Name': self.table_name,
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}]
            }
        }
        # Table doesn't exist - delete_table returns False
        error_response = {'Error': {'Code': 'EntityNotFoundException'}}
        self.mock_glue.delete_table.side_effect = ClientError(error_response, 'delete_table')
        self.mock_glue.create_table.return_value = {'TableMetadata': {}}
        
        result = self.manager.recreate_table(self.table_name, table_input)
        
        # Verify delete_table is called (returns False) and create_table is called
        self.mock_glue.delete_table.assert_called_once()
        self.mock_glue.create_table.assert_called_once()


if __name__ == '__main__':
    unittest.main()
