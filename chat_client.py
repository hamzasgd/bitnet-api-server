#!/usr/bin/env python3

import requests
import json
import sys
import time
import argparse

# Default server URL
DEFAULT_URL = "http://127.0.0.1:8081"

class BitNetChatClient:
    def __init__(self, server_url=DEFAULT_URL):
        self.server_url = server_url
        self.conversation_id = None
        self.messages = []
    
    def create_conversation(self):
        """Create a new conversation"""
        try:
            response = requests.post(
                f"{self.server_url}/v1/conversations",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.conversation_id = data.get("conversation_id")
                self.messages = []
                print(f"Created new conversation: {self.conversation_id}")
                return True
            else:
                print(f"Error creating conversation: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error: {str(e)}")
            return False
    
    def send_message(self, message, max_tokens=100):
        """Send a message to the conversation"""
        if not self.conversation_id:
            if not self.create_conversation():
                return False
        
        payload = {
            "model": "bitnet",
            "messages": [{"role": "user", "content": message}],
            "temperature": 0.7,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/v1/conversations/{self.conversation_id}/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Update local message history
                self.messages.append({"role": "user", "content": message})
                self.messages.append({"role": "assistant", "content": content})
                
                return content
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    def get_conversation_history(self):
        """Get the current conversation history"""
        if not self.conversation_id:
            print("No active conversation.")
            return []
        
        try:
            response = requests.get(
                f"{self.server_url}/v1/conversations/{self.conversation_id}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.messages = data.get("messages", [])
                return self.messages
            else:
                print(f"Error getting conversation: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error: {str(e)}")
            return []
    
    def print_conversation(self):
        """Print the current conversation"""
        if not self.messages:
            history = self.get_conversation_history()
            if not history:
                print("No conversation history.")
                return
        
        print("\n===== Conversation =====")
        for msg in self.messages:
            role = msg.get("role", "").capitalize()
            content = msg.get("content", "")
            print(f"{role}: {content}\n")

def interactive_chat(client):
    """Run an interactive chat session"""
    print("BitNet Chat Client")
    print("Type 'exit' to quit, 'new' for a new conversation, 'history' to show history")
    
    client.create_conversation()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'exit':
                break
            elif user_input.lower() == 'new':
                client.create_conversation()
                print("Started a new conversation.")
                continue
            elif user_input.lower() == 'history':
                client.print_conversation()
                continue
            elif not user_input:
                continue
            
            print("BitNet: ", end="", flush=True)
            start_time = time.time()
            
            response = client.send_message(user_input)
            end_time = time.time()
            
            if response:
                print(response)
                print(f"[Response time: {end_time - start_time:.2f}s]")
            else:
                print("No response received.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BitNet Chat Client")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="BitNet server URL")
    args = parser.parse_args()
    
    client = BitNetChatClient(server_url=args.url)
    interactive_chat(client) 