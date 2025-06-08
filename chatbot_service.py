import os
import json
import logging
from azure_openai_client import client as azure_oai_client, azure_openai_configured, AZURE_OAI_DEPLOYMENT_NAME

logger = logging.getLogger('upload_history')

FIELD_DEFINITIONS_CS = {} # Global for chatbot service

def initialize_chatbot_service(field_definitions):
    """Initialize the chatbot_service with field definitions"""
    global FIELD_DEFINITIONS_CS
    FIELD_DEFINITIONS_CS = field_definitions
    logger.info(f"chatbot_service initialized with {len(FIELD_DEFINITIONS_CS)} field definitions.")

def get_mapping_suggestions(original_header, current_mapped_field, all_field_definitions=None):
    """
    Generates mapping suggestions for a given original header.
    Uses Azure OpenAI if configured, otherwise falls back to alias-based logic.
    Uses the globally initialized FIELD_DEFINITIONS_CS if all_field_definitions is not provided.
    """
    target_definitions = all_field_definitions if all_field_definitions is not None else FIELD_DEFINITIONS_CS
    if not target_definitions:
        logger.error("get_mapping_suggestions called before FIELD_DEFINITIONS_CS was initialized or provided.")
        return []
    
    suggestions = []

    if azure_openai_configured and azure_oai_client:
        standard_field_names = list(target_definitions.keys())
        prompt = f"""Context: A user is reviewing field mappings for a document. For the original header "{original_header}", it is currently mapped to "{current_mapped_field}". The user is requesting alternative suggestions.
Instruction: Please suggest 2-3 alternative standard field names from the following list that "{original_header}" could map to. Exclude "{current_mapped_field}" from your suggestions. For each suggestion, provide a brief reason (10-15 words).
Standard Field Names: {json.dumps(standard_field_names)}
Format hint: Respond ONLY with a valid JSON array of objects, where each object has keys "suggested_field" and "reason". For example: [{{"suggested_field": "FIELD_NAME_1", "reason": "..."}}, {{"suggested_field": "FIELD_NAME_2", "reason": "..."}}]
If no other suitable suggestions are found from the list, return an empty JSON array [].
"""
        try:
            logger.info(f"Requesting mapping suggestions from Azure OpenAI for header: '{original_header}', current map: '{current_mapped_field}'")
            response = azure_oai_client.chat.completions.create( # Use chat.completions.create
                model=AZURE_OAI_DEPLOYMENT_NAME,
                messages=[ # Chat models expect a messages array
                    {"role": "system", "content": "You are an AI assistant helping with field mapping."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.2,
                stop=None
            )

            raw_response_text = response.choices[0].message.content.strip() # Access content from message
            logger.info(f"Raw Azure OpenAI response for suggestions: {raw_response_text}")

            # Try to parse the JSON response
            try:
                # A common issue is the LLM sometimes includes introductory text before the JSON.
                # Try to find the start of the JSON array.
                json_start_index = raw_response_text.find('[')
                json_end_index = raw_response_text.rfind(']') + 1

                if json_start_index != -1 and json_end_index != -1 :
                    json_response_str = raw_response_text[json_start_index:json_end_index]
                    suggestions = json.loads(json_response_str)
                    # Filter out the current_mapped_field just in case LLM includes it
                    suggestions = [s for s in suggestions if s.get('suggested_field') != current_mapped_field]
                    logger.info(f"Successfully parsed suggestions from LLM: {suggestions}")
                    if suggestions:
                        return suggestions # Return early if LLM provides valid suggestions
                else:
                    logger.warning(f"Could not find JSON array in LLM response for '{original_header}'. Response: {raw_response_text}")

            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse JSON response from LLM for suggestions for '{original_header}'. Error: {je}. Response: {raw_response_text}")
            # If LLM fails or returns empty/unparsable, fall through to fallback logic

        except Exception as e:
            logger.error(f"Error calling Azure OpenAI for suggestions for '{original_header}': {e}", exc_info=True)
            # Fall through to fallback logic

    # Fallback Logic (or if Azure OpenAI not configured/fails/returns no valid suggestions)
    logger.info(f"Using fallback logic for suggestions for header: '{original_header}'")
    fallback_suggestions = []
    original_header_lower = original_header.lower()
    original_header_keywords = set(original_header_lower.replace("_", " ").replace("-", " ").split())

    for field_name, details in target_definitions.items(): # Use target_definitions
        # Ensure aliases are fetched correctly from the details dictionary
        aliases = details.get('aliases', []) if isinstance(details, dict) else []
        if field_name == current_mapped_field:
            continue # Skip the currently mapped field

        # Check against field name itself
        field_name_lower = field_name.lower()
        field_name_keywords = set(field_name_lower.replace("_", " ").replace("-", " ").split())
        if original_header_keywords.intersection(field_name_keywords):
             fallback_suggestions.append({
                'suggested_field': field_name,
                'reason': f'Shares keywords with standard field name.'
            })
             if len(fallback_suggestions) >=3: break # Limit suggestions
             continue # Move to next field_name if matched

        # Check against aliases
        for alias in aliases:
            alias_lower = alias.lower()
            alias_keywords = set(alias_lower.replace("_", " ").replace("-", " ").split())

            # More sophisticated fuzzy matching could be added here later
            if original_header_keywords.intersection(alias_keywords):
                if not any(s['suggested_field'] == field_name for s in fallback_suggestions): # Avoid duplicates for same field
                    fallback_suggestions.append({
                        'suggested_field': field_name,
                        'reason': f'Shares keywords with alias: "{alias}".'
                    })
                break # Found a matching alias for this field_name, move to next field_name

        if len(fallback_suggestions) >= 3: # Limit total fallback suggestions
            break

    if not suggestions and not fallback_suggestions: # If LLM failed and fallback also found nothing
        logger.info(f"No suggestions found for header '{original_header}' via LLM or fallback.")
        return [{'suggested_field': 'N/A', 'reason': 'No alternative suggestions found.'}]

    return fallback_suggestions if not suggestions else suggestions # Prefer LLM if it had any, else fallback.

if __name__ == '__main__':
    # Basic testing (requires FIELD_DEFINITIONS to be available if app.py isn't running)
    # For standalone testing, you might mock FIELD_DEFINITIONS or ensure app context is available.
    logging.basicConfig(level=logging.INFO)

    # Mock FIELD_DEFINITIONS for standalone testing as it's no longer globally imported
    FIELD_DEFINITIONS_MOCK = {
        "InvoiceID": {"aliases": ["Invoice ID", "Invoice Number", "Inv No", "Reference"], "description": "...", "expected_type": "string"},
        "InvoiceDate": {"aliases": ["Invoice Date", "Date Issued", "Inv Date", "Date"], "description": "...", "expected_type": "date"},
        "TotalAmount": {"aliases": ["Total Amount", "Amount Due", "Total", "Net Amount"], "description": "...", "expected_type": "currency"},
        "VendorName": {"aliases": ["Vendor", "Supplier", "Seller Name"], "description": "...", "expected_type": "string"}
    }
    print("Using MOCKED FIELD_DEFINITIONS for chatbot_service.py standalone test, as global import from app.py is removed.")


    test_header = "Invoice Dt"
    current_map = "InvoiceDate"
    print(f"\nTesting suggestions for: '{test_header}' (currently '{current_map}')")
    initialize_chatbot_service(FIELD_DEFINITIONS_MOCK) # Initialize before test
    suggs = get_mapping_suggestions(test_header, current_map)
    print("Suggestions:", json.dumps(suggs, indent=2))

    test_header_2 = "Total Val"
    current_map_2 = "SubTotal" # Example, user wants alternatives for "Total Val" if not SubTotal
    print(f"\nTesting suggestions for: '{test_header_2}' (currently '{current_map_2}')")
    suggs_2 = get_mapping_suggestions(test_header_2, current_map_2)
    print("Suggestions:", json.dumps(suggs_2, indent=2))

    test_header_3 = "Supplier Company"
    current_map_3 = "InvoiceID"
    print(f"\nTesting suggestions for: '{test_header_3}' (currently '{current_map_3}')")
    suggs_3 = get_mapping_suggestions(test_header_3, current_map_3)
    print("Suggestions:", json.dumps(suggs_3, indent=2))

    # Test case where no suggestions should be found easily (apart from current_map)
    test_header_4 = "Unique Header XYZ"
    current_map_4 = "InvoiceID"
    print(f"\nTesting suggestions for: '{test_header_4}' (currently '{current_map_4}')")
    # Pass the mock definitions to the test call
    initialize_chatbot_service(FIELD_DEFINITIONS_MOCK) # Initialize before test
    suggs_4 = get_mapping_suggestions(test_header_4, current_map_4)
    print("Suggestions:", json.dumps(suggs_4, indent=2))
