import collections
from datetime import datetime
import requests
from flask import current_app # To access app.config for API URL and Key
import logging

logger = logging.getLogger('upload_history') # Use the same logger

def validate_uniqueness(data_list_of_dicts, field_name):
    """
    Validates that all values in a specified field (column) of a list of dictionaries are unique.
    Empty strings and None values are also considered for uniqueness checks.

    Args:
        data_list_of_dicts (list[dict]): The data to validate.
        field_name (str): The name of the field (key) to check for uniqueness.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains details
                    about a duplicate value found. Each dict includes:
                    'value': The duplicate value.
                    'indices': A list of 0-based row indices where the value appears.
                    'field_name': The name of the field checked.
                    'message': A descriptive error message.
                    'severity': "error"
                    Returns an empty list if all values in the specified field are unique.
    """
    value_counts = collections.defaultdict(lambda: {'count': 0, 'indices': []})
    duplicate_info = []

    for index, row in enumerate(data_list_of_dicts):
        value = row.get(field_name)
        # Even if value is None or "", it's treated as a value for uniqueness check.
        # If specific handling for None/empty is needed (e.g., ignore them), add it here.

        value_counts[value]['count'] += 1
        value_counts[value]['indices'].append(index)

    for value, entry in value_counts.items():
        if entry['count'] > 1:
            duplicate_info.append({
                'value': value,
                'indices': entry['indices'],
                'field_name': field_name,
                'message': f"Value '{value}' in field '{field_name}' is not unique. Found at row indices: {entry['indices']}.",
                'severity': "error"
            })

    return duplicate_info

if __name__ == '__main__':
    print("--- Testing validate_uniqueness ---")

    sample_data_1 = [
        {'InvoiceID': 'INV001', 'Amount': 50},
        {'InvoiceID': 'INV002', 'Amount': 75},
        {'InvoiceID': 'INV001', 'Amount': 60}, # Duplicate InvoiceID
        {'InvoiceID': 'INV003', 'Amount': 100},
        {'InvoiceID': 'INV002', 'Amount': 80}  # Duplicate InvoiceID
    ]
    print(f"\nSample Data 1: {sample_data_1}")
    duplicates_inv_id = validate_uniqueness(sample_data_1, 'InvoiceID')
    print(f"Uniqueness validation for 'InvoiceID':")
    if duplicates_inv_id:
        for dup in duplicates_inv_id:
            print(dup)
    else:
        print("No duplicates found for 'InvoiceID'.")


