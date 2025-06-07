import os
import openai
import logging
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# Get a logger instance (consistent with app.py logging)
logger = logging.getLogger('upload_history')

AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT")
AZURE_OAI_KEY = os.getenv("AZURE_OAI_KEY")
AZURE_OAI_DEPLOYMENT_NAME = os.getenv("AZURE_OAI_DEPLOYMENT_NAME") # Model deployment name (e.g., for gpt-3.5-turbo or text-embedding-ada-002)
AZURE_OAI_API_VERSION = os.getenv("AZURE_OAI_API_VERSION", "2023-05-15") # Adjust as per your Azure OpenAI service version

client = None
azure_openai_configured = False

if AZURE_OAI_ENDPOINT and AZURE_OAI_KEY and AZURE_OAI_DEPLOYMENT_NAME:
    try:
        client = openai.AzureOpenAI(
            azure_endpoint=AZURE_OAI_ENDPOINT,
            api_key=AZURE_OAI_KEY,
            api_version=AZURE_OAI_API_VERSION
        )
        azure_openai_configured = True
        logger.info("Azure OpenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {e}")
        # client remains None, azure_openai_configured remains False
else:
    logger.warning("Azure OpenAI environment variables (AZURE_OAI_ENDPOINT, AZURE_OAI_KEY, AZURE_OAI_DEPLOYMENT_NAME) are not fully set. AI features will be limited.")

def test_azure_openai_connection():
    """
    Tests the Azure OpenAI connection with a simple API call.
    """
    if not client:
        message = "Azure OpenAI client is not configured. Skipping connection test."
        logger.warning(message)
        return {"success": False, "message": message, "details": "Configuration missing."}

    try:
        # A simple, low-cost request: list models (if permitted by policy) or a tiny completion.
        # Using a simple completion request as it's more universally available.
        # Ensure the AZURE_OAI_DEPLOYMENT_NAME is for a completions model if using this test.
        logger.info(f"Attempting test completion with deployment: {AZURE_OAI_DEPLOYMENT_NAME}")
        response = client.completions.create(
            model=AZURE_OAI_DEPLOYMENT_NAME, # This needs to be a completions model deployment
            prompt="What is 1+1?",
            max_tokens=5,
            temperature=0
        )
        # For ChatCompletions model, the call would be:
        # response = client.chat.completions.create(
        # model=AZURE_OAI_DEPLOYMENT_NAME,
        # messages=[{"role": "user", "content": "What is 1+1?"}],
        # max_tokens=5
        # )
        message = f"Azure OpenAI connection test successful. Response: {response.choices[0].text.strip()}"
        logger.info(message)
        return {"success": True, "message": "Connection successful.", "details": response.choices[0].text.strip()}
    except openai.APIAuthenticationError as e:
        error_message = f"Azure OpenAI API Authentication Error: {e}"
        logger.error(error_message)
        return {"success": False, "message": "Authentication failed.", "details": str(e)}
    except openai.APIConnectionError as e:
        error_message = f"Azure OpenAI API Connection Error: {e}"
        logger.error(error_message)
        return {"success": False, "message": "Connection error.", "details": str(e)}
    except openai.RateLimitError as e:
        error_message = f"Azure OpenAI API Rate Limit Error: {e}"
        logger.error(error_message)
        return {"success": False, "message": "Rate limit exceeded.", "details": str(e)}
    except openai.APIError as e: # Catch-all for other OpenAI API errors
        error_message = f"Azure OpenAI API Error: {e}"
        logger.error(error_message)
        return {"success": False, "message": "API error.", "details": str(e)}
    except Exception as e: # Catch any other exceptions
        error_message = f"An unexpected error occurred during Azure OpenAI connection test: {e}"
        logger.error(error_message)
        return {"success": False, "message": "Unexpected error.", "details": str(e)}

if __name__ == '__main__':
    # This allows direct testing of the client if run as a script
    # For this to work, you'd need to set up basic logging if you want to see logger outputs
    # Or just rely on print statements for this direct test.
    print("Attempting to test Azure OpenAI connection...")
    # Set up a basic logger for standalone testing
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # You would need to set the environment variables for this test to run meaningfully.
    # Example:
    # export AZURE_OAI_ENDPOINT="your_endpoint"
    # export AZURE_OAI_KEY="your_key"
    # export AZURE_OAI_DEPLOYMENT_NAME="your_deployment_name" # (Ensure this is a completions model for the test)

    test_result = test_azure_openai_connection()
    print(f"Test Result: {test_result}")
