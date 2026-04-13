"""Tests for the Salesforce MCP server."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from simple_salesforce import SFType
from src.salesforce.server import format_records, SalesforceClient


class TestFormatRecords:
    """Tests for the format_records function."""

    def test_csv_format_strips_attributes(self):
        """CSV format should remove 'attributes' metadata from records."""
        records = [
            {'attributes': {'type': 'Account', 'url': '/services/data/v59.0/sobjects/Account/001'},
             'Id': '001ABC', 'Name': 'Acme Corp'},
            {'attributes': {'type': 'Account', 'url': '/services/data/v59.0/sobjects/Account/002'},
             'Id': '002DEF', 'Name': 'Globex'},
        ]
        result = format_records(records, 'csv')

        assert 'attributes' not in result
        assert 'type' not in result.split('\n')[1]  # Not in header
        assert '001ABC' in result
        assert 'Acme Corp' in result
        assert 'Total: 2 records' in result

    def test_csv_format_header_and_rows(self):
        """CSV should have proper header and data rows."""
        records = [
            {'attributes': {'type': 'Store__c'}, 'Id': '123', 'Name': 'Store A', 'Entity': '10'},
            {'attributes': {'type': 'Store__c'}, 'Id': '456', 'Name': 'Store B', 'Entity': '20'},
        ]
        result = format_records(records, 'csv')
        # Normalize line endings for cross-platform compatibility
        result = result.replace('\r\n', '\n').replace('\r', '\n')
        lines = result.strip().split('\n')

        assert lines[0] == 'Total: 2 records'
        assert lines[1] == 'Id,Name,Entity'
        assert lines[2] == '123,Store A,10'
        assert lines[3] == '456,Store B,20'

    def test_compact_json_format(self):
        """Compact JSON should have no whitespace and no attributes."""
        records = [
            {'attributes': {'type': 'Account'}, 'Id': '001', 'Name': 'Test'},
        ]
        result = format_records(records, 'compact')

        assert 'attributes' not in result
        assert '  ' not in result  # No indentation
        assert '\n' not in result.split('\n', 1)[1]  # No newlines in JSON part
        assert '[{"Id":"001","Name":"Test"}]' in result

    def test_json_format_pretty_printed(self):
        """Full JSON should be indented and readable."""
        records = [
            {'attributes': {'type': 'Account'}, 'Id': '001', 'Name': 'Test'},
        ]
        result = format_records(records, 'json')

        assert 'attributes' not in result
        assert '  ' in result  # Has indentation
        assert '"Id": "001"' in result

    def test_empty_records(self):
        """Empty record list should return appropriate message."""
        result = format_records([], 'csv')
        assert result == 'No records found.'

        result = format_records([], 'json')
        assert result == 'No records found.'

    def test_nested_attributes_stripped(self):
        """Nested records (relationships) should have their attributes stripped too."""
        records = [
            {
                'attributes': {'type': 'Store__c'},
                'Id': '123',
                'Owner': {
                    'attributes': {'type': 'User', 'url': '/services/data/v59.0/sobjects/User/005'},
                    'Name': 'John Doe',
                    'Id': 'user1'
                }
            }
        ]
        result = format_records(records, 'json')
        parsed = json.loads(result.split('\n', 1)[1])

        assert 'attributes' not in parsed[0]
        assert 'attributes' not in parsed[0]['Owner']
        assert parsed[0]['Owner']['Name'] == 'John Doe'

    def test_csv_flattens_nested_dicts(self):
        """CSV format should JSON-serialize nested dictionaries."""
        records = [
            {
                'attributes': {'type': 'Store__c'},
                'Id': '123',
                'Owner': {'Name': 'John', 'Id': 'u1'}
            }
        ]
        result = format_records(records, 'csv')

        # Nested dict should be JSON string in CSV (CSV uses "" to escape quotes)
        assert 'John' in result
        assert 'u1' in result
        # The JSON is quoted and escaped in CSV format
        assert '123' in result

    def test_include_total_false(self):
        """Should be able to exclude total count from output."""
        records = [{'attributes': {}, 'Id': '1', 'Name': 'Test'}]
        result = format_records(records, 'csv', include_total=False)

        assert 'Total:' not in result
        assert 'Id,Name' in result

    def test_null_values_in_records(self):
        """Should handle None/null values gracefully."""
        records = [
            {'attributes': {}, 'Id': '123', 'Name': 'Test', 'Phone': None},
        ]
        result = format_records(records, 'csv')

        assert '123' in result
        assert 'Test' in result
        # None should appear as empty or 'None' in CSV

    def test_special_characters_in_csv(self):
        """CSV should handle special characters (commas, quotes) properly."""
        records = [
            {'attributes': {}, 'Id': '1', 'Name': 'Acme, Inc.', 'Description': 'He said "hello"'},
        ]
        result = format_records(records, 'csv')

        # CSV library should properly quote/escape these
        assert 'Acme' in result


class TestSalesforceClient:
    """Tests for the SalesforceClient class."""

    @patch('src.salesforce.server.Salesforce')
    def test_connect_with_client_credentials(self, mock_sf_class):
        """Should connect using client credentials when provided."""
        mock_sf_class.return_value = Mock()

        with patch.dict('os.environ', {
            'SALESFORCE_CLIENT_ID': 'test_client_id',
            'SALESFORCE_CLIENT_SECRET': 'test_secret',
            'SALESFORCE_DOMAIN': 'test.my'
        }, clear=True):
            client = SalesforceClient()
            result = client.connect()

        assert result is True
        mock_sf_class.assert_called_once_with(
            consumer_key='test_client_id',
            consumer_secret='test_secret',
            domain='test.my'
        )

    @patch('src.salesforce.server.Salesforce')
    def test_connect_with_access_token(self, mock_sf_class):
        """Should connect using access token when provided (takes priority)."""
        mock_sf_class.return_value = Mock()

        with patch.dict('os.environ', {
            'SALESFORCE_ACCESS_TOKEN': 'test_token',
            'SALESFORCE_INSTANCE_URL': 'https://test.salesforce.com',
            'SALESFORCE_DOMAIN': 'test'
        }, clear=True):
            client = SalesforceClient()
            result = client.connect()

        assert result is True
        mock_sf_class.assert_called_once_with(
            instance_url='https://test.salesforce.com',
            session_id='test_token',
            domain='test'
        )

    @patch('src.salesforce.server.Salesforce')
    def test_connect_failure_returns_false(self, mock_sf_class):
        """Should return False when connection fails."""
        mock_sf_class.side_effect = Exception("Connection failed")

        with patch.dict('os.environ', {
            'SALESFORCE_CLIENT_ID': 'test',
            'SALESFORCE_CLIENT_SECRET': 'test'
        }, clear=True):
            client = SalesforceClient()
            result = client.connect()

        assert result is False

    @patch('src.salesforce.server.Salesforce')
    def test_get_object_fields_returns_csv(self, mock_sf_class):
        """get_object_fields should return CSV formatted field list."""
        mock_sf = Mock()
        mock_sf_class.return_value = mock_sf

        mock_describe = {
            'fields': [
                {'name': 'Id', 'label': 'Record ID', 'type': 'id', 'updateable': False},
                {'name': 'Name', 'label': 'Account Name', 'type': 'string', 'updateable': True},
            ]
        }
        mock_sf.Account.describe.return_value = mock_describe

        with patch.dict('os.environ', {
            'SALESFORCE_CLIENT_ID': 'test',
            'SALESFORCE_CLIENT_SECRET': 'test'
        }, clear=True):
            client = SalesforceClient()
            client.connect()
            result = client.get_object_fields('Account')

        assert 'Total: 2 fields' in result
        assert 'name,label,type,updateable' in result
        assert 'Id,Record ID,id,False' in result
        assert 'Name,Account Name,string,True' in result

    @patch('src.salesforce.server.Salesforce')
    def test_get_object_fields_caches_results(self, mock_sf_class):
        """get_object_fields should cache results to avoid repeated API calls."""
        mock_sf = Mock()
        mock_sf_class.return_value = mock_sf

        mock_describe = {'fields': [{'name': 'Id', 'label': 'ID', 'type': 'id', 'updateable': False}]}
        mock_sf.Account.describe.return_value = mock_describe

        with patch.dict('os.environ', {
            'SALESFORCE_CLIENT_ID': 'test',
            'SALESFORCE_CLIENT_SECRET': 'test'
        }, clear=True):
            client = SalesforceClient()
            client.connect()

            # Call twice
            client.get_object_fields('Account')
            client.get_object_fields('Account')

        # describe() should only be called once due to caching
        assert mock_sf.Account.describe.call_count == 1


class TestToolHandlers:
    """Tests for the MCP tool handlers."""

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_run_soql_query_csv_format(self, mock_client):
        """run_soql_query should return CSV formatted results by default."""
        from src.salesforce.server import handle_call_tool

        mock_client.sf.query_all.return_value = {
            'records': [
                {'attributes': {'type': 'Account'}, 'Id': '001', 'Name': 'Test'}
            ],
            'totalSize': 1,
            'done': True
        }

        result = await handle_call_tool('run_soql_query', {'query': 'SELECT Id, Name FROM Account'})

        assert len(result) == 1
        assert 'Total: 1 records' in result[0].text
        assert 'Id,Name' in result[0].text
        assert '001,Test' in result[0].text

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_run_soql_query_json_format(self, mock_client):
        """run_soql_query should return JSON when format='json'."""
        from src.salesforce.server import handle_call_tool

        mock_client.sf.query_all.return_value = {
            'records': [
                {'attributes': {'type': 'Account'}, 'Id': '001', 'Name': 'Test'}
            ]
        }

        result = await handle_call_tool('run_soql_query', {'query': 'SELECT Id FROM Account', 'format': 'json'})

        assert '"Id": "001"' in result[0].text

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_run_soql_query_missing_query(self, mock_client):
        """run_soql_query should raise error when query is missing."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="Missing 'query' argument"):
            await handle_call_tool('run_soql_query', {})

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_get_record_strips_attributes(self, mock_client):
        """get_record should strip attributes from response."""
        from src.salesforce.server import handle_call_tool

        mock_sf_object = Mock(spec=SFType)
        mock_sf_object.get.return_value = {
            'attributes': {'type': 'Account', 'url': '/test'},
            'Id': '001',
            'Name': 'Test Account'
        }
        mock_client.sf = Mock()
        mock_client.sf.Account = mock_sf_object

        # Mock getattr to return our mock object
        with patch('src.salesforce.server.getattr', return_value=mock_sf_object):
            result = await handle_call_tool('get_record', {
                'object_name': 'Account',
                'record_id': '001'
            })

        assert 'attributes' not in result[0].text
        assert '001' in result[0].text
        assert 'Test Account' in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_error(self):
        """Unknown tool names should raise ValueError."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="Unknown tool"):
            await handle_call_tool('nonexistent_tool', {})


class TestBulkOperations:
    """Tests for bulk_create_records, bulk_update_records, and bulk_delete_records tools."""

    # ------------------------------------------------------------------ #
    # bulk_create_records                                                  #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_create_records_success(self, mock_client):
        """bulk_create_records should call bulk.insert and return results."""
        from src.salesforce.server import handle_call_tool

        mock_bulk_result = [
            {'id': '001AA', 'success': True, 'errors': []},
            {'id': '001BB', 'success': True, 'errors': []},
        ]
        mock_bulk_op = Mock()
        mock_bulk_op.insert.return_value = mock_bulk_result
        mock_client.sf.bulk.Account = mock_bulk_op

        records = [{'Name': 'Alpha Corp'}, {'Name': 'Beta Corp'}]
        result = await handle_call_tool('bulk_create_records', {
            'object_name': 'Account',
            'data': records,
        })

        mock_bulk_op.insert.assert_called_once_with(records)
        assert len(result) == 1
        assert 'Bulk Create Account Results' in result[0].text
        assert '001AA' in result[0].text
        assert '001BB' in result[0].text

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_create_records_missing_arguments(self, mock_client):
        """bulk_create_records should raise ValueError when object_name or data is missing."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="Missing 'object_name' or 'data'"):
            await handle_call_tool('bulk_create_records', {'object_name': 'Account'})

        with pytest.raises(ValueError, match="Missing 'object_name' or 'data'"):
            await handle_call_tool('bulk_create_records', {'data': [{'Name': 'X'}]})

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_create_records_data_not_list(self, mock_client):
        """bulk_create_records should raise ValueError when data is not a list."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="list of records"):
            await handle_call_tool('bulk_create_records', {
                'object_name': 'Account',
                'data': {'Name': 'Not a list'},
            })

    # ------------------------------------------------------------------ #
    # bulk_update_records                                                  #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_update_records_success(self, mock_client):
        """bulk_update_records should call bulk.update and return results."""
        from src.salesforce.server import handle_call_tool

        mock_bulk_result = [
            {'id': '001AA', 'success': True, 'errors': []},
            {'id': '001BB', 'success': True, 'errors': []},
        ]
        mock_bulk_op = Mock()
        mock_bulk_op.update.return_value = mock_bulk_result
        mock_client.sf.bulk.Account = mock_bulk_op

        records = [
            {'Id': '001AA', 'Name': 'Alpha Updated'},
            {'Id': '001BB', 'Name': 'Beta Updated'},
        ]
        result = await handle_call_tool('bulk_update_records', {
            'object_name': 'Account',
            'data': records,
        })

        mock_bulk_op.update.assert_called_once_with(records)
        assert 'Bulk Update Account Results' in result[0].text
        assert '001AA' in result[0].text

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_update_records_missing_id_field(self, mock_client):
        """bulk_update_records should raise ValueError when a record lacks an Id field."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="'Id' field"):
            await handle_call_tool('bulk_update_records', {
                'object_name': 'Account',
                'data': [{'Name': 'No ID here'}],
            })

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_update_records_missing_arguments(self, mock_client):
        """bulk_update_records should raise ValueError when object_name or data is missing."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="Missing 'object_name' or 'data'"):
            await handle_call_tool('bulk_update_records', {'object_name': 'Account'})

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_update_records_data_not_list(self, mock_client):
        """bulk_update_records should raise ValueError when data is not a list."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="list of records"):
            await handle_call_tool('bulk_update_records', {
                'object_name': 'Account',
                'data': {'Id': '001', 'Name': 'Not a list'},
            })

    # ------------------------------------------------------------------ #
    # bulk_delete_records                                                  #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_delete_records_success(self, mock_client):
        """bulk_delete_records should convert IDs to dicts, call bulk.delete, and return results."""
        from src.salesforce.server import handle_call_tool

        mock_bulk_result = [
            {'id': '001AA', 'success': True, 'errors': []},
            {'id': '001BB', 'success': True, 'errors': []},
        ]
        mock_bulk_op = Mock()
        mock_bulk_op.delete.return_value = mock_bulk_result
        mock_client.sf.bulk.Account = mock_bulk_op

        result = await handle_call_tool('bulk_delete_records', {
            'object_name': 'Account',
            'record_ids': ['001AA', '001BB'],
        })

        mock_bulk_op.delete.assert_called_once_with([{'Id': '001AA'}, {'Id': '001BB'}])
        assert 'Bulk Delete Account Results' in result[0].text
        assert '001AA' in result[0].text

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_delete_records_missing_arguments(self, mock_client):
        """bulk_delete_records should raise ValueError when object_name or record_ids is missing."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="Missing 'object_name' or 'record_ids'"):
            await handle_call_tool('bulk_delete_records', {'object_name': 'Account'})

        with pytest.raises(ValueError, match="Missing 'object_name' or 'record_ids'"):
            await handle_call_tool('bulk_delete_records', {'record_ids': ['001AA']})

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_delete_records_not_a_list(self, mock_client):
        """bulk_delete_records should raise ValueError when record_ids is not a list."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="list of strings"):
            await handle_call_tool('bulk_delete_records', {
                'object_name': 'Account',
                'record_ids': '001AA',
            })

    @pytest.mark.asyncio
    @patch('src.salesforce.server.sf_client')
    async def test_bulk_delete_records_non_string_id(self, mock_client):
        """bulk_delete_records should raise ValueError when an ID is not a string."""
        from src.salesforce.server import handle_call_tool

        with pytest.raises(ValueError, match="string ID"):
            await handle_call_tool('bulk_delete_records', {
                'object_name': 'Account',
                'record_ids': [123, 456],
            })
