# Auto-Patch-AI

Scans a Docker image for CVEs using Trivy, then uses GPT-4o-mini to generate a patched Dockerfile. Closes the gap between "found a vulnerability" and "here's the fix."

The typical DevSecOps problem: scanner finds 30 CVEs, developer stares at the report, doesn't know which base image to upgrade to, does nothing. This tool takes the Trivy JSON output, structures it into a prompt, and produces a concrete Dockerfile with version pins and `apt-get` upgrades.

---

### How it works

```
docker image
     │
     ▼
trivy image --format json
     │  CVE list + affected packages + fixed versions
     ▼
GPT-4o-mini
     │  "given these vulns, rewrite the Dockerfile securely"
     ▼
Dockerfile.secure  (printed to terminal + saved to disk)
```

---

### Requirements

- Python 3.9+
- [Trivy](https://github.com/aquasecurity/trivy) installed and in PATH
  - macOS: `brew install trivy`
  - Linux: `apt install trivy` or see [trivy install docs](https://github.com/aquasecurity/trivy#installation)
- OpenAI API key

---

### Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
```

---

### Usage

```bash
# Scan an image and generate a patched Dockerfile
python autopatch.py python:3.9-slim

# Any public image works
python autopatch.py nginx:1.21
python autopatch.py node:18
```

The patched Dockerfile is printed to the terminal and saved as `Dockerfile.secure` in the current directory.

```bash
# Build and test the patched image
docker build -f Dockerfile.secure -t myapp:patched .
```

---

### Example output

Input image: `python:3.9-slim`

```
⚠️  Found 38 vulnerabilities.

╭─────────── Secure Dockerfile ────────────╮
│ FROM python:3.11-slim-bookworm           │
│ RUN apt-get update && \                  │
│     apt-get upgrade -y && \              │
│     apt-get clean && \                   │
│     rm -rf /var/lib/apt/lists/*          │
│ COPY . /app                              │
│ WORKDIR /app                             │
│ RUN pip install --upgrade pip            │
│ CMD ["python", "app.py"]                 │
╰──────────────────────────────────────────╯

✅ Wrote patched Dockerfile to Dockerfile.secure
```

---

### Notes

- Uses `gpt-4-turbo` by default. Override with `LLM_MODEL=gpt-4o-mini` for lower cost
- For local Ollama: set `LLM_BASE_URL=http://localhost:11434/v1` and `LLM_MODEL=llama3`
- Trivy is called as a subprocess — it must be installed separately
- The patched Dockerfile is a suggestion — always test it before deploying

---

### License

MIT
