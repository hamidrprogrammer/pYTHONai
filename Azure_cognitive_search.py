import base64
import json
import os
import logging
import pprint
from typing import List
from openai import AzureOpenAI
from fastapi import FastAPI, HTTPException
from azure.storage.blob import BlobServiceClient
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import markdown  # Python Markdown library
from fastapi.responses import StreamingResponse
import time
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your front-end origin if necessary
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Environment variables for Azure OpenAI
endpoint = os.getenv("EDPOINT_URL", "https://alfalavahub28182992243.openai.azure.com/")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o-2")
search_endpoint = os.getenv("SEARCH_ENDPOINT", "https://alfalaval1.search.windows.net")
search_key = os.getenv("SEARCH_KEY", "xQMFJrkvxL9yIAItDvLW3UOe380yg1iQ4tcal2z5omAzSeB39ZCS")
search_index = os.getenv("SEARCH_INDEX_NAME", "azureblob-newalfalaval")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "80f0255c0bfa4bd28e32db4582e1c4b1")
# Initialize Azure OpenAI client with key-based authentication
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2024-05-01-preview",
)
class Message(BaseModel):
    content: str
    role: str

class PromptRequest(BaseModel):
    prompt: List[Message]

@app.post("/ai/prompt")
async def handle_prompt(prompt_request: PromptRequest):
    try:
        additional_prompt = Message(
            role="system", 
            content=(
                "Generate a formatted document in that answers the question. As an assistant, "
                "provide a comprehensive and accurate response to the employee's query. If unable to find "
                "the information, provide a thoughtful and informative answer instead of saying 'I couldn't find anything.' "
                "Ensure the output is concise and easy to read, with a clear and organized structure. "
                "This modified prompt provides specific guidelines for the output, including: "
                "* The format of the response Gernal document "
                "* The level of detail required  "
                "* Do not use asterisks, of course, it should be like a professional document, a beautiful template, and try not to jumble your words, do not leave spaces between words."
                "* Most of the data are technical data, there are technical data in it, there may be different symbols and algorithms in it, there may be different words. Absolutely, what you are writing or using, or using creativity, or not writing in such a way that it is different from the pdf or the file you are looking at."
                "* The tone and style of the response like dcoumet "
                "* The structure and organization of the output (clear and concise) "
                "By providing these specific guidelines, the ChatGPT model will be able to generate a high-quality response that meets the requirements of the task."
            )
        )
        user_input = [additional_prompt] + prompt_request.prompt
        if not user_input:
            raise HTTPException(status_code=400, detail="No prompt provided")

        time.sleep(3) # Create a thread with Azure OpenAI
        response = client.chat.completions.create(
            model=deployment,
            messages=user_input,
            max_tokens=900,
            temperature=0.2,
            top_p=0.2,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stream=True,
            extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                        "filter": None,
                        "semantic_configuration": "default",
                        "fields_mapping": {
              "content_fields_separator": "\n",
              "content_fields": [
                "content"
              ],
              "filepath_field": "metadata_storage_path",
              "title_field": "merged_content",
              "url_field": "metadata_storage_name",
              "vector_fields": []
            },
                        "endpoint": search_endpoint,
                        "index_name": search_index,
                        "authentication": {
                            "type": "api_key",
                            "key": search_key
                        },
                        "query_type": "simple",
                        "in_scope": True,
                        "role_information": ""  "Generate a formatted document in that answers the question. As an assistant, "
                "provide a comprehensive and accurate response to the employee's query. If unable to find "
                "the information, provide a thoughtful and informative answer instead of saying 'I couldn't find anything.' "
                "Ensure the output is concise and easy to read, with a clear and organized structure. "
                "This modified prompt provides specific guidelines for the output, including: "
                "* The format of the response Gernal document "
                "* The level of detail required  "
                                "* Most of the data are technical data, there are technical data in it, there may be different symbols and algorithms in it, there may be different words. Absolutely, what you are writing or using, or using creativity, or not writing in such a way that it is different from the pdf or the file you are looking at."

                "* The tone and style of the response like dcoumet "
                "* Do not use asterisks, of course, it should be like a professional document, a beautiful template, and try not to jumble your words, do not leave spaces between words."
                "* The structure and organization of the output (clear and concise) "
                "By providing these specific guidelines, the ChatGPT model will be able to generate a high-quality response that meets the requirements of the task.""",
                        "strictness": 1,
                        "top_n_documents": 2,
                    }
                }]
            }
        )

        async def generate_response():
            
            citations = []  # To store citations
            for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'context') and delta.context:
                  if 'citations' in delta.context:
                  
                   for file in delta.context['citations']:
                    citations.append(file['url'])
                    
                if delta.content:
                    

                    # Assuming the citations are provided in the model's extra context
                    

                    yield delta.content + " "

            # Yield citations at the end of the response
            if citations:
                html_citations = [f'<a href="https://alfalavastorge.blob.core.windows.net/alfalava/{citation}?sp=r&st=2024-10-20T03:34:11Z&se=2025-01-01T11:34:11Z&sv=2022-11-02&sr=c&sig=5sYsQNlaIt%2BJeeRZA%2Bxrl5a7Rw4KnN8Cv9Fb0kqDVYs%3D">{citation}</a>' for citation in citations]

    # Join the converted links with line breaks and yield them
                yield "\n<p> <strong>Reference :</strong></p>\n" + "<br>".join(html_citations)

        
        return StreamingResponse(generate_response(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
       
@app.post("/ai/file")
async def handle_file(prompt_request: PromptRequest):
    try:
        user_input = prompt_request.prompt
        if not user_input:
            raise HTTPException(status_code=400, detail="No prompt provided")

        # Create a thread with Azure OpenAI
        completion =   response = client.chat.completions.create(
            model=deployment,
            messages=user_input,
            max_tokens=900,
            temperature=0.2,
            top_p=0.2,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stream=False,
            extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                        "filter": None,
                        "semantic_configuration": "default",
                         "fields_mapping": {
              "content_fields_separator": "\n",
              "content_fields": [
                "content"
              ],
              "filepath_field": "metadata_storage_path",
              "title_field": "merged_content",
              "url_field": "metadata_title",
              "vector_fields": []
            },
                        "endpoint": search_endpoint,
                        "index_name": search_index,
                        "authentication": {
                            "type": "api_key",
                            "key": search_key
                        },
                        "query_type": "simple",
                        "in_scope": True,
                        "role_information": "You are an AI assistant that helps people find information.",
                        "strictness": 1,
                        "top_n_documents": 2,
                    }
                }]
            }
        )
        content = completion.choices[0].message.content
        context = completion.choices[0].message.context
        for citation_index, citation in enumerate(context["citations"]):
            citation_reference = f"[doc{citation_index + 1}]"
            url = "https://example.com/?redirect=" + citation["url"] # replace with actual host and encode the URL
            filepath = citation["filepath"]
            title = citation["title"]
            snippet = citation["content"]
            chunk_id = citation["chunk_id"]
            replaced_html = f"<a href='{url}' title='{title}\n{snippet}''>(See from file {filepath}, Part {chunk_id})</a>"
            content = content.replace(citation_reference, replaced_html)
            print(content)

        data = json.loads(completion.to_json())
        choice = data["choices"][0]
        print(data)
        citations = choice["message"]["context"].get("citations", [])
        
        if citations:
            title = citations[0]["title"]
            # file_response = await get_file(title)

            # Prepare the result with the citations
            html_response = choice["message"]["content"]
            result = {
                "id": data["id"],
                "content": data['choices'][0]['message']['content'],
                # "file": file_response,  # Response includes file info
            }

            return JSONResponse(content={"response": result})
        else:
            logger.warning("No citations found.")
            raise HTTPException(status_code=404, detail="No citations found.")

    except Exception as e:
        logger.error(f"Error in handle_prompt: {str(e)}")
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
        logger.error(f"Error in get_file: {str(e)}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