def validate_range(data_list_of_dicts, field_name, min_value=None, max_value=None, expected_type='number'):
    """
    Validates that values in a specified field fall within a given min/max range.

    Args:
        data_list_of_dicts (list[dict]): The data to validate.
        field_name (str): The name of the field (key) to check.
        min_value (float/int/date, optional): Minimum allowed value (inclusive). Defaults to None.
        max_value (float/int/date, optional): Maximum allowed value (inclusive). Defaults to None.
        expected_type (str, optional): The expected type of the data ('number', 'date').
                                     Guides conversion before comparison. Defaults to 'number'.

    Returns:
        list[dict]: A list of dictionaries, each detailing an out-of-range value or a conversion error.
                    Each dict includes: 'value' (original), 'index', 'field_name', 'message', 'severity'.
                    For range violations, 'actual_converted_value' is also included.
                    Returns an empty list if all values are within range or not applicable.
    """
    out_of_range_info = []

    if min_value is None and max_value is None:
        return out_of_range_info # No range to check against

    for index, row in enumerate(data_list_of_dicts):
        raw_value = row.get(field_name)

        if raw_value is None or str(raw_value).strip() == "":
            # Skip None or empty string values for range validation.
            # Required field validation should be a separate rule if empty/None is not allowed.
            continue

        converted_value = None
        conversion_error_message = None
        problem_type = "conversion_error" # Default problem type

        if expected_type == 'number':
            try:
                # Attempt to convert to float for numerical comparison
                # Handle potential currency symbols or thousands separators if necessary,
                # though this basic version assumes a clean number string or actual number.
                if isinstance(raw_value, str):
                    # Basic cleaning for common currency/number formats if needed:
                    # cleaned_raw_value = raw_value.replace('$', '').replace(',', '').strip()
                    # For now, assume it's relatively clean or an actual number type
                    cleaned_raw_value = str(raw_value).strip()
                    if not cleaned_raw_value: continue # Skip if it becomes empty after stripping
                else:
                    cleaned_raw_value = raw_value

                converted_value = float(cleaned_raw_value)
            except ValueError:
                conversion_error_message = f"Cannot be converted to a number."
            except TypeError: # If raw_value is not string-like or number-like for float()
                 conversion_error_message = f"Is not a processable type for numeric conversion (e.g. list, dict)."


        elif expected_type == 'date':
            # Placeholder for basic date parsing - this is highly dependent on expected formats
            # For a robust solution, use a library like dateutil.parser
            # And ensure min_value/max_value are also date objects for comparison
            if isinstance(raw_value, str):
                try:
                    # Example: Try a common format. This should be made more robust or configurable.
                    converted_value = datetime.strptime(raw_value, '%Y-%m-%d').date()
                except ValueError:
                    try: # Try another common format
                        converted_value = datetime.strptime(raw_value, '%m/%d/%Y').date()
                    except ValueError:
                        conversion_error_message = f"Does not match expected date formats (e.g., YYYY-MM-DD, MM/DD/YYYY)."
            elif isinstance(raw_value, datetime.date): # Already a date object
                converted_value = raw_value
            elif isinstance(raw_value, datetime): # Datetime object
                converted_value = raw_value.date()
            else:
                conversion_error_message = f"Is not a recognizable date string or date object."

        else: # Unknown expected_type
            conversion_error_message = f"Unsupported 'expected_type' for range validation: {expected_type}."


        if conversion_error_message:
            out_of_range_info.append({
                'value': raw_value,
                'index': index,
                'field_name': field_name,
                'message': f"Value '{raw_value}' in field '{field_name}' (row {index+1}) could not be processed as {expected_type}: {conversion_error_message}",
                'severity': 'warning', # Data type/conversion issues are warnings for range check
                'problem_type': problem_type
            })
            continue # Move to next row

        # Proceed with Range Check if conversion was successful
        is_out_of_range = False
        message_parts = []
        problem_type = "range_violation"

        if min_value is not None:
            # Ensure min_value is of comparable type if converted_value is a date
            if expected_type == 'date' and isinstance(min_value, str):
                try: min_value = datetime.strptime(min_value, '%Y-%m-%d').date() # Assuming min/max for dates are in YYYY-MM-DD
                except ValueError: # Handle error if min_value string for date is not in expected format
                    out_of_range_info.append({'value': raw_value, 'index': index, 'field_name': field_name, 'message': f"Min value '{min_value}' for date range check is not in expected format YYYY-MM-DD.", 'severity': 'config_error', 'problem_type': 'config_error'})
                    continue
            if converted_value < min_value:
                is_out_of_range = True
                message_parts.append(f"is less than min value {min_value}")

        if max_value is not None:
            if expected_type == 'date' and isinstance(max_value, str):
                try: max_value = datetime.strptime(max_value, '%Y-%m-%d').date()
                except ValueError:
                    out_of_range_info.append({'value': raw_value, 'index': index, 'field_name': field_name, 'message': f"Max value '{max_value}' for date range check is not in expected format YYYY-MM-DD.", 'severity': 'config_error', 'problem_type': 'config_error'})
                    continue
            if converted_value > max_value:
                is_out_of_range = True
                message_parts.append(f"is greater than max value {max_value}")

        if is_out_of_range:
            out_of_range_info.append({
                'value': raw_value,
                'actual_converted_value': str(converted_value), # Store converted value as string for JSON
                'index': index,
                'field_name': field_name,
                'message': f"Value '{raw_value}' (as {expected_type}: {converted_value}) in field '{field_name}' (row {index+1}) " + " and ".join(message_parts) + ".",
                'severity': 'warning', # Range violations are warnings
                'problem_type': problem_type
            })

    return out_of_range_info


