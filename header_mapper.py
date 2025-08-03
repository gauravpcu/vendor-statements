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
    Enhanced header mapping using Azure OpenAI with improved intelligence.
    Uses target_fields_with_aliases if provided, otherwise uses globally initialized FIELD_DEFINITIONS_HM.
    """
    current_target_fields = target_fields_with_aliases if target_fields_with_aliases is not None else FIELD_DEFINITIONS_HM
    if not current_target_fields:
        logger.error("map_header_to_field called before FIELD_DEFINITIONS_HM was initialized or provided.")
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': header_text, 'error': 'Field definitions not available.', 'method': 'error'}
    
    original_header = header_text

    # Step 1: Check for exact alias match (highest confidence)
    for field, details in current_target_fields.items(): 
        aliases = details.get('aliases', [])
        if header_text.lower() in [alias.lower() for alias in aliases]:
            logger.info(f"Direct alias match for '{header_text}': '{field}'")
            return {'mapped_field': field, 'confidence_score': 98, 'original_header': original_header, 'method': 'alias'}

    # Step 2: Check for partial alias match (high confidence)
    for field, details in current_target_fields.items():
        aliases = details.get('aliases', [])
        for alias in aliases:
            if (header_text.lower() in alias.lower() or alias.lower() in header_text.lower()) and len(header_text) > 3:
                logger.info(f"Partial alias match for '{header_text}': '{field}' (via alias '{alias}')")
                return {'mapped_field': field, 'confidence_score': 85, 'original_header': original_header, 'method': 'partial_alias'}

    # Step 3: Use Azure OpenAI for intelligent mapping
    if not azure_openai_configured or not azure_oai_client:
        logger.warning(f"Azure OpenAI not configured. Using fallback matching for: {header_text}")
        # Enhanced fallback matching
        best_match = None
        best_score = 0
        
        for field, details in current_target_fields.items():
            aliases = details.get('aliases', [])
            # Check field name similarity
            if header_text.lower() in field.lower() or field.lower() in header_text.lower():
                score = 60 if header_text.lower() == field.lower() else 45
                if score > best_score:
                    best_match = field
                    best_score = score
            
            # Check alias similarity
            for alias in aliases:
                if header_text.lower() in alias.lower() or alias.lower() in header_text.lower():
                    score = 50 if len(header_text) > 5 else 35
                    if score > best_score:
                        best_match = field
                        best_score = score
        
        if best_match:
            logger.info(f"Enhanced fallback match for '{header_text}': '{best_match}' (score: {best_score})")
            return {'mapped_field': best_match, 'confidence_score': best_score, 'original_header': original_header, 'method': 'enhanced_fallback'}
        
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': original_header, 'error': 'Azure OpenAI not configured, no fallback match', 'method': 'none'}

    # Step 4: Enhanced Azure OpenAI mapping with better context
    standard_field_names = list(current_target_fields.keys())
    
    # Create detailed field context for better AI understanding
    field_context = {}
    for field, details in current_target_fields.items():
        field_context[field] = {
            "description": details.get('description', ''),
            "aliases": details.get('aliases', [])[:5],  # Limit to top 5 aliases for context
            "type": details.get('expected_type', 'string')
        }
    
    prompt_messages = [
        {
            "role": "system", 
            "content": """You are an expert data analyst specializing in financial documents, invoices, and vendor statements. 
            Your task is to intelligently map column headers from various document formats to standardized field names.
            
            Consider these factors when mapping:
            1. Semantic meaning (what the field represents)
            2. Common business terminology variations
            3. Abbreviations and shortened forms
            4. Multi-language variations
            5. Context of financial/invoice documents
            
            Be confident in your mappings when there's clear semantic alignment, even if the exact wording differs."""
        },
        {
            "role": "user", 
            "content": f"""Map this column header to the most appropriate standard field:

Column Header: "{header_text}"

Available Standard Fields with Context:
{json.dumps(field_context, indent=2)}

Instructions:
- Respond with ONLY the exact standard field name that best matches
- Consider semantic meaning, not just exact text matching
- If no reasonable match exists, respond with "N/A"
- Be confident with mappings that make business sense

Standard Field Names: {json.dumps(standard_field_names)}"""
        }
    ]

    try:
        logger.info(f"Attempting intelligent mapping for header '{header_text}' using Azure OpenAI deployment '{AZURE_OAI_DEPLOYMENT_NAME}'.")
        response = azure_oai_client.chat.completions.create(
            model=AZURE_OAI_DEPLOYMENT_NAME,
            messages=prompt_messages,
            max_tokens=100,  # Increased for better responses
            temperature=0.1,  # Slight temperature for more natural responses
        )
        
        raw_suggested_field = response.choices[0].message.content.strip()
        suggested_field_cleaned = raw_suggested_field.replace('"', '').replace("\n", " ").replace("'", "").strip()
        
        logger.info(f"Azure OpenAI intelligent mapping for '{header_text}': '{suggested_field_cleaned}'")

        # Exact match (highest confidence)
        if suggested_field_cleaned in standard_field_names:
            confidence = 95
            # Boost confidence for common business terms
            business_indicators = ['invoice', 'amount', 'total', 'date', 'number', 'vendor', 'description']
            if any(indicator in header_text.lower() for indicator in business_indicators):
                confidence = 97
            
            logger.info(f"✅ Exact AI match: '{header_text}' → '{suggested_field_cleaned}' (confidence: {confidence}%)")
            return {'mapped_field': suggested_field_cleaned, 'confidence_score': confidence, 'original_header': original_header, 'method': 'ai_exact'}
        
        # No match determined by AI
        elif suggested_field_cleaned == "N/A":
            logger.info(f"🤖 AI determined no suitable match for '{header_text}'")
            return {'mapped_field': 'N/A', 'confidence_score': 90, 'original_header': original_header, 'message': 'AI determined no suitable match.', 'method': 'ai_no_match'}
        
        # Fuzzy matching for close suggestions
        else:
            best_match = None
            best_score = 0
            
            for std_field in standard_field_names:
                # Check for partial matches
                if suggested_field_cleaned.lower() in std_field.lower():
                    score = 80
                elif std_field.lower() in suggested_field_cleaned.lower():
                    score = 75
                elif any(word in std_field.lower() for word in suggested_field_cleaned.lower().split()):
                    score = 70
                else:
                    continue
                
                if score > best_score:
                    best_match = std_field
                    best_score = score
            
            if best_match and best_score >= 70:
                logger.info(f"🔍 AI fuzzy match: '{header_text}' → '{best_match}' (suggested: '{suggested_field_cleaned}', confidence: {best_score}%)")
                return {'mapped_field': best_match, 'confidence_score': best_score, 'original_header': original_header, 'message': f"AI suggested '{suggested_field_cleaned}', matched to '{best_match}'", 'method': 'ai_fuzzy'}
            
            # No good match found
            logger.warning(f"❌ AI suggested unrecognized field '{suggested_field_cleaned}' for header '{header_text}'")
            return {'mapped_field': 'N/A', 'confidence_score': 20, 'original_header': original_header, 'message': f"AI suggested unrecognized field: '{suggested_field_cleaned}'", 'method': 'ai_unrecognized'}

    except Exception as api_err: 
        logger.error(f"Azure OpenAI API Error for header '{header_text}': {api_err}", exc_info=True)
        for field, details in current_target_fields.items():
            aliases = details.get('aliases', [])
            if header_text.lower() in field.lower() or any(header_text.lower() in alias.lower() for alias in aliases):
                 logger.info(f"Fallback (post-API error) keyword match for '{header_text}': '{field}'")
                 return {'mapped_field': field, 'confidence_score': 35, 'original_header': original_header, 'method': 'fallback_keyword_post_error'}
        return {'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': original_header, 'error': f"OpenAI API Error: {str(api_err)}, no fallback match", 'method': 'error_openai_api_no_fallback'}

