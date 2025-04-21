#!/usr/bin/env python3
"""
BitNet API Server - A FastAPI wrapper for Microsoft's BitNet inference framework
Provides OpenAI-compatible API endpoints for 1-bit LLMs.

Copyright (c) 2024 BitNet API Server Contributors
Released under MIT License
"""

import os
import sys
import time
import json
import signal
import platform
import subprocess
import argparse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Request models
class CompletionRequest(BaseModel):
    prompt: str
    temperature: float = 0.7
    top_k: int = 40
    top_p: float = 0.95
    n_predict: int = 128
    threads: int = 4
    ctx_size: int = 2048
    stream: bool = False

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    top_p: float = 0.95
    max_tokens: int = 128
    stream: bool = False

# Create FastAPI app
app = FastAPI(title="BitNet API Server")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
model_path = None
executable_path = None
# Add conversation store
conversation_store = {}

def get_executable_path():
    """Get the path to the llama-cli executable"""
    build_dir = "build"
    if platform.system() == "Windows":
        exe_path = os.path.join(build_dir, "bin", "Release", "llama-cli.exe")
        if not os.path.exists(exe_path):
            exe_path = os.path.join(build_dir, "bin", "llama-cli")
    else:
        exe_path = os.path.join(build_dir, "bin", "llama-cli")
    return exe_path

@app.get("/")
async def root():
    """API root"""
    return {"message": "BitNet API Server is running"}

@app.post("/completion")
async def completion(request: CompletionRequest):
    """Generate a completion for the given prompt"""
    if not model_path or not os.path.exists(model_path):
        raise HTTPException(status_code=400, detail="Model not loaded")

    try:
        return await run_completion(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions API"""
    if not model_path or not os.path.exists(model_path):
        raise HTTPException(status_code=400, detail="Model not loaded")
    
    # Get or create conversation ID
    conversation_id = request.model
    if len(request.messages) > 0 and hasattr(request, 'conversation_id'):
        conversation_id = request.conversation_id
    
    # Check if we have history for this conversation
    if conversation_id in conversation_store:
        # Only add new messages that aren't already in history
        current_messages = [msg.dict() for msg in request.messages]
        stored_messages = conversation_store[conversation_id]
        
        # If client sends fewer messages than we have stored, they might have reset
        if len(current_messages) < len(stored_messages):
            stored_messages = current_messages
        else:
            # Add only new messages
            stored_messages = current_messages
    else:
        # New conversation
        stored_messages = [msg.dict() for msg in request.messages]
    
    # Convert chat format to prompt using full history
    prompt = format_chat_prompt([ChatMessage(**msg) for msg in stored_messages])
    
    # Create a completion request
    completion_request = CompletionRequest(
        prompt=prompt,
        temperature=request.temperature,
        top_p=request.top_p,
        n_predict=request.max_tokens,
        stream=request.stream,
        threads=4,
        ctx_size=2048
    )
    
    try:
        result = await run_completion(completion_request)
        
        if request.stream:
            return result  # Already a StreamingResponse
        
        # Add assistant's response to conversation history
        assistant_message = {
            "role": "assistant",
            "content": result.get("content", "")
        }
        stored_messages.append(assistant_message)
        
        # Store updated conversation
        conversation_store[conversation_id] = stored_messages
        
        # Format in OpenAI-like format
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": os.path.basename(model_path),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("content", "")
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

def format_chat_prompt(messages: List[ChatMessage]) -> str:
    """Format chat messages into a prompt"""
    prompt = ""
    
    for msg in messages:
        if msg.role == "system":
            prompt += f"System: {msg.content}\n"
        elif msg.role == "user":
            prompt += f"User: {msg.content}\n"
        elif msg.role == "assistant":
            prompt += f"Assistant: {msg.content}\n"
    
    if not prompt.endswith("Assistant:"):
        prompt += "Assistant:"
    
    return prompt

async def run_completion(request: CompletionRequest):
    """Run BitNet completion with the given parameters"""
    # Build command
    command = [
        executable_path,
        "-m", model_path,
        "-n", str(request.n_predict),
        "-t", str(request.threads),
        "-p", request.prompt,
        "-ngl", "0",
        "-c", str(request.ctx_size),
        "--temp", str(request.temperature),
        "-b", "1",
        "--top_k", str(request.top_k),
        "--top_p", str(request.top_p)
    ]
    
    # For streaming responses
    if request.stream:
        return StreamingResponse(
            generate_stream(command, request.prompt),
            media_type="text/event-stream"
        )
    
    # For regular responses
    try:
        # Run the subprocess
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Set a timeout
        timeout = 30  # seconds
        start_time = time.time()
        
        # Collect output
        output_lines = []
        response_started = False
        
        # Read stdout until process finishes or times out
        while process.poll() is None:
            # Check timeout
            if time.time() - start_time > timeout:
                process.terminate()
                raise TimeoutError(f"Process timed out after {timeout} seconds")
            
            # Get output line by line
            if process.stdout.readable():
                line = process.stdout.readline()
                if not line:
                    continue
                
                # Skip debug lines
                if any(marker in line for marker in [
                    "llama_", "gguf_", "main:", "build:", "system_info:", 
                    "warning:", "sampler", "generate:", "eval time"
                ]):
                    continue
                
                # Check if this line contains the prompt
                if request.prompt in line and not response_started:
                    # Extract everything after the prompt
                    parts = line.split(request.prompt, 1)
                    if len(parts) > 1:
                        output_lines.append(parts[1])
                        response_started = True
                    continue
                
                # Look for "Assistant:" marker
                if "Assistant:" in line and not response_started:
                    parts = line.split("Assistant:", 1)
                    if len(parts) > 1:
                        output_lines.append(parts[1])
                        response_started = True
                    continue
                
                # If we've started collecting the response, add all non-debug lines
                if response_started:
                    output_lines.append(line)
        
        # Clean up
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except:
                process.kill()
        
        # Join and clean output
        response_text = "".join(output_lines).strip()
        
        # Return the result
        return {
            "model": os.path.basename(model_path),
            "created_at": int(time.time()),
            "content": response_text,
            "stopped_at": None,
            "stop_reason": "length"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating completion: {str(e)}")

async def generate_stream(command, prompt):
    """Generate a streaming response"""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        output_buffer = ""
        response_started = False
        
        for line in process.stdout:
            # Skip debug lines
            if any(marker in line for marker in [
                "llama_", "gguf_", "main:", "build:", "system_info:", 
                "warning:", "sampler", "generate:", "eval time"
            ]):
                continue
            
            # Check if this line contains the prompt
            if prompt in line and not response_started:
                # Extract everything after the prompt
                parts = line.split(prompt, 1)
                if len(parts) > 1:
                    output_buffer = parts[1]
                    response_started = True
                continue
            
            # Look for "Assistant:" marker
            if "Assistant:" in line and not response_started:
                parts = line.split("Assistant:", 1)
                if len(parts) > 1:
                    output_buffer = parts[1]
                    response_started = True
                continue
            
            # If we've started collecting the response, add all non-debug lines
            if response_started:
                output_buffer += line
            
            # If we have accumulated output, send it
            if output_buffer:
                response_json = {
                    "model": os.path.basename(model_path),
                    "created_at": int(time.time()),
                    "content": output_buffer.strip(),
                    "done": False
                }
                
                output_buffer = ""  # Clear buffer
                yield f"data: {json.dumps(response_json)}\n\n"
        
        # Send the final "done" message
        yield f"data: {json.dumps({'done': True})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        # Clean up
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except:
                process.kill()

# Add a new endpoint to create/get conversation
@app.post("/v1/conversations")
async def create_conversation():
    """Create a new conversation and return its ID"""
    conversation_id = f"conv_{int(time.time())}_{len(conversation_store)}"
    conversation_store[conversation_id] = []
    return {"conversation_id": conversation_id}

@app.get("/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation by ID"""
    if conversation_id not in conversation_store:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"conversation_id": conversation_id, "messages": conversation_store[conversation_id]}

