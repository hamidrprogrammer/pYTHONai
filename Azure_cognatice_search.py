import base64
import json
import os
from openai import AzureOpenAI
from fastapi import FastAPI, HTTPException
from azure.storage.blob import BlobServiceClient
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods, or specify ['POST']
    allow_headers=["*"],  # Allows all headers
)
# Replace with your actual Azure Blob Storage credentials
STORAGE_ACCOUNT_NAME = 'alfalavastorge'
STORAGE_ACCOUNT_KEY = 'leVXl7PECLEP5tpDWwH18bXOPZCkvGWdRosfdUy0U0UvKbAIGgV3poNYimVpRBgv13lgCkgY3k+7+AStNrWTOQ=='
CONTAINER_NAME = 'alfalava'
BLOB_NAME = "8347-ALFA LAVAL-Lifting lugs CCH32 .pdf"

# Create the blob service client using connection string
blob_service_client = BlobServiceClient.from_connection_string(
    f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT_NAME};"
    f"AccountKey={STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
)
endpoint = os.getenv("ENDPOINT_URL", "https://alfalavahub28182992243.openai.azure.com/")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o")
search_endpoint = os.getenv("SEARCH_ENDPOINT", "https://alfalaval1.search.windows.net")
search_key = os.getenv("SEARCH_KEY", "xQMFJrkvxL9yIAItDvLW3UOe380yg1iQ4tcal2z5omAzSeB39ZCS")
search_index = os.getenv("SEARCH_INDEX_NAME", "azureblob-index2")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "80f0255c0bfa4bd28e32db4582e1c4b1")

# Initialize Azure OpenAI client with key-based authentication
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2024-05-01-preview",
)

class PromptRequest(BaseModel):
    prompt: str

@app.post("/api/prompt")
async def handle_prompt(prompt_request: PromptRequest):
    try:
        user_input = prompt_request.prompt
        if not user_input:
            raise HTTPException(status_code=400, detail="No prompt provided")

        # Create a thread with Azure OpenAI
        completion = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": user_input}],
            max_tokens=200,
            temperature=0.5,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.5,
            stream=False,
            extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                        "filter": None,
                        "fields_mapping": {
                            "content_fields_separator": "\n",
                            "content_fields": ["content"],
                            "filepath_field": "metadata_storage_path",
                            "title_field": "metadata_storage_name",
                            "url_field": "metadata_storage_content_type",
                            "vector_fields": []
                        },
                        "endpoint": search_endpoint,
                        "index_name": search_index,
                        "semantic_configuration": "",
                        "authentication": {
                            "type": "api_key",
                            "key": search_key
                        },
                        "query_type": "simple",
                        "in_scope": False,
                        "strictness": 1,
                        "top_n_documents": 3
                    }
                }]
            }
        )

        data = json.loads(completion.to_json())
        choice = data["choices"][0]
        citations = choice["message"]["context"].get("citations", [])
        if citations:
            title = citations[0]["title"]
            file_response = await get_file(title)

            # Prepare the result with the title
            result = {
                "id": data["id"],
                "content": choice["message"]["content"],
                "file": file_response,  # List of titles from citations
            }

            return JSONResponse(content={"response": result})
        else:
            raise HTTPException(status_code=404, detail="No citations found.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_file(blob_name: str):
    try:
        # Get the container client
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        # Get the blob client
        blob_client = container_client.get_blob_client(blob_name)
        # Download blob content
        blob_data = blob_client.download_blob()
        file_content = blob_data.readall()

        # Encode content to base64
        base64_encoded_content = base64.b64encode(file_content).decode('utf-8')

        # Determine the content type based on file extension
        content_type = "application/octet-stream"  # Default content type
        if blob_name.endswith(".pdf"):
            content_type = "application/pdf"
        elif blob_name.endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif blob_name.endswith(".xlsx"):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif blob_name.endswith(".jpg") or blob_name.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif blob_name.endswith(".png"):
            content_type = "image/png"

        # Prepare and return the response data
        return {
            "file_name": blob_name,
            "content_type": content_type,
            "base64_data": base64_encoded_content
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