def generate_intelligent_batch_mapping(extracted_headers, target_fields_with_aliases=None):
    """
    Enhanced batch mapping with context awareness and intelligent suggestions.
    Uses Azure OpenAI to understand the document context and provide better mappings.
    """
    current_target_fields = target_fields_with_aliases if target_fields_with_aliases is not None else FIELD_DEFINITIONS_HM
    if not current_target_fields: 
        logger.error("generate_intelligent_batch_mapping called before FIELD_DEFINITIONS_HM was initialized.")
        return [{'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': str(h), 'error': 'Field definitions not available.', 'method': 'error'} for h in extracted_headers]

    if not extracted_headers:
        return []

    logger.info(f"🤖 Starting intelligent batch mapping for {len(extracted_headers)} headers")

    # First, try individual mapping for each header
    individual_mappings = []
    for header in extracted_headers:
        if isinstance(header, str): 
            mapping_result = map_header_to_field(header, current_target_fields)
            individual_mappings.append(mapping_result)
        else:
            logger.warning(f"Converting non-string header: {header}")
            try:
                str_header = str(header)
                mapping_result = map_header_to_field(str_header, current_target_fields)
                individual_mappings.append(mapping_result)
            except Exception as e_conv:
                logger.error(f"Could not convert header {header}: {e_conv}")
                individual_mappings.append({'mapped_field': 'N/A', 'confidence_score': 0, 'original_header': str(header), 'error': 'Invalid header type', 'method': 'error_type_conversion'})

    # Analyze mapping quality and provide context-aware improvements
    high_confidence_mappings = [m for m in individual_mappings if m.get('confidence_score', 0) >= 80]
    low_confidence_mappings = [m for m in individual_mappings if m.get('confidence_score', 0) < 80]
    
    logger.info(f"📊 Mapping analysis: {len(high_confidence_mappings)} high-confidence, {len(low_confidence_mappings)} low-confidence")

    # If we have many low-confidence mappings, try batch context mapping
    if len(low_confidence_mappings) > 2 and azure_openai_configured and azure_oai_client:
        try:
            improved_mappings = _improve_mappings_with_context(individual_mappings, extracted_headers, current_target_fields)
            if improved_mappings:
                logger.info("✨ Applied context-aware mapping improvements")
                return improved_mappings
        except Exception as e:
            logger.warning(f"Context-aware improvement failed, using individual mappings: {e}")

    return individual_mappings