if __name__ == '__main__':
    # ... (previous tests for validate_uniqueness) ...
    print("\n--- Testing validate_range ---")
    numeric_data = [
        {'id': 1, 'value': 10},
        {'id': 2, 'value': 0},
        {'id': 3, 'value': 100},
        {'id': 4, 'value': 50},
        {'id': 5, 'value': -5}, # Out of range (below min)
        {'id': 6, 'value': 105},# Out of range (above max)
        {'id': 7, 'value': "abc"},# Not a number
        {'id': 8, 'value': None}, # Skipped
        {'id': 9, 'value': ""},   # Skipped
        {'id': 10, 'value': "50.5"},
        {'id': 11, 'value': "$12.50"}, # Test with some cleaning (though current basic version might fail this)
    ]
    print(f"\nNumeric Data: {numeric_data}")

    range_results_num = validate_range(numeric_data, 'value', min_value=0, max_value=100, expected_type='number')
    print("Range validation for 'value' (0-100):")
    if range_results_num:
        for issue in range_results_num:
            print(issue)
    else:
        print("All applicable values are within range.")

def validate_invoice_via_api(invoice_number: str) -> dict:
    """
    Validates an invoice number using an external API.

    Args:
        invoice_number (str): The invoice number to validate.

    Returns:
        dict: A dictionary containing the validation status and details.
              Example: {'status': 'found', 'invoice_number': 'INV001', 'details': {...api_response...}}
                       {'status': 'not_found', 'invoice_number': 'INV002', 'message': 'Not found by API'}
                       {'status': 'error', 'message': 'API error message'}
                       {'status': 'config_error', 'message': 'API URL not configured.'}
    """
    if not current_app: # Should not happen in Flask context, but good for standalone testing
        logger.error("Flask current_app context not available for API validation.")
        return {'status': 'error', 'invoice_number': invoice_number, 'message': 'Application context not available.'}

    api_url = current_app.config.get('INVOICE_VALIDATION_API_URL')
    api_key = current_app.config.get('INVOICE_VALIDATION_API_KEY')

    if not api_url:
        logger.warning("INVOICE_VALIDATION_API_URL not configured. External validation skipped.")
        return {'status': 'config_error', 'invoice_number': invoice_number, 'message': 'External API URL not configured.'}

    headers = {}
    params = {'invoice_id': invoice_number} # Example: API takes ID in query param

    if api_key:
        headers['X-API-Key'] = api_key # Assuming API key is passed in a header called X-API-Key

    try:
        logger.info(f"Validating invoice '{invoice_number}' via external API: {api_url}")
        response = requests.get(api_url, params=params, headers=headers, timeout=10) # 10-second timeout
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

        api_response_data = response.json()
        logger.debug(f"API response for invoice '{invoice_number}': {api_response_data}")

        # Example parsing logic (adjust to your actual API contract)
        # This assumes the API returns a JSON with a 'status' or 'isValid' field.
        if api_response_data.get('status') == 'found' or api_response_data.get('isValid') is True:
            return {'status': 'found', 'invoice_number': invoice_number, 'details': api_response_data}
        elif api_response_data.get('status') == 'not_found' or api_response_data.get('isValid') is False:
            return {'status': 'not_found', 'invoice_number': invoice_number, 'message': api_response_data.get('message', 'Invoice not found or invalid according to external API.'), 'details': api_response_data}
        else:
            # If the API response format is unknown or doesn't match expected success/failure indicators
            logger.warning(f"Unexpected API response structure for invoice '{invoice_number}': {api_response_data}")
            return {'status': 'unknown_response', 'invoice_number': invoice_number, 'message': 'API response structure not recognized.', 'details': api_response_data}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout during API validation for invoice '{invoice_number}' at {api_url}.")
        return {'status': 'error', 'invoice_number': invoice_number, 'message': 'API request timed out.'}
    except requests.exceptions.HTTPError as e:
        error_text = e.response.text[:100] if e.response else "No response body"
        logger.error(f"HTTPError during API validation for invoice '{invoice_number}': {e.response.status_code} - {error_text}")
        return {'status': 'error', 'invoice_number': invoice_number, 'message': f'API request failed: {e.response.status_code} - {error_text}'}
    except requests.exceptions.RequestException as e: # Catches other network/connection errors
        logger.error(f"RequestException during API validation for invoice '{invoice_number}': {e}")
        return {'status': 'error', 'invoice_number': invoice_number, 'message': f'API request failed due to network issue: {str(e)}'}
    except ValueError: # Includes JSONDecodeError if response.json() fails
        logger.error(f"ValueError (e.g. JSONDecodeError) during API validation for invoice '{invoice_number}'. Response: {response.text[:200] if response else 'No response'}")
        return {'status': 'error', 'invoice_number': invoice_number, 'message': 'API response was not valid JSON.'}
    except Exception as e: # Catch-all for any other unexpected error
        logger.error(f"Unexpected error during API validation for invoice '{invoice_number}': {e}", exc_info=True)
        return {'status': 'error', 'invoice_number': invoice_number, 'message': f'An unexpected error occurred: {str(e)}'}


