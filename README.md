# Auto-Patch-AI 🤖🛡️

A CLI tool for DevSecOps that automatically scans your Docker containers and writes security-patched `Dockerfiles` using AI (OpenAI or Local Ollama).

## How it works:
1. Natively executes `trivy` under the hood to detect CVEs.
2. Parses the JSON vulnerability report.
3. Feeds the data to an LLM context window.
4. Generates a completely secure, upgraded `Dockerfile`.

## Setup
1. Verify `trivy` is installed on your system (`brew install trivy`).
2. Run standard Python setup:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Export your LLM API Key:
   ```bash
   export OPENAI_API_KEY="sk-..."
   # Or for local Ollama:
   # export LLM_BASE_URL="http://127.0.0.1:11434/v1"
   # export LLM_MODEL="llama3"
   ```

## Usage
Run the CLI against any public or local image:
```bash
python autopatch.py scan python:3.9-slim
```
The tool will output `Dockerfile.secure` into your current directory, containing the patched base image and `apt-get` upgrades.
