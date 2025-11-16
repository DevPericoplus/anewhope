# anewhope
Project to manage infrastructure and applications in AWS cloud with AI-enhanced security features.

## Features

- **Encryption System**: Fernet-based symmetric encryption for secure data handling
- **AI Integration**: Local Ollama models for security analysis and recommendations
- **AWS Infrastructure Management**: Tools for managing AWS cloud resources
- **Ansible Support**: Automated infrastructure provisioning

## AI-Enhanced Security with Ollama

This project now includes integration with local Ollama models to provide AI-powered security features:

- Security context analysis
- Password policy recommendations
- Best practices suggestions
- Risk assessment

### Prerequisites for Ollama Integration

1. **Install Ollama**:
   ```bash
   # Visit https://ollama.ai for installation instructions
   # Linux:
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # macOS:
   brew install ollama
   ```

2. **Pull a model** (recommended: llama3.2):
   ```bash
   ollama pull llama3.2
   ```

3. **Start Ollama server**:
   ```bash
   ollama serve
   ```

### Using Ollama Features

The application automatically connects to Ollama when running:

```bash
python main.py
```

You can also test the Ollama integration separately:

```bash
python ollama_integration.py
```

### Available Ollama Models

The integration works with any Ollama model. Popular choices:
- `llama3.2` (default, recommended)
- `llama3.1`
- `mistral`
- `codellama`

To change the model, update the model parameter in `main.py`:
```python
ollama_client = OllamaClient(model="your-model-name")
```

## Installation

1. Clone the repository
2. Create and activate virtual environment (see info.txt for OS-specific instructions)
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create `protected_values.py` in the root folder with:
   ```python
   global_shared_key_raw = "Your-Secret-Key-Here"
   ```
5. Install and configure Ollama (optional, for AI features)

## Running the Application

```bash
python main.py
```

## Configuration

- Security files are stored in the `security/` folder
- The `basesecuritypass.json` file contains encrypted keys (git-ignored)
- Ollama connects to `http://localhost:11434` by default