# Add a new chat endpoint with explicit conversation ID
@app.post("/v1/conversations/{conversation_id}/chat")
async def conversation_chat(conversation_id: str, request: ChatCompletionRequest):
    """Chat within a specific conversation"""
    if conversation_id not in conversation_store:
        conversation_store[conversation_id] = []
    
    # Use existing stored history
    stored_messages = conversation_store[conversation_id]
    
    # Add new user message
    user_messages = [msg for msg in request.messages if msg.role == "user"]
    if user_messages:
        stored_messages.append(user_messages[-1].dict())
    
    # Convert chat format to prompt using full history
    history_messages = [ChatMessage(**msg) for msg in stored_messages]
    prompt = format_chat_prompt(history_messages)
    
    # Create a completion request
    completion_request = CompletionRequest(
        prompt=prompt,
        temperature=request.temperature,
        top_p=request.top_p,
        n_predict=request.max_tokens,
        stream=request.stream,
        threads=4,
        ctx_size=2048
    )
    
    try:
        result = await run_completion(completion_request)
        
        if request.stream:
            return result  # Already a StreamingResponse
        
        # Add assistant's response to conversation history
        assistant_message = {
            "role": "assistant",
            "content": result.get("content", "")
        }
        stored_messages.append(assistant_message)
        
        # Store updated conversation
        conversation_store[conversation_id] = stored_messages
        
        # Format in OpenAI-like format
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": os.path.basename(model_path),
            "conversation_id": conversation_id,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("content", "")
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

def main():
    """Main entry point"""
    global model_path, executable_path
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="BitNet API Server")
    parser.add_argument("-m", "--model", type=str, required=True, help="Path to the model file")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    
    args = parser.parse_args()
    
    model_path = args.model
    executable_path = get_executable_path()
    
    # Check if the model exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found: {model_path}")
        return 1
    
    # Check if the executable exists
    if not os.path.exists(executable_path):
        print(f"Error: Executable not found: {executable_path}")
        return 1
    
    # Register signal handlers
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))
    
    # Print startup info
    print(f"BitNet API Server starting...")
    print(f"Model: {model_path}")
    print(f"Executable: {executable_path}")
    print(f"Server will be available at http://{args.host}:{args.port}")
    
    # Start the server
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 