import subprocess
import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
import os
from openai import OpenAI

app = typer.Typer(help="Container vulnerability scanner — Trivy + LLM to auto-patch Dockerfiles")
console = Console()

# ── Provider config ────────────────────────────────────────────────────────────
# Groq (free, no card): set GROQ_API_KEY — https://console.groq.com
# OpenAI (paid):        set OPENAI_API_KEY
# Ollama (local):       set LLM_BASE_URL=http://localhost:11434/v1 and LLM_MODEL

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
OPENAI_DEFAULT_MODEL = "gpt-4o"

def _resolve_client():
    """
    Priority: Groq > OpenAI > Ollama (via LLM_BASE_URL).
    Returns (OpenAI client, model_name, provider_label).
    """
    groq_key = os.environ.get("GROQ_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    custom_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL")

    if groq_key:
        return (
            OpenAI(api_key=groq_key, base_url=GROQ_BASE_URL),
            model or GROQ_DEFAULT_MODEL,
            "Groq (free)",
        )
    if custom_url:
        # Ollama or any other OpenAI-compatible endpoint
        return (
            OpenAI(api_key=openai_key or "ollama", base_url=custom_url),
            model or "llama3",
            f"Custom ({custom_url})",
        )
    if openai_key:
        return (
            OpenAI(api_key=openai_key),
            model or OPENAI_DEFAULT_MODEL,
            "OpenAI",
        )

    console.print(
        "[bold red]No API key found.[/bold red]\n"
        "Set [cyan]GROQ_API_KEY[/cyan] for free usage (groq.com) "
        "or [cyan]OPENAI_API_KEY[/cyan] for OpenAI."
    )
    raise typer.Exit(1)


# ── Trivy ──────────────────────────────────────────────────────────────────────

def run_trivy(image_name: str) -> dict:
    try:
        result = subprocess.run(
            ["trivy", "image", "--format", "json", image_name],
            capture_output=True, text=True, check=False,
        )
        if not result.stdout:
            console.print("[bold red]No Trivy output. Is Trivy installed?[/bold red]")
            return None
        return json.loads(result.stdout)
    except FileNotFoundError:
        console.print("[bold red]Trivy not found. Install: brew install trivy[/bold red]")
        return None
    except json.JSONDecodeError:
        console.print("[bold red]Failed to parse Trivy JSON output.[/bold red]")
        return None


def extract_vulnerabilities(trivy_report: dict) -> list:
    vulns = []
    for result in trivy_report.get("Results", []):
        for v in result.get("Vulnerabilities", []):
            vulns.append({
                "id":                v.get("VulnerabilityID"),
                "severity":          v.get("Severity"),
                "title":             v.get("Title", ""),
                "installed_version": v.get("InstalledVersion", ""),
                "fixed_version":     v.get("FixedVersion", ""),
            })
    return vulns


# ── LLM patch generation ───────────────────────────────────────────────────────

def ask_ai_for_patch(vulns: list, base_image: str, client: OpenAI, model: str) -> str:
    prompt = (
        f"I scanned Docker image '{base_image}' with Trivy and found these vulnerabilities:\n"
        f"{json.dumps(vulns, indent=2)}\n\n"
        "Write a secure replacement Dockerfile. Upgrade the base image to a patched version, "
        "add apt-get/apk upgrade if needed. Output ONLY valid Dockerfile content — no markdown, "
        "no explanation, no code fences."
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a DevSecOps engineer. Output ONLY Dockerfile content."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        console.print(f"[bold red]LLM call failed: {e}[/bold red]")
        return ""


# ── CLI ────────────────────────────────────────────────────────────────────────

@app.command()
def scan(image: str):
    """Scan a Docker image and generate a patched Dockerfile."""
    client, model, provider = _resolve_client()
    console.print(
        f"[bold cyan]Auto-Patch-AI[/bold cyan] — "
        f"provider: [green]{provider}[/green]  model: [yellow]{model}[/yellow]"
    )
    console.print(f"Scanning image: [yellow]{image}[/yellow]\n")

    with Progress() as progress:
        t1 = progress.add_task("[green]Running Trivy...", total=100)
        report = run_trivy(image)
        progress.update(t1, advance=100)

        if not report:
            raise typer.Exit(1)

        vulns = extract_vulnerabilities(report)

    severity_counts = {}
    for v in vulns:
        severity_counts[v["severity"]] = severity_counts.get(v["severity"], 0) + 1
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if sev in severity_counts:
            color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "dim"}.get(sev, "white")
            console.print(f"  [{color}]{sev}[/{color}]  {severity_counts[sev]}")

    if not vulns:
        console.print("\n[bold green]Image is clean — no patching needed.[/bold green]")
        raise typer.Exit(0)

    console.print(f"\nFound [bold red]{len(vulns)}[/bold red] vulnerabilities. Generating patch...\n")

    with Progress() as progress:
        t2 = progress.add_task("[magenta]Consulting LLM...", total=100)
        patched = ask_ai_for_patch(vulns[:20], image, client, model)
        progress.update(t2, advance=100)

    if patched:
        console.print(Panel(patched, title="Dockerfile.secure", border_style="green"))
        with open("Dockerfile.secure", "w") as f:
            f.write(patched)
        console.print(
            "\n[bold green]Saved to Dockerfile.secure[/bold green]\n"
            "Test it: [yellow]docker build -f Dockerfile.secure -t myapp:patched .[/yellow]"
        )


if __name__ == "__main__":
    app()
