# BitNet API Server

A FastAPI wrapper for Microsoft's BitNet inference framework that provides OpenAI-compatible API endpoints for 1-bit LLMs.

## Features

- Simple REST API for BitNet models
- OpenAI-compatible chat completions endpoint (`/v1/chat/completions`)
- Conversation management
- Streaming responses support
- Cross-origin resource sharing (CORS) enabled

## Requirements

- Python 3.9+
- FastAPI
- Uvicorn
- Pydantic
- A built BitNet executable and model

## Installation

1. Clone the Microsoft BitNet repository and build it following the instructions in their [GitHub repository](https://github.com/microsoft/BitNet)

2. Install the required Python packages:

```bash
pip install fastapi uvicorn pydantic
```

3. Place the `bitnet_api_server.py` file in your BitNet directory.

## Usage

1. Run the API server:

```bash
python bitnet_api_server.py -m /path/to/your/model.gguf --host 127.0.0.1 --port 8080
```

Parameters:
- `-m` or `--model`: Path to your BitNet model file (required)
- `--host`: Host to bind the server to (default: 127.0.0.1)
- `--port`: Port to listen on (default: 8080)

2. The server will be available at the specified host and port (default: http://127.0.0.1:8080)

## API Endpoints

### Text Completion

```
POST /completion
```

Request body:
```json
{
  "prompt": "Your prompt text",
  "temperature": 0.7,
  "top_k": 40,
  "top_p": 0.95,
  "n_predict": 128,
  "threads": 4,
  "ctx_size": 2048,
  "stream": false
}
```

### Chat Completion (OpenAI-compatible)

```
POST /v1/chat/completions
```

Request body:
```json
{
  "model": "model_name",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me a joke."}
  ],
  "temperature": 0.7,
  "top_p": 0.95,
  "max_tokens": 128,
  "stream": false
}
```

### Conversation Management

Create a new conversation:
```
POST /v1/conversations
```

Get a conversation:
```
GET /v1/conversations/{conversation_id}
```

Chat within a conversation:
```
POST /v1/conversations/{conversation_id}/chat
```

## Examples

### Python example (using the requests library)

```python
import requests

# Text completion
response = requests.post(
    "http://localhost:8080/completion",
    json={
        "prompt": "Once upon a time",
        "temperature": 0.7,
        "n_predict": 50
    }
)
print(response.json()["content"])

# Chat completion
response = requests.post(
    "http://localhost:8080/v1/chat/completions",
    json={
        "model": "bitnet-model",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write a short poem about AI."}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
)
print(response.json()["choices"][0]["message"]["content"])
```

## License

MIT License

## Acknowledgements

This project serves as an API wrapper for Microsoft's BitNet framework. All credit for the underlying BitNet implementation goes to Microsoft and the BitNet contributors.

## Disclaimer

This is not an official Microsoft product. This project is a community contribution to make BitNet more accessible through a standard API interface. 