def _improve_mappings_with_context(mappings, headers, target_fields):
    """
    Use Azure OpenAI to improve mappings by understanding document context.
    """
    try:
        # Prepare context for AI analysis
        low_confidence_headers = [
            {"header": m['original_header'], "current_mapping": m.get('mapped_field', 'N/A'), "confidence": m.get('confidence_score', 0)}
            for m in mappings if m.get('confidence_score', 0) < 80
        ]
        
        if not low_confidence_headers:
            return mappings  # No improvements needed
        
        high_confidence_context = [
            {"header": m['original_header'], "mapping": m['mapped_field']}
            for m in mappings if m.get('confidence_score', 0) >= 80
        ]
        
        standard_fields = list(target_fields.keys())
        
        context_prompt = [
            {
                "role": "system",
                "content": """You are an expert at analyzing financial documents and understanding field relationships.
                Given a set of column headers from a document, improve the field mappings by understanding the document context.
                
                Consider:
                1. Document type patterns (invoice, statement, etc.)
                2. Field relationships and common groupings
                3. Business logic and standard practices
                4. Header naming conventions in the document"""
            },
            {
                "role": "user",
                "content": f"""Analyze these document headers and improve the low-confidence mappings:

All Headers: {headers}

High-Confidence Mappings (for context):
{json.dumps(high_confidence_context, indent=2)}

Low-Confidence Mappings to Improve:
{json.dumps(low_confidence_headers, indent=2)}

Available Standard Fields: {standard_fields}

For each low-confidence mapping, suggest the best standard field or confirm "N/A" if no good match exists.
Respond in JSON format:
{{"improvements": [{{"header": "original_header", "suggested_field": "StandardField", "reason": "explanation"}}]}}"""
            }
        ]
        
        response = azure_oai_client.chat.completions.create(
            model=AZURE_OAI_DEPLOYMENT_NAME,
            messages=context_prompt,
            max_tokens=500,
            temperature=0.2,
        )
        
        ai_response = response.choices[0].message.content.strip()
        logger.info(f"🤖 Context-aware AI response: {ai_response}")
        
        # Parse AI suggestions and apply improvements
        try:
            suggestions = json.loads(ai_response)
            improvements = suggestions.get('improvements', [])
            
            # Apply improvements to mappings
            improved_mappings = mappings.copy()
            for improvement in improvements:
                header = improvement.get('header')
                suggested_field = improvement.get('suggested_field')
                reason = improvement.get('reason', '')
                
                if suggested_field in standard_fields:
                    # Find and update the mapping
                    for i, mapping in enumerate(improved_mappings):
                        if mapping['original_header'] == header:
                            improved_mappings[i] = {
                                'mapped_field': suggested_field,
                                'confidence_score': 88,  # High confidence for AI context improvements
                                'original_header': header,
                                'method': 'ai_context_improved',
                                'message': f"Context-aware improvement: {reason}"
                            }
                            logger.info(f"✨ Improved mapping: '{header}' → '{suggested_field}' ({reason})")
                            break
            
            return improved_mappings
            
        except json.JSONDecodeError:
            logger.warning("Could not parse AI context improvement response")
            return mappings
            
    except Exception as e:
        logger.error(f"Context-aware mapping improvement failed: {e}")
        return mappings

def generate_mappings(extracted_headers, target_fields_with_aliases=None):
    """
    Generates mappings for a list of extracted headers.
    Now uses intelligent batch mapping for better results.
    """
    return generate_intelligent_batch_mapping(extracted_headers, target_fields_with_aliases)

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
