# BitNet API Guide

This guide explains how to use the BitNet API with conversation history features.

## Starting the BitNet Server

```bash
# Start the server with a model file
python3 bitnet_fast.py -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf --port 8081
```

## Using the Interactive Chat Client

The simplest way to interact with BitNet is through our interactive chat client:

```bash
# Start the interactive chat client
python3 chat_client.py

# To specify a different server URL
python3 chat_client.py --url http://127.0.0.1:8081
```

### Chat Client Commands:
- Type your message normally to chat with BitNet
- Type `history` to show the conversation history
- Type `new` to start a new conversation
- Type `exit` to quit

## Using the API Directly with curl

### Create a New Conversation

```bash
# Create a new conversation
curl -X POST http://127.0.0.1:8081/v1/conversations

# Response:
# {"conversation_id":"conv_1234567890_0"}
```

### Chat Within a Conversation

```bash
# Store the conversation ID in a variable
CONV_ID=$(curl -s -X POST http://127.0.0.1:8081/v1/conversations | jq -r .conversation_id)

# Send a message
curl -X POST http://127.0.0.1:8081/v1/conversations/$CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bitnet",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "temperature": 0.7,
    "max_tokens": 100
  }'

# Send a follow-up message that references the previous one
curl -X POST http://127.0.0.1:8081/v1/conversations/$CONV_ID/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bitnet",
    "messages": [{"role": "user", "content": "What did I just ask you?"}],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### View Conversation History

```bash
# Get conversation history
curl -X GET http://127.0.0.1:8081/v1/conversations/$CONV_ID
```

## Using the API in Python

```python
import requests

# Create a conversation
response = requests.post("http://127.0.0.1:8081/v1/conversations")
conv_id = response.json()["conversation_id"]

# Send a message
response = requests.post(
    f"http://127.0.0.1:8081/v1/conversations/{conv_id}/chat",
    json={
        "model": "bitnet",
        "messages": [{"role": "user", "content": "Hello!"}],
        "temperature": 0.7,
        "max_tokens": 100
    }
)

# Get the model's response
answer = response.json()["choices"][0]["message"]["content"]
print(f"BitNet says: {answer}")

# Send a follow-up message referring to history
response = requests.post(
    f"http://127.0.0.1:8081/v1/conversations/{conv_id}/chat",
    json={
        "model": "bitnet",
        "messages": [{"role": "user", "content": "What did I just say?"}],
        "temperature": 0.7,
        "max_tokens": 100
    }
)

# BitNet will recall the previous "Hello!" message
```

## API Reference

### Conversation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/conversations` | POST | Create a new conversation |
| `/v1/conversations/{id}` | GET | Get conversation history |
| `/v1/conversations/{id}/chat` | POST | Send a message within a conversation |

### Completion Endpoint (No History)

```bash
# One-off completion without saving to conversation history
curl -X POST http://127.0.0.1:8081/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is artificial intelligence?",
    "temperature": 0.7,
    "n_predict": 100
  }'
```

### OpenAI-Compatible Endpoint (No History)

```bash
# OpenAI-compatible endpoint (without conversation persistence)
curl -X POST http://127.0.0.1:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bitnet",
    "messages": [
      {"role": "system", "content": "You are a helpful AI assistant."},
      {"role": "user", "content": "What is artificial intelligence?"}
    ],
    "temperature": 0.7,
    "max_tokens": 150
  }'
```

## Common Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `temperature` | Controls randomness (0-1) | 0.7 |
| `max_tokens` / `n_predict` | Max tokens to generate | 100 |
| `top_p` | Nucleus sampling probability | 0.95 |
| `top_k` | Top-k sampling | 40 |
| `threads` | CPU threads to use | 4 |

## Troubleshooting

If you encounter 422 errors, check your JSON formatting and make sure all required fields are present.

This setup allows you to have ongoing conversations with BitNet where it remembers the context of previous exchanges. 