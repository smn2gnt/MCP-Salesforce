# src/salesforce/tests/test_server.py (initial content)
import unittest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
import json # For comparing JSON strings
from typing import Any, Optional # For type hints if needed in test setup

# Assuming server.py is in the parent directory relative to this test file's directory.
# Adjust the import path if necessary based on how Python resolves modules in this structure.
# This might require PYTHONPATH adjustments when running tests, or a different import strategy
# if src is a package itself. For now, let's try a relative import path first,
# but be prepared that this might need adjustment.
# A more robust way might be 'from src.salesforce.server import ...' if 'src' is on PYTHONPATH.

from ..server import (
    SalesforceClient, # We might not mock SalesforceClient directly, but its instance sf_client
    run_soql_query,
    run_sosl_search,
    get_object_fields,
    get_record,
    create_record,
    update_record,
    delete_record,
    tooling_execute,
    apex_execute,
    restful,
    sf_client # This is the actual instance we need to patch/mock
)

class TestSalesforceTools(unittest.IsolatedAsyncioTestCase): # Using IsolatedAsyncioTestCase for async tool functions
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_run_soql_query_success(self, mock_sf_client):
        """Test successful SOQL query execution."""
        expected_data = {'totalSize': 1, 'records': [{'Name': 'Test Account'}]}
        mock_sf_client.sf.query_all.return_value = expected_data
        
        query = "SELECT Name FROM Account"
        result = await run_soql_query(query=query)
        
        expected_output = f"SOQL Query Results (JSON):\n{json.dumps(expected_data, indent=2)}"
        self.assertEqual(result, expected_output)
        mock_sf_client.sf.query_all.assert_called_once_with(query)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_run_soql_query_missing_arg(self, mock_sf_client):
        """Test SOQL query with missing query argument."""
        async with self.assertRaisesRegex(ValueError, "Missing 'query' argument"):
            await run_soql_query(query="")
        mock_sf_client.sf.query_all.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_get_object_fields_success(self, mock_sf_client):
        """Test successful retrieval of object fields."""
        expected_json_string = '[{"name": "Name", "label": "Account Name"}]'
        # Mock the SalesforceClient's get_object_fields method
        mock_sf_client.get_object_fields.return_value = expected_json_string 
        
        object_name = "Account"
        result = await get_object_fields(object_name=object_name)
        
        expected_output = f"{object_name} Metadata (JSON):\n{expected_json_string}"
        self.assertEqual(result, expected_output)
        mock_sf_client.get_object_fields.assert_called_once_with(object_name)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_get_object_fields_missing_arg(self, mock_sf_client):
        """Test get_object_fields with missing object_name argument."""
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name' argument"):
            await get_object_fields(object_name="")
        mock_sf_client.get_object_fields.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_get_object_fields_sf_none(self, mock_sf_client):
        """Test get_object_fields when sf_client.sf is None (connection not established)."""
        mock_sf_client.sf = None
        # The tool's internal check for sf_client.sf should raise the error
        # before trying to call sf_client.get_object_fields
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await get_object_fields(object_name="Account")
        mock_sf_client.get_object_fields.assert_not_called()


    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_update_record_success(self, mock_sf_client):
        """Test successful record update."""
        object_name = "Account"
        record_id = "001x00000000001AAA"
        data_to_update = {'Name': 'New Name'}
        expected_status_code = 204

        # Configure the mock for simple-salesforce style call: sf.Account.update(...)
        mock_sf_client.sf.Account.update.return_value = expected_status_code
        
        result = await update_record(object_name=object_name, record_id=record_id, data=data_to_update)
        
        expected_output = f"Update {object_name} Record Result: {expected_status_code}"
        self.assertEqual(result, expected_output)
        mock_sf_client.sf.Account.update.assert_called_once_with(record_id, data_to_update)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_update_record_missing_object_name(self, mock_sf_client):
        """Test update_record with missing object_name."""
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name', 'record_id', or 'data' argument"):
            await update_record(object_name="", record_id="123", data={'key': 'value'})
        mock_sf_client.sf.assert_not_called() # sf is the parent of Account, etc.

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_update_record_missing_record_id(self, mock_sf_client):
        """Test update_record with missing record_id."""
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name', 'record_id', or 'data' argument"):
            await update_record(object_name="Account", record_id="", data={'key': 'value'})
        mock_sf_client.sf.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_update_record_missing_data(self, mock_sf_client):
        """Test update_record with missing data."""
        # The type hint is dict[str, Any], so passing None or empty dict should be checked.
        # The current check is `if not object_name or not record_id or not data:`, so an empty dict would pass.
        # Let's assume the check implies data must be non-empty or present if required by Salesforce.
        # For this test, we'll pass an empty dict, which should pass the guard, but the tool might still fail
        # if simple-salesforce expects data. However, the guard is the first line of defense.
        # The problem asks to test "missing arguments", which could mean `None` or not provided.
        # The tool defines data: dict[str, Any], so it will always be a dict if type hints are followed.
        # The ValueError is for "missing 'object_name', 'record_id', or 'data' argument"
        # which implies `not data` (empty dict is not `not data`).
        # Let's assume the intent is to test the guard.
        # A more robust check in the tool might be `if not all([object_name, record_id, data]):`
        # or specific checks. Given the current guard, an empty dict for `data` will pass it.
        # To trigger the "missing 'data'" part of the error message from the guard, data would have to be None.
        # However, the type hint is `dict[str, Any]`. Let's test the spirit of the guard.
        # The tool's guard `if not object_name or not record_id or not data:` will be true if data is an empty dict.
        
        # Correction: `not data` for a dictionary is true if the dictionary is empty.
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name', 'record_id', or 'data' argument"):
            await update_record(object_name="Account", record_id="123", data={}) # Empty dict
        mock_sf_client.sf.assert_not_called()

    # Tests for run_sosl_search
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_run_sosl_search_success(self, mock_sf_client):
        """Test successful SOSL search execution."""
        expected_data = {'searchRecords': [{'attributes': {'type': 'Account'}, 'Id': '001x00000000001AAA'}]}
        mock_sf_client.sf.search.return_value = expected_data
        
        search_term = "FIND {Test Account}"
        result = await run_sosl_search(search=search_term)
        
        expected_output = f"SOSL Search Results (JSON):\n{json.dumps(expected_data, indent=2)}"
        self.assertEqual(result, expected_output)
        mock_sf_client.sf.search.assert_called_once_with(search_term)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_run_sosl_search_missing_arg(self, mock_sf_client):
        """Test SOSL search with missing search argument."""
        async with self.assertRaisesRegex(ValueError, "Missing 'search' argument"):
            await run_sosl_search(search="")
        mock_sf_client.sf.search.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_run_sosl_search_sf_none(self, mock_sf_client):
        """Test run_sosl_search when sf_client.sf is None."""
        mock_sf_client.sf = None
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await run_sosl_search(search="FIND {Test}")
        # No direct call to sf_client.sf.search, but the sf_client.sf check is implicit in the tool

    # Tests for get_record
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_get_record_success(self, mock_sf_client):
        """Test successful retrieval of a record."""
        object_name = "Contact"
        record_id = "003x00000000001AAA"
        expected_data = {'Id': record_id, 'LastName': 'Tester'}

        mock_object_operations = MagicMock()
        mock_object_operations.get.return_value = expected_data
        type(mock_sf_client.sf).Contact = PropertyMock(return_value=mock_object_operations)
        
        result = await get_record(object_name=object_name, record_id=record_id)
        
        expected_output = f"{object_name} Record (JSON):\n{json.dumps(expected_data, indent=2)}"
        self.assertEqual(result, expected_output)
        mock_object_operations.get.assert_called_once_with(record_id)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_get_record_missing_args(self, mock_sf_client):
        """Test get_record with missing arguments."""
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name' or 'record_id' argument"):
            await get_record(object_name="", record_id="123")
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name' or 'record_id' argument"):
            await get_record(object_name="Contact", record_id="")
        mock_sf_client.sf.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_get_record_sf_none(self, mock_sf_client):
        """Test get_record when sf_client.sf is None."""
        mock_sf_client.sf = None
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await get_record(object_name="Contact", record_id="123")

    # Tests for create_record
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_create_record_success(self, mock_sf_client):
        """Test successful creation of a record."""
        object_name = "Lead"
        data_to_create = {'Company': 'Test Corp', 'LastName': 'Person'}
        expected_response = {'id': '00Qx00000000001AAA', 'success': True, 'errors': []}

        mock_object_operations = MagicMock()
        mock_object_operations.create.return_value = expected_response
        type(mock_sf_client.sf).Lead = PropertyMock(return_value=mock_object_operations)
        
        result = await create_record(object_name=object_name, data=data_to_create)
        
        expected_output = f"Create {object_name} Record Result (JSON):\n{json.dumps(expected_response, indent=2)}"
        self.assertEqual(result, expected_output)
        mock_object_operations.create.assert_called_once_with(data_to_create)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_create_record_missing_args(self, mock_sf_client):
        """Test create_record with missing arguments."""
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name' or 'data' argument"):
            await create_record(object_name="", data={'key': 'value'})
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name' or 'data' argument"):
            await create_record(object_name="Lead", data={}) # Empty dict for data
        mock_sf_client.sf.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_create_record_sf_none(self, mock_sf_client):
        """Test create_record when sf_client.sf is None."""
        mock_sf_client.sf = None
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await create_record(object_name="Lead", data={'Company': 'Test Corp'})

    # Tests for delete_record
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_delete_record_success(self, mock_sf_client):
        """Test successful deletion of a record."""
        object_name = "Opportunity"
        record_id = "006x00000000001AAA"
        expected_status_code = 204

        mock_object_operations = MagicMock()
        mock_object_operations.delete.return_value = expected_status_code
        type(mock_sf_client.sf).Opportunity = PropertyMock(return_value=mock_object_operations)
        
        result = await delete_record(object_name=object_name, record_id=record_id)
        
        expected_output = f"Delete {object_name} Record Result: {expected_status_code}"
        self.assertEqual(result, expected_output)
        mock_object_operations.delete.assert_called_once_with(record_id)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_delete_record_missing_args(self, mock_sf_client):
        """Test delete_record with missing arguments."""
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name' or 'record_id' argument"):
            await delete_record(object_name="", record_id="123")
        async with self.assertRaisesRegex(ValueError, "Missing 'object_name' or 'record_id' argument"):
            await delete_record(object_name="Opportunity", record_id="")
        mock_sf_client.sf.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_delete_record_sf_none(self, mock_sf_client):
        """Test delete_record when sf_client.sf is None."""
        mock_sf_client.sf = None
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await delete_record(object_name="Opportunity", record_id="123")

    # Tests for tooling_execute
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_tooling_execute_success(self, mock_sf_client):
        """Test successful tooling_execute call."""
        action = "sobjects/ApexClass"
        expected_response = {'size': 0, 'totalSize': 0, 'records': []}
        mock_sf_client.sf.toolingexecute.return_value = expected_response
        
        result = await tooling_execute(action=action)
        
        expected_output = f"Tooling Execute Result (JSON):\n{json.dumps(expected_response, indent=2)}"
        self.assertEqual(result, expected_output)
        mock_sf_client.sf.toolingexecute.assert_called_once_with(action, method="GET", data=None)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_tooling_execute_missing_arg(self, mock_sf_client):
        """Test tooling_execute with missing action argument."""
        async with self.assertRaisesRegex(ValueError, "Missing 'action' argument"):
            await tooling_execute(action="")
        mock_sf_client.sf.toolingexecute.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_tooling_execute_sf_none(self, mock_sf_client):
        """Test tooling_execute when sf_client.sf is None."""
        mock_sf_client.sf = None
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await tooling_execute(action="sobjects/ApexClass")

    # Tests for apex_execute
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_apex_execute_success(self, mock_sf_client):
        """Test successful apex_execute call."""
        action = "/MyApexClass/"
        expected_response = {'status': 'Success'}
        mock_sf_client.sf.apexecute.return_value = expected_response
        
        result = await apex_execute(action=action, method="POST", data={'param': 'value'})
        
        expected_output = f"Apex Execute Result (JSON):\n{json.dumps(expected_response, indent=2)}"
        self.assertEqual(result, expected_output)
        mock_sf_client.sf.apexecute.assert_called_once_with(action, method="POST", data={'param': 'value'})

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_apex_execute_missing_arg(self, mock_sf_client):
        """Test apex_execute with missing action argument."""
        async with self.assertRaisesRegex(ValueError, "Missing 'action' argument"):
            await apex_execute(action="")
        mock_sf_client.sf.apexecute.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_apex_execute_sf_none(self, mock_sf_client):
        """Test apex_execute when sf_client.sf is None."""
        mock_sf_client.sf = None
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await apex_execute(action="/MyApexClass/")

    # Tests for restful
    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_restful_success(self, mock_sf_client):
        """Test successful restful call."""
        path = "sobjects/Account/describe"
        expected_response = {'name': 'Account', 'fields': []}
        mock_sf_client.sf.restful.return_value = expected_response
        
        result = await restful(path=path, method="GET", params={'detail': 'full'})
        
        expected_output = f"RESTful API Call Result (JSON):\n{json.dumps(expected_response, indent=2)}"
        self.assertEqual(result, expected_output)
        mock_sf_client.sf.restful.assert_called_once_with(path, method="GET", params={'detail': 'full'}, json=None)

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_restful_missing_arg(self, mock_sf_client):
        """Test restful with missing path argument."""
        async with self.assertRaisesRegex(ValueError, "Missing 'path' argument"):
            await restful(path="")
        mock_sf_client.sf.restful.assert_not_called()

    @patch('src.salesforce.server.sf_client', autospec=True)
    async def test_restful_sf_none(self, mock_sf_client):
        """Test restful when sf_client.sf is None."""
        mock_sf_client.sf = None
        async with self.assertRaisesRegex(ValueError, "Salesforce connection not established."):
            await restful(path="sobjects/Account/describe")

if __name__ == '__main__':
    unittest.main()
