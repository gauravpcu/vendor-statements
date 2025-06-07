import os
from azure_openai_client import client as azure_oai_client, azure_openai_configured, AZURE_OAI_DEPLOYMENT_NAME
from app import FIELD_DEFINITIONS # Importing directly for now
import logging
import json # For parsing potential JSON in response, though unlikely for this prompt

logger = logging.getLogger('upload_history')

def map_header_to_field(header_text, target_fields_with_aliases):
    """
    Maps a single header text to a standard field name using Azure OpenAI.
    """
    original_header = header_text

    # Check for direct alias match first for higher confidence
    for field, aliases in target_fields_with_aliases.items():
        if header_text.lower() in [alias.lower() for alias in aliases]:
            logger.info(f"Direct alias match for '{header_text}': '{field}'")
            return {'mapped_field': field, 'confidence_score': 98, 'original_header': original_header, 'method': 'alias'} # Increased alias confidence

    if not azure_openai_configured or not azure_oai_client:
        logger.warning(f"Azure OpenAI not configured. Cannot map header: {header_text}")
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': original_header, 'error': 'Azure OpenAI not configured', 'method': 'none'}

    standard_field_names = list(target_fields_with_aliases.keys())

    prompt = f"""Context: You are an expert data analyst specializing in financial documents. Your task is to map a given column header to one of the predefined standard field names.
Standard Field Names: {json.dumps(standard_field_names)}
Column Header: "{header_text}"
Which standard field name does this column header best map to? Respond with only the single best matching standard field name from the list provided. If no suitable match is found, respond with "N/A".
"""

    try:
        logger.info(f"Attempting to map header '{header_text}' using Azure OpenAI deployment '{AZURE_OAI_DEPLOYMENT_NAME}'.")
        response = azure_oai_client.completions.create(
            model=AZURE_OAI_DEPLOYMENT_NAME, # Ensure this is a completions model
            prompt=prompt,
            max_tokens=20,  # Enough for a field name
            temperature=0.0, # For deterministic mapping
            stop=None # Could add stop sequences like newline if needed
        )

        raw_suggested_field = response.choices[0].text.strip()
        # Normalize the suggested field: remove potential quotes or extra characters if any.
        # For this prompt, it should be clean, but good practice.
        suggested_field_cleaned = raw_suggested_field.replace('"', '').replace("'", "").strip()

        logger.info(f"Azure OpenAI response for header '{header_text}': Raw='{raw_suggested_field}', Cleaned='{suggested_field_cleaned}'")

        if suggested_field_cleaned in standard_field_names:
            # Model provided a valid standard field name
            return {'mapped_field': suggested_field_cleaned, 'confidence_score': 88, 'original_header': original_header, 'method': 'llm_exact_match'} # Higher confidence for exact LLM match
        elif suggested_field_cleaned == "N/A":
             # LLM explicitly stated no match
             return {'mapped_field': 'N/A', 'confidence_score': 40, 'original_header': original_header, 'message': 'No suitable match found by LLM.', 'method': 'llm_no_match'}
        elif not suggested_field_cleaned or len(suggested_field_cleaned) == 0 : # Check for empty response from LLM
            logger.warning(f"LLM provided an empty or whitespace response for header '{header_text}'.")
            return {'mapped_field': 'N/A', 'confidence_score': 5, 'original_header': original_header, 'message': 'LLM provided an empty response.', 'method': 'llm_empty_response'}
        else:
            # Model provided something, but it's not in our list of standard fields
            logger.warning(f"LLM suggested field '{suggested_field_cleaned}' for header '{header_text}', which is not a recognized standard field.")
            # Store the LLM's raw suggestion if it's not a standard one, for review.
            return {'mapped_field': f"Unknown: {suggested_field_cleaned}", 'confidence_score': 15, 'original_header': original_header, 'message': f"LLM suggested an unrecognized field: '{suggested_field_cleaned}'", 'method': 'llm_unknown_suggestion'}

    except openai.APIError as api_err: # More specific OpenAI error
        logger.error(f"Azure OpenAI API Error for header '{header_text}': {api_err}", exc_info=True)
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': original_header, 'error': f"OpenAI API Error: {str(api_err)}", 'method': 'error_openai_api'}
    except Exception as e: # General exception
        logger.error(f"Error calling Azure OpenAI for header '{header_text}': {e}", exc_info=True)
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': original_header, 'error': f"General Error: {str(e)}", 'method': 'error_general'}


def generate_mappings(extracted_headers, target_fields_with_aliases):
    """
    Generates mappings for a list of extracted headers.
    """
    if not extracted_headers:
        return []

    mappings = []
    for header in extracted_headers:
        if isinstance(header, str): # Ensure header is a string
            mapping_result = map_header_to_field(header, target_fields_with_aliases)
            mappings.append(mapping_result)
        else:
            logger.warning(f"Skipping non-string header found in extracted_headers: {header}")
            mappings.append({'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': str(header), 'error': 'Invalid header format (not a string).', 'method': 'error'})

    return mappings

if __name__ == '__main__':
    # This section is for basic testing if you run the file directly.
    # You'll need to have Azure OpenAI configured and FIELD_DEFINITIONS available.

    # Mock FIELD_DEFINITIONS for standalone testing
    mock_field_defs = {
        "InvoiceID": ["Invoice ID", "Invoice Number", "Inv No"],
        "InvoiceDate": ["Invoice Date", "Date Issued", "Inv Date"],
        "TotalAmount": ["Total Amount", "Amount Due", "Total"]
    }

    # Example headers
    example_headers = ["Invoice Number", "Date", "Total", "Completely Unknown Header", "Inv. Date"]

    print(f"Testing with Azure OpenAI Configured: {azure_openai_configured}")

    # If you want to test without needing app.py running, you might need to
    # temporarily set up basic logging here too, or ensure env vars are set for Azure.
    if not logger.handlers:
         logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Test direct alias matching
    print("\nTesting direct alias matching (OpenAI should not be called):")
    direct_match_header = "Inv No" # Should be InvoiceID
    mapping = map_header_to_field(direct_match_header, mock_field_defs)
    print(f"Header: '{direct_match_header}' -> Mapped: {mapping}")

    if azure_openai_configured:
        print("\nTesting with LLM (if direct alias not found):")
        # Test LLM mapping for a header that's not a direct alias but close
        llm_map_header = "Invoice Dt" # Not a direct alias, expect InvoiceDate from LLM
        mapping = map_header_to_field(llm_map_header, mock_field_defs)
        print(f"Header: '{llm_map_header}' -> Mapped: {mapping}")

        print("\nGenerating mappings for example headers:")
        all_mappings = generate_mappings(example_headers, mock_field_defs)
        for m in all_mappings:
            print(m)
    else:
        print("\nAzure OpenAI not configured. Skipping LLM-dependent tests.")
        print("\nGenerating mappings (will show 'Azure OpenAI not configured' for non-alias):")
        all_mappings = generate_mappings(example_headers, mock_field_defs)
        for m in all_mappings:
            print(m)
