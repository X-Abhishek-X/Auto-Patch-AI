# Auto-Patch-AI

Scans a Docker image for CVEs using Trivy, then uses GPT-4o-mini to generate a patched Dockerfile. Closes the loop between "found a vulnerability" and "here's how to fix it."

The typical DevSecOps workflow is: scanner finds 30 CVEs, developer stares at the report, doesn't know which base image to upgrade to, does nothing. This tool takes the Trivy JSON output, structures it into a prompt, and produces a concrete Dockerfile diff with version pins and `apt-get` upgrades.

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
     │  "given these vulns in this Dockerfile, produce a patched version"
     ▼
Dockerfile.secure
```

The prompt includes: the full Dockerfile content, each CVE with its severity and fixed version, and an instruction to pin to the minimal safe base image. The model is told to only change what's necessary — it doesn't redesign your Dockerfile.

---

### Requirements

- Python 3.9+
- [Trivy](https://github.com/aquasecurity/trivy) installed (`brew install trivy` on macOS, `apt install trivy` on Linux)
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
python autopatch.py --image python:3.9-slim

# Scan against a specific existing Dockerfile
python autopatch.py --image python:3.9-slim --dockerfile ./Dockerfile

# Write output to a specific path
python autopatch.py --image nginx:1.21 --output ./Dockerfile.patched
```

---

### Example output

Input Dockerfile:
```dockerfile
FROM python:3.9-slim
RUN pip install flask==2.0.1
COPY . /app
CMD ["python", "app.py"]
```

After patching (`Dockerfile.secure`):
```dockerfile
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get upgrade -y && apt-get clean
RUN pip install flask==3.0.3
COPY . /app
CMD ["python", "app.py"]
```

CVE summary printed to terminal:
```
CRITICAL  2    libssl1.1, libc6
HIGH      7    expat, libxml2, curl ...
MEDIUM    14
LOW       31
──────────────────────────────────
Patched Dockerfile written to Dockerfile.secure
```

---

### Notes

- Trivy must be installed separately — `autopatch.py` calls it as a subprocess
- The patched Dockerfile is a suggestion, not a guarantee — always test it
- GPT-4o-mini is used for cost efficiency; swap to `gpt-4o` in `autopatch.py` for better results on complex multi-stage builds

---

### License

MIT
