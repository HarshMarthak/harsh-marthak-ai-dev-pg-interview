import os
import json
import logging
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import ValidationError
from schema import PromotionSchema

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment & API Setup
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.critical("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
    exit(1)

client = genai.Client(api_key=api_key)

# The product text provided in the task
INPUT_TEXT = """
Ariel 3-in-1 Pods will be on promotion at Tesco and Asda from the first of April through to the thirtieth, offering shoppers a twenty percent saving off the standard shelf price. This promotion does not apply to convenience stores.
"""

def get_extraction_prompt(text, error_msg=None, failed_json=None):
    """
    Constructs a prompt with strict boundary delimiters and a feedback loop for retries.
    """
    current_year = datetime.now().year
    
    base_prompt = f"""
    Extract promotion details from the text below into a structured JSON format.
    
    Rules:
    1. Dates must be ISO 8601 (YYYY-MM-DD). Use the year {current_year} if not specified.
    2. discount_percentage must be an integer (extract from text like 'fifty percent or 50 %').
    3. eligible_retailers must be a list of strings.
    4. excluded_store_formats must capture any store types explicitly excluded in the text.
    5. Return ONLY valid JSON. No markdown formatting, no backticks, no preamble.

    Target Schema:
    {json.dumps(PromotionSchema.model_json_schema())}

    Text to process:
    \"\"\"{text}\"\"\"
    """
    
    if error_msg:
        return base_prompt + f"\n\nCRITICAL: Your previous attempt failed validation.\nERROR: {error_msg}\nFAILED OUTPUT: {failed_json}\nPlease correct the format and try again."
    
    return base_prompt

def run_extraction():
    max_retries = 3
    current_error = None
    last_output = None

    for attempt in range(max_retries + 1):
        logger.info(f"Extraction attempt {attempt + 1}/{max_retries + 1}")
        
        prompt = get_extraction_prompt(INPUT_TEXT, current_error, last_output)
        
        try:
            #Google GenAI SDK syntax with system instructions
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a JSON-only extraction engine. You never provide conversational text.",
                    temperature=0.1 # Low temperature for deterministic data extraction
                )
            )
            
            # Cleaning potential markdown formatting if the LLM ignores instructions
            raw_text = response.text.strip().replace("```json", "").replace("```", "")
            
            # JSON Parsing
            data = json.loads(raw_text)
            
            # Pydantic Validation
            validated_data = PromotionSchema(**data)
            
            logger.info("Extraction and validation successful.")
            print("\n--- FINAL VALIDATED JSON RESULT ---")
            print(validated_data.model_dump_json(indent=2))
            return validated_data

        except (json.JSONDecodeError, ValidationError) as e:
            current_error = str(e)
            last_output = response.text if 'response' in locals() else "No response"
            logger.error(f"Attempt {attempt + 1} failed: {current_error}")
            
            if attempt == max_retries:
                logger.critical("Maximum retries reached. Could not extract valid data.")
                print("\nError: The LLM could not produce valid data after 3 retries.")

if __name__ == "__main__":
    run_extraction()