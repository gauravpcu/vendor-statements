import os
from azure_openai_client import client as azure_oai_client, azure_openai_configured, AZURE_OAI_DEPLOYMENT_NAME
import logging
import json

logger = logging.getLogger('upload_history')

FIELD_DEFINITIONS_HM = {}

def initialize_header_mapper(field_definitions):
    """Initialize the header_mapper with field definitions"""
    global FIELD_DEFINITIONS_HM
    FIELD_DEFINITIONS_HM = field_definitions
    logger.info(f"header_mapper initialized with {len(FIELD_DEFINITIONS_HM)} field definitions.")

def map_header_to_field(header_text, target_fields_with_aliases=None):
    """
    Maps a single header text to a standard field name using Azure OpenAI.
    Uses target_fields_with_aliases if provided, otherwise uses globally initialized FIELD_DEFINITIONS_HM.
    """
    current_target_fields = target_fields_with_aliases if target_fields_with_aliases is not None else FIELD_DEFINITIONS_HM
    if not current_target_fields:
        logger.error("map_header_to_field called before FIELD_DEFINITIONS_HM was initialized or provided.")
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': header_text, 'error': 'Field definitions not available.', 'method': 'error'}
    
    original_header = header_text

    # Check for direct alias match first for higher confidence
    # Assuming current_target_fields is {field_name: {"aliases": [...]}}
    for field, details in current_target_fields.items(): 
        aliases = details.get('aliases', []) # Use .get() for safety
        if header_text.lower() in [alias.lower() for alias in aliases]:
            logger.info(f"Direct alias match for '{header_text}': '{field}'")
            return {'mapped_field': field, 'confidence_score': 98, 'original_header': original_header, 'method': 'alias'}

    if not azure_openai_configured or not azure_oai_client:
        logger.warning(f"Azure OpenAI not configured. Cannot map header: {header_text}")
        # Attempt fallback to simple keyword matching if AI is not available
        for field, details in current_target_fields.items():
            aliases = details.get('aliases', [])
            if header_text.lower() in field.lower() or any(header_text.lower() in alias.lower() for alias in aliases):
                 logger.info(f"Fallback keyword match for '{header_text}': '{field}'")
                 return {'mapped_field': field, 'confidence_score': 40, 'original_header': original_header, 'method': 'fallback_keyword'}
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': original_header, 'error': 'Azure OpenAI not configured, no fallback match', 'method': 'none'}

    standard_field_names = list(current_target_fields.keys())
    
    prompt_messages = [
        {"role": "system", "content": "You are an expert data analyst specializing in financial documents. Your task is to map a given column header to one of the predefined standard field names."},
        {"role": "user", "content": f"Standard Field Names: {json.dumps(standard_field_names)}\nColumn Header: \"{header_text}\"\nWhich standard field name does this column header best map to? Respond with only the single best matching standard field name from the list provided. If no suitable match is found, respond with \"N/A\"."}
    ]

    try:
        logger.info(f"Attempting to map header '{header_text}' using Azure OpenAI (Chat) deployment '{AZURE_OAI_DEPLOYMENT_NAME}'.")
        response = azure_oai_client.chat.completions.create(
            model=AZURE_OAI_DEPLOYMENT_NAME,
            messages=prompt_messages,
            max_tokens=50, 
            temperature=0.0,
        )
        
        raw_suggested_field = response.choices[0].message.content.strip()
        suggested_field_cleaned = raw_suggested_field.replace('"', '').replace("\n", " ").replace("'", "").strip()
        
        logger.info(f"Azure OpenAI response for header '{header_text}': Raw='{raw_suggested_field}', Cleaned='{suggested_field_cleaned}'")

        if suggested_field_cleaned in standard_field_names:
            return {'mapped_field': suggested_field_cleaned, 'confidence_score': 95, 'original_header': original_header, 'method': 'ai'}
        elif suggested_field_cleaned == "N/A":
            return {'mapped_field': 'N/A', 'confidence_score': 90, 'original_header': original_header, 'message': 'AI determined no suitable match.', 'method': 'ai_no_match'}
        else:
            for std_field in standard_field_names:
                if suggested_field_cleaned.lower() in std_field.lower() or std_field.lower() in suggested_field_cleaned.lower():
                    logger.warning(f"LLM suggested field '{suggested_field_cleaned}' for header '{header_text}', which is not an exact match but found a close standard field '{std_field}'. Using '{std_field}'.")
                    return {'mapped_field': std_field, 'confidence_score': 75, 'original_header': original_header, 'message': f"LLM suggested '{suggested_field_cleaned}', matched to '{std_field}'", 'method': 'ai_close_match'}
            
            logger.warning(f"LLM suggested field '{suggested_field_cleaned}' for header '{header_text}', which is not a recognized standard field, N/A, nor a close match.")
            return {'mapped_field': f"Unknown: {suggested_field_cleaned}", 'confidence_score': 15, 'original_header': original_header, 'message': f"LLM suggested an unrecognized or non-matching field: '{suggested_field_cleaned}'", 'method': 'llm_unknown_suggestion'}

    except Exception as api_err: 
        logger.error(f"Azure OpenAI API Error for header '{header_text}': {api_err}", exc_info=True)
        for field, details in current_target_fields.items():
            aliases = details.get('aliases', [])
            if header_text.lower() in field.lower() or any(header_text.lower() in alias.lower() for alias in aliases):
                 logger.info(f"Fallback (post-API error) keyword match for '{header_text}': '{field}'")
                 return {'mapped_field': field, 'confidence_score': 35, 'original_header': original_header, 'method': 'fallback_keyword_post_error'}
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': original_header, 'error': f"OpenAI API Error: {str(api_err)}, no fallback match", 'method': 'error_openai_api_no_fallback'}

def generate_mappings(extracted_headers, target_fields_with_aliases=None):
    """
    Generates mappings for a list of extracted headers.
    Uses target_fields_with_aliases if provided, otherwise uses globally initialized FIELD_DEFINITIONS_HM.
    """
    current_target_fields = target_fields_with_aliases if target_fields_with_aliases is not None else FIELD_DEFINITIONS_HM
    if not current_target_fields: 
        logger.error("generate_mappings called before FIELD_DEFINITIONS_HM was initialized or provided.")
        return [{'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': str(h), 'error': 'Field definitions not available.', 'method': 'error'} for h in extracted_headers]

    if not extracted_headers:
        return []

    mappings = []
    for header in extracted_headers:
        if isinstance(header, str): 
            mapping_result = map_header_to_field(header, current_target_fields)
            mappings.append(mapping_result)
        else:
            logger.warning(f"Encountered non-string header: {header} (type: {type(header)}). Attempting to convert to string.")
            try:
                str_header = str(header)
                mapping_result = map_header_to_field(str_header, current_target_fields)
                mappings.append(mapping_result)
            except Exception as e_conv:
                logger.error(f"Could not convert header {header} to string or map it: {e_conv}")
                mappings.append({'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': str(header), 'error': 'Invalid header type, conversion failed', 'method': 'error_type_conversion'})
    return mappings

def apply_learned_preferences(mappings, preferences):
    updated_mappings = []
    for m in mappings:
        preferred_field = preferences.get(m['original_header'])
        if preferred_field and preferred_field in FIELD_DEFINITIONS_HM: 
            if m['mapped_field'] != preferred_field:
                logger.info(f"Applying learned preference for '{m['original_header']}': changing from '{m['mapped_field']}' to '{preferred_field}'")
                m['mapped_field'] = preferred_field
                m['confidence_score'] = 99 
                m['method'] = 'learned_preference'
        updated_mappings.append(m)
    return updated_mappings