if __name__ == '__main__':
    # ... (previous tests for validate_uniqueness and validate_range) ...
    print("\n--- Testing validate_invoice_via_api ---")

    # Mock Flask app context for testing current_app.config
    class MockApp:
        def __init__(self):
            self.config = {}

    mock_app = MockApp()

    # Test case 1: API URL not configured
    print("\nTest 1: API URL not configured")
    # current_app is not available directly here, so we need a way to simulate it or test this part within Flask context
    # For direct script execution, this test will rely on the function handling current_app being None if not in Flask context.
    # However, the function as written uses `from flask import current_app` which means it expects to be run in Flask context.
    # To make it testable standalone for this part, we'd have to pass app_config or mock current_app.
    # Let's assume for now this is tested via integration or by temporarily modifying how config is accessed for the test.

    # Simulate config for other tests:
    # Option 1: Use a public test API like httpbin.org
    # mock_app.config['INVOICE_VALIDATION_API_URL'] = 'https://httpbin.org/get'
    # mock_app.config['INVOICE_VALIDATION_API_KEY'] = None # httpbin.org/get doesn't need a key

    # Option 2: Use a non-existent URL to test error handling for connection
    mock_app.config['INVOICE_VALIDATION_API_URL'] = 'http://localhost:12345/nonexistent'
    mock_app.config['INVOICE_VALIDATION_API_KEY'] = 'testkey123'

    # To properly test this function when run directly, we'd need to patch current_app
    # or pass app_config. For now, these __main__ tests will show limitations.

    print("\nTest 2: API call (example to a non-existent local URL to show error handling)")
    # This will likely fail if not in Flask app context or if current_app cannot be resolved.
    # To make this runnable directly for demonstration of the requests part:
    # We could temporarily modify validate_invoice_via_api to accept config dict for testing.
    # For now, this part of the test will likely show an error or skip if current_app isn't available.

    # A better way for standalone testing is to have a helper that sets up a mock current_app
    # For this subtask, the focus is on the function's internal logic assuming current_app is available.

    # If you were to run this within a Flask shell or test client:
    # with app.app_context():
    #     current_app.config['INVOICE_VALIDATION_API_URL'] = 'http://localhost:12345/nonexistent' # or a real test URL
    #     current_app.config['INVOICE_VALIDATION_API_KEY'] = 'fakekey'
    #     result = validate_invoice_via_api("INV_TEST_001")
    #     print(result)

    print("Note: Full testing of validate_invoice_via_api requires a Flask app context or mocking.")
    print("The function structure for API calls and error handling is in place.")
    # Example of how it *would* be called if current_app was properly mocked for this standalone script:
    # (This won't run correctly as is without more test setup for current_app)
    # from unittest.mock import patch
    # with patch('data_validator.current_app', mock_app):
    #     result = validate_invoice_via_api("INV_TEST_001")
    #     print(f"Simulated API call result: {result}")

    # Test with API URL configured but no key (if API supports it)
    mock_app.config['INVOICE_VALIDATION_API_URL'] = 'https://httpbin.org/get' # Public test API
    mock_app.config['INVOICE_VALIDATION_API_KEY'] = None

    # This direct call will fail because current_app is not available.
    # This test block demonstrates the intended usage within a Flask environment.
    try:
        from flask import Flask
        app_for_test = Flask("TestAppForDataValidator")
        app_for_test.config['INVOICE_VALIDATION_API_URL'] = 'https://httpbin.org/get'
        app_for_test.config['INVOICE_VALIDATION_API_KEY'] = None
        with app_for_test.app_context():
            print("\nTest 3: API call to httpbin.org/get (no key)")
            result = validate_invoice_via_api("INV_HTTPBIN_TEST")
            print(f"API call result to httpbin: {result}") # httpbin will return args, not 'status':'found'
                                                            # So this will likely be 'unknown_response'
    except ImportError:
        print("Flask not available in this test environment to fully simulate current_app.")
    except Exception as e:
        print(f"Error during httpbin test setup or call: {e}")

    # Test case: API URL not configured (simulating by clearing it)
    try:
        from flask import Flask
        app_for_test_no_url = Flask("TestAppNoUrl")
        app_for_test_no_url.config['INVOICE_VALIDATION_API_URL'] = None
        app_for_test_no_url.config['INVOICE_VALIDATION_API_KEY'] = None
        with app_for_test_no_url.app_context():
            print("\nTest 4: API URL deliberately not configured")
            result = validate_invoice_via_api("INV_NOCONFIG_TEST")
            print(f"API call result (no URL): {result}")
    except ImportError:
        print("Flask not available for no URL test.")
    except Exception as e:
        print(f"Error during no URL test: {e}")

    range_results_no_max = validate_range(numeric_data, 'value', min_value=0, expected_type='number')
    print("\nRange validation for 'value' (min 0, no max):")
    if range_results_no_max:
        for issue in range_results_no_max:
            print(issue)
    else:
        print("All applicable values are within range.")

    date_data = [
        {'id': 1, 'event_date': '2023-01-15'},
        {'id': 2, 'event_date': '2023-12-31'},
        {'id': 3, 'event_date': '2024-01-01'}, # Out of range (above max)
        {'id': 4, 'event_date': '2022-12-31'}, # Out of range (below min)
        {'id': 5, 'event_date': '15-01-2023'}, # Invalid format for current basic parser
        {'id': 6, 'event_date': None},
        {'id': 7, 'event_date': datetime(2023, 6, 15).date()} # Already a date object
    ]
    print(f"\nDate Data: {date_data}")
    # Note: min/max for dates should ideally be date objects or strings in YYYY-MM-DD
    range_results_date = validate_range(date_data, 'event_date',
                                        min_value='2023-01-01',
                                        max_value='2023-12-30', # Max is exclusive for this setup
                                        expected_type='date')
    print("Range validation for 'event_date' (2023-01-01 to 2023-12-30):")
    if range_results_date:
        for issue in range_results_date:
            print(issue)
    else:
        print("All applicable values are within range.")

    duplicates_amount = validate_uniqueness(sample_data_1, 'Amount')
    print(f"\nUniqueness validation for 'Amount':") # Amounts can be non-unique, expect no errors
    if duplicates_amount:
        for dup in duplicates_amount:
            print(dup)
    else:
        print("No duplicates found for 'Amount'.") # This should be the case

    sample_data_2 = [
        {'id': 1, 'email': 'test1@example.com'},
        {'id': 2, 'email': 'test2@example.com'},
        {'id': 3, 'email': 'test1@example.com'}, # Duplicate email
        {'id': 4, 'email': None},
        {'id': 5, 'email': None}, # Duplicate None
        {'id': 6, 'email': ""},
        {'id': 7, 'email': ""}  # Duplicate empty string
    ]
    print(f"\nSample Data 2: {sample_data_2}")
    duplicates_email = validate_uniqueness(sample_data_2, 'email')
    print(f"Uniqueness validation for 'email':")
    if duplicates_email:
        for dup in duplicates_email:
            print(dup)
    else:
        print("No duplicates found for 'email'.")

    sample_data_3 = [
        {'name': 'Alice'}, {'name': 'Bob'}, {'name': 'Charlie'}
    ]
    print(f"\nSample Data 3 (all unique): {sample_data_3}")
    duplicates_name = validate_uniqueness(sample_data_3, 'name')
    print(f"Uniqueness validation for 'name':")
    if duplicates_name:
        for dup in duplicates_name:
            print(dup)
    else:
        print("No duplicates found for 'name'.")

    sample_data_4_missing_field = [
        {'InvoiceID': 'INV100'},
        {'Amount': 200}, # Missing InvoiceID
        {'InvoiceID': 'INV100'}
    ]
    print(f"\nSample Data 4 (missing field in one row): {sample_data_4_missing_field}")
    # When 'InvoiceID' is checked, the row {'Amount': 200} will have value=None for 'InvoiceID'.
    # If another row also has value=None for 'InvoiceID', they will be considered duplicates of None.
    duplicates_inv_id_missing = validate_uniqueness(sample_data_4_missing_field, 'InvoiceID')
    print(f"Uniqueness validation for 'InvoiceID' with missing field:")
    if duplicates_inv_id_missing:
        for dup in duplicates_inv_id_missing:
            print(dup)
    else:
        print("No duplicates found for 'InvoiceID'.")
