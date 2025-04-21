#!/usr/bin/env python3

import requests
import json
import time
import sys

# Base URL for the API
BASE_URL = "http://127.0.0.1:8080"

def test_completion_api():
    """Test basic completion API"""
    print("\n=== Testing Completion API ===")
    
    url = f"{BASE_URL}/completion"
    
    # Test data
    payload = {
        "prompt": "What is artificial intelligence?",
        "temperature": 0.7,
        "n_predict": 100,
        "threads": 4,
        "ctx_size": 2048,
        "top_k": 40,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "stream": False
    }
    
    print(f"Sending request to {url}")
    print(f"Prompt: '{payload['prompt']}'")
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=90)
        end_time = time.time()
        
        print(f"Response received in {end_time - start_time:.2f} seconds")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\nResponse content:")
            print(f"{result.get('content', 'No content')}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("Request timed out after 90 seconds")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_chat_api():
    """Test chat completions API"""
    print("\n=== Testing Chat Completions API ===")
    
    url = f"{BASE_URL}/v1/chat/completions"
    
    # Test data
    payload = {
        "model": "bitnet",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "What is artificial intelligence?"}
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.95,
        "stream": False
    }
    
    print(f"Sending request to {url}")
    print(f"User message: '{payload['messages'][1]['content']}'")
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=90)
        end_time = time.time()
        
        print(f"Response received in {end_time - start_time:.2f} seconds")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "No content")
            print("\nResponse content:")
            print(f"{content}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("Request timed out after 90 seconds")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_streaming_chat():
    """Test streaming chat API"""
    print("\n=== Testing Streaming Chat API ===")
    
    url = f"{BASE_URL}/v1/chat/completions"
    
    # Test data
    payload = {
        "model": "bitnet",
        "messages": [
            {"role": "user", "content": "What is artificial intelligence?"}
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "stream": True
    }
    
    print(f"Sending streaming request to {url}")
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=90)
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("\nStreaming response:")
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        if line == 'data: [DONE]':
                            print("\n[DONE]")
                            break
                        
                        data = json.loads(line[6:])
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            print(content, end="", flush=True)
            print()  # Add final newline
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    print("Starting BitNet API tests...")
    
    # Test server availability
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"Server not available at {BASE_URL}. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error connecting to server at {BASE_URL}: {str(e)}")
        return False
    
    print(f"Server available at {BASE_URL}")
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_completion_api():
        tests_passed += 1
    
    if test_chat_api():
        tests_passed += 1
    
    if test_streaming_chat():
        tests_passed += 1
    
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 