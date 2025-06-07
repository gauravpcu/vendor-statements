## Azure OpenAI Configuration

To enable features that use Azure OpenAI (like AI-powered field mapping and chatbot suggestions), you need to configure your Azure OpenAI credentials.

This project uses a `.env` file to manage these credentials securely, preventing them from being accidentally committed to version control.

### Setup Instructions:

1.  **Create a `.env` file:**
    In the root directory of the project, make a copy of the example environment file `.env.example` and rename it to `.env`. You can do this with the following command in your terminal:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Open the newly created `.env` file in a text editor. You will need to replace the placeholder values with your actual Azure OpenAI service details:

    *   `AZURE_OAI_ENDPOINT`: Set this to your specific Azure OpenAI resource's endpoint URL. It usually looks something like `https://YOUR_RESOURCE_NAME.openai.azure.com/`.
    *   `AZURE_OAI_KEY`: Enter your Azure OpenAI API key. This is a secret key used to authenticate your requests.
    *   `AZURE_OAI_DEPLOYMENT_NAME`: Specify the deployment name of your model on Azure. This is the name you gave to your deployed model instance (e.g., `gpt-35-turbo`, `text-embedding-ada-002`, or whatever you named your completion/chat model).
    *   `AZURE_OAI_API_VERSION`: Verify or update this to match the API version supported by your Azure OpenAI resource and the SDK. The default provided in `.env.example` is `2023-05-15`, which is a common version, but you should check the Azure documentation for the most current or appropriate version for your setup.

3.  **Save the `.env` file.**

The `.env` file is listed in the project's `.gitignore` file, which means Git will ignore it, and your sensitive credentials will not be included in commits to the repository.

The application utilizes the `python-dotenv` library, which automatically loads the variables defined in your `.env` file into environment variables when the application starts. If the `.env` file is not present, or if the required Azure OpenAI variables are not set within it, the features of the application that depend on Azure OpenAI will be gracefully disabled or operate in a limited, non-AI mode. You will see log messages indicating if the Azure OpenAI client could not be configured.
