import json
from flask import Flask, request, jsonify
import os
import time
from openai import AzureOpenAI
import markdown  # Python Markdown library

from flask_cors import CORS
import os
from openai import AzureOpenAI

# Set up environment variables


app = Flask(__name__)
CORS(app) 

# Set up the Azure OpenAI client
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



# Create a thread

# Define a route for the AI interaction
@app.route('/api/prompt', methods=['POST'])
def handle_prompt():
    try:
        # Get the user's input from the request JSON
        data = request.get_json()
        prompt = data.get('prompt', None)
        user_input = prompt
        print(user_input)
        if not user_input:
            return jsonify({'error': 'No prompt provided'}), 400

        # Create a thread
        completion = client.chat.completions.create(
    model=deployment,
    messages=[
        
        {
            "role": "user",
            "content": prompt
        },
        
    ],
    max_tokens=200,  # Example: Increased max_tokens for longer responses
    temperature=0.5,  # Example: Lowered temperature for more deterministic responses
    top_p=0.9,  # Example: Adjusted to allow for a bit more creativity
    frequency_penalty=0.5,  # Example: Increased to reduce repetitive content
    presence_penalty=0.5,
    stream=False,
    extra_body={
        "data_sources": [{
            "type": "azure_search",
            "parameters": {
                "filter": None,
                 "fields_mapping": {
              "content_fields_separator": "\n",
              "content_fields": [
                "content"
              ],
              "filepath_field": "metadata_storage_path",
              "title_field": "metadata_storage_name",
              "url_field": "metadata_storage_content_type",
              "vector_fields": []
            },
                "endpoint": search_endpoint,
                "index_name": "azureblob-index",
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

                # Return the JSON response with the HTML and reference to Python Markdown
        data = json.loads(completion.to_json())
        result = {
    "id": data["id"],
    "content": data["choices"][0]["message"]["content"],
    "citations": [citation["content"] for citation in data["choices"][0]["message"]["context"]["citations"]]
} 
        # html_response = markdown.markdown(result["citations"])
        # print(completion.to_json())
        return jsonify({
                    'response':  data,
                }), 200
           

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
