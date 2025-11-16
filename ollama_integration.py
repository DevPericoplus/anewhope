"""
Ollama Integration Module
Provides AI capabilities using local Ollama models
"""
import requests
import json
import os


class OllamaClient:
    """Client for interacting with local Ollama models"""
    
    def __init__(self, base_url="http://localhost:11434", model="llama3.2"):
        """
        Initialize Ollama client
        
        Args:
            base_url: URL where Ollama is running (default: http://localhost:11434)
            model: Model to use (default: llama3.2)
        """
        self.base_url = base_url
        self.model = model
        self.api_url = f"{base_url}/api"
    
    def check_connection(self):
        """Check if Ollama server is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                print(f"✅ Connected to Ollama server at {self.base_url}")
                return True
            else:
                print(f"❌ Ollama server returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to Ollama server at {self.base_url}: {e}")
            return False
    
    def list_models(self):
        """List all available models in Ollama"""
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])
                print(f"Available models ({len(models)}):")
                for model in models:
                    print(f"  - {model.get('name', 'Unknown')}")
                return models
            else:
                print(f"❌ Error listing models: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error listing models: {e}")
            return []
    
    def generate(self, prompt, stream=False):
        """
        Generate text using the Ollama model
        
        Args:
            prompt: The prompt to send to the model
            stream: Whether to stream the response (default: False)
            
        Returns:
            Generated text response
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream
            }
            
            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                if stream:
                    return self._handle_stream_response(response)
                else:
                    result = response.json()
                    return result.get('response', '')
            else:
                print(f"❌ Error generating response: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error during generation: {e}")
            return None
    
    def _handle_stream_response(self, response):
        """Handle streaming response from Ollama"""
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    chunk = data.get('response', '')
                    full_response += chunk
                    print(chunk, end='', flush=True)
                except json.JSONDecodeError:
                    continue
        print()  # New line after streaming
        return full_response
    
    def chat(self, messages):
        """
        Chat with the Ollama model
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            Generated response
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False
            }
            
            response = requests.post(
                f"{self.api_url}/chat",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', '')
            else:
                print(f"❌ Error in chat: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error during chat: {e}")
            return None
    
    def analyze_security_context(self, context):
        """
        Analyze security context using AI
        
        Args:
            context: Security context to analyze
            
        Returns:
            Analysis result
        """
        prompt = f"""You are a security analyst. Analyze the following security context and provide insights:

Context: {context}

Provide a brief analysis focusing on:
1. Potential security risks
2. Recommendations
3. Best practices

Keep the response concise and actionable."""
        
        return self.generate(prompt)
    
    def suggest_password_policy(self):
        """Get AI-generated password policy suggestions"""
        prompt = """Suggest a strong password policy for an enterprise application. 
Include requirements for length, complexity, rotation, and any other important security considerations.
Keep it concise and practical."""
        
        return self.generate(prompt)


def test_ollama_connection():
    """Test function to verify Ollama connectivity"""
    print("Testing Ollama connection...")
    print("-" * 50)
    
    client = OllamaClient()
    
    if client.check_connection():
        print("\nListing available models:")
        client.list_models()
        
        print("\nTesting basic generation:")
        response = client.generate("Say hello in one sentence.")
        if response:
            print(f"Response: {response}")
        
        return True
    else:
        print("\n⚠️  Make sure Ollama is running with: ollama serve")
        return False


if __name__ == "__main__":
    test_ollama_connection()
