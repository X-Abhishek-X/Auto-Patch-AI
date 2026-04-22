# Auto-Patch-AI

Scans a Docker image for CVEs with Trivy, then uses an LLM to write a patched Dockerfile. Works free out of the box via Groq — no credit card needed.

```
docker image
     │
     ▼
trivy image --format json
     │  CVE list + affected packages + fixed versions
     ▼
LLM (Groq / OpenAI / Ollama)
     │  "rewrite this Dockerfile to fix these CVEs"
     ▼
Dockerfile.secure
```

---

### Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Install Trivy:
```bash
brew install trivy          # macOS
sudo apt install trivy      # Linux
```

---

### API key (pick one)

**Free — Groq** (recommended): sign up at [console.groq.com](https://console.groq.com) — no card required
```bash
export GROQ_API_KEY="your_groq_key"
```

**Paid — OpenAI:**
```bash
export OPENAI_API_KEY="sk-..."
```

**Local — Ollama:**
```bash
export LLM_BASE_URL="http://localhost:11434/v1"
export LLM_MODEL="llama3"
```

Priority order: Groq → Ollama (if `LLM_BASE_URL` set) → OpenAI.

---

### Usage

```bash
python autopatch.py python:3.9-slim
python autopatch.py nginx:1.21
python autopatch.py node:18
```

Output:
```
Auto-Patch-AI — provider: Groq (free)  model: llama-3.3-70b-versatile
Scanning image: python:3.9-slim

  CRITICAL  2
  HIGH      7
  MEDIUM    14
  LOW       31

Found 54 vulnerabilities. Generating patch...

╭─────────────── Dockerfile.secure ───────────────╮
│ FROM python:3.11-slim-bookworm                  │
│ RUN apt-get update && apt-get upgrade -y && \   │
│     apt-get clean && rm -rf /var/lib/apt/lists/* │
│ COPY . /app                                     │
│ WORKDIR /app                                    │
│ CMD ["python", "app.py"]                        │
╰──────────────────────────────────────────────────╯

Saved to Dockerfile.secure
Test it: docker build -f Dockerfile.secure -t myapp:patched .
```

---

### Notes

- Cap of 20 CVEs sent to the LLM to stay within context limits
- The patched Dockerfile is a suggestion — test before deploying
- For `.env` file usage: copy `.env.example` to `.env` and fill in your key

---

### License

MIT
