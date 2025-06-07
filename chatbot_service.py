import os
import json
import logging
from azure_openai_client import client as azure_oai_client, azure_openai_configured, AZURE_OAI_DEPLOYMENT_NAME
from app import FIELD_DEFINITIONS # Assuming FIELD_DEFINITIONS is accessible

logger = logging.getLogger('upload_history')

def get_mapping_suggestions(original_header, current_mapped_field, all_field_definitions):
    """
    Generates mapping suggestions for a given original header.
    Uses Azure OpenAI if configured, otherwise falls back to alias-based logic.
    """
    suggestions = []

    if azure_openai_configured and azure_oai_client:
        standard_field_names = list(all_field_definitions.keys())
        prompt = f"""Context: A user is reviewing field mappings for a document. For the original header "{original_header}", it is currently mapped to "{current_mapped_field}". The user is requesting alternative suggestions.
Instruction: Please suggest 2-3 alternative standard field names from the following list that "{original_header}" could map to. Exclude "{current_mapped_field}" from your suggestions. For each suggestion, provide a brief reason (10-15 words).
Standard Field Names: {json.dumps(standard_field_names)}
Format hint: Respond ONLY with a valid JSON array of objects, where each object has keys "suggested_field" and "reason". For example: [{{"suggested_field": "FIELD_NAME_1", "reason": "..."}}, {{"suggested_field": "FIELD_NAME_2", "reason": "..."}}]
If no other suitable suggestions are found from the list, return an empty JSON array [].
"""
        try:
            logger.info(f"Requesting mapping suggestions from Azure OpenAI for header: '{original_header}', current map: '{current_mapped_field}'")
            response = azure_oai_client.completions.create( # Or chat.completions.create if using a chat model
                model=AZURE_OAI_DEPLOYMENT_NAME,
                prompt=prompt,
                max_tokens=150, # Increased to allow for a few suggestions with reasons
                temperature=0.2, # Slightly higher for more varied suggestions but still factual
                stop=None # Could add "]" as a stop token if issues with JSON completion
            )

            raw_response_text = response.choices[0].text.strip()
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

    # Simple keyword matching for fallback
    original_header_keywords = set(original_header_lower.replace("_", " ").replace("-", " ").split())

    for field_name, aliases in all_field_definitions.items():
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

    # Mock FIELD_DEFINITIONS for testing
    if not FIELD_DEFINITIONS:
        FIELD_DEFINITIONS_MOCK = {
            "InvoiceID": ["Invoice ID", "Invoice Number", "Inv No", "Reference"],
            "InvoiceDate": ["Invoice Date", "Date Issued", "Inv Date", "Date"],
            "TotalAmount": ["Total Amount", "Amount Due", "Total", "Net Amount"],
            "VendorName": ["Vendor", "Supplier", "Seller Name"]
        }
        print("Using MOCKED FIELD_DEFINITIONS for chatbot_service.py standalone test.")
    else:
        FIELD_DEFINITIONS_MOCK = FIELD_DEFINITIONS
        print("Using FIELD_DEFINITIONS from app.py for chatbot_service.py standalone test.")


    test_header = "Invoice Dt"
    current_map = "InvoiceDate"
    print(f"\nTesting suggestions for: '{test_header}' (currently '{current_map}')")
    suggs = get_mapping_suggestions(test_header, current_map, FIELD_DEFINITIONS_MOCK)
    print("Suggestions:", json.dumps(suggs, indent=2))

    test_header_2 = "Total Val"
    current_map_2 = "SubTotal" # Example, user wants alternatives for "Total Val" if not SubTotal
    print(f"\nTesting suggestions for: '{test_header_2}' (currently '{current_map_2}')")
    suggs_2 = get_mapping_suggestions(test_header_2, current_map_2, FIELD_DEFINITIONS_MOCK)
    print("Suggestions:", json.dumps(suggs_2, indent=2))

    test_header_3 = "Supplier Company"
    current_map_3 = "InvoiceID"
    print(f"\nTesting suggestions for: '{test_header_3}' (currently '{current_map_3}')")
    suggs_3 = get_mapping_suggestions(test_header_3, current_map_3, FIELD_DEFINITIONS_MOCK)
    print("Suggestions:", json.dumps(suggs_3, indent=2))

    # Test case where no suggestions should be found easily (apart from current_map)
    test_header_4 = "Unique Header XYZ"
    current_map_4 = "InvoiceID"
    print(f"\nTesting suggestions for: '{test_header_4}' (currently '{current_map_4}')")
    suggs_4 = get_mapping_suggestions(test_header_4, current_map_4, FIELD_DEFINITIONS_MOCK)
    print("Suggestions:", json.dumps(suggs_4, indent=2))
