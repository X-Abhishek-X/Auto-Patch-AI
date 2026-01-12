import subprocess
import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
import os
from openai import OpenAI

app = typer.Typer(help="The Zero-Effort Container Security Fixer")
console = Console()

def run_trivy(image_name: str) -> dict:
    """Run Trivy vulnerability scanner on the specified Docker image."""
    try:
        # Run trivy and capture JSON output
        result = subprocess.run(
            ["trivy", "image", "--format", "json", image_name],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Trivy returns exit code 0 even if vulnerabilities exist, unless configured otherwise
        if not result.stdout:
            console.print("[bold red]Failed to capture Trivy output. Is Trivy installed?[/bold red]")
            return None
            
        return json.loads(result.stdout)
    except FileNotFoundError:
        console.print("[bold red]Trivy CLI is not installed or not in PATH.[/bold red]")
        return None
    except json.JSONDecodeError:
        console.print("[bold red]Failed to parse Trivy JSON output.[/bold red]")
        return None

def extract_vulnerabilities(trivy_report: dict) -> list:
    """Extract a summarized list of vulnerabilities from the raw Trivy JSON."""
    vulns = []
    if "Results" in trivy_report:
        for result in trivy_report["Results"]:
            if "Vulnerabilities" in result:
                for v in result["Vulnerabilities"]:
                    vulns.append({
                        "id": v.get("VulnerabilityID"),
                        "severity": v.get("Severity"),
                        "title": v.get("Title", "No title"),
                        "installed_version": v.get("InstalledVersion", ""),
                        "fixed_version": v.get("FixedVersion", "")
                    })
    return vulns

def ask_ai_for_patch(vulns_summary: list, base_image: str) -> str:
    """Send the vulnerabilities to OpenAI/Ollama to generate a patched Dockerfile."""
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
        base_url=os.environ.get("LLM_BASE_URL")  # Use for Ollama (e.g., http://localhost:11434/v1)
    )
    
    prompt = f"""
    I scanned a Docker image named '{base_image}' using Trivy and found the following vulnerabilities:
    {json.dumps(vulns_summary, indent=2)}
    
    Write a brand new 'Dockerfile' capable of building this image securely. 
    It should upgrade the base image to a secure version, install security patches via apk/apt-get if necessary, 
    and output ONLY the contents of the rewritten Dockerfile. Do not use markdown blocks.
    """
    
    try:
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4-turbo"),
            messages=[
                {"role": "system", "content": "You are an elite DevSecOps engineer. Provide ONLY the Dockerfile code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        console.print(f"[bold red]AI Engine failed: {e}[/bold red]")
        return ""

@app.command()
def scan(image: str):
    """Scan an image and generate a remediated Dockerfile magically."""
    console.print(f"🤖 [bold cyan]Auto-Patch-AI[/bold cyan] initializing for [yellow]{image}[/yellow]...")
    
    with Progress() as progress:
        # Phase 1: Scanning
        task1 = progress.add_task("[green]Scanning with Trivy...", total=100)
        report = run_trivy(image)
        progress.update(task1, advance=100)
        
        if not report:
            raise typer.Exit(1)
            
        vulns = extract_vulnerabilities(report)
        console.print(f"\n[bold red]⚠️  Found {len(vulns)} vulnerabilities.[/bold red]")
        
        if len(vulns) == 0:
            console.print("🎉 [bold green]Your image is secure! No patching needed.[/bold green]")
            raise typer.Exit(0)
            
        # Filter for Critical/High if needed, but let's pass all to AI to fix
        
        # Phase 2: Generating Patch
        task2 = progress.add_task("[magenta]Consulting LLM for a secure Dockerfile...", total=100)
        patched_dockerfile = ask_ai_for_patch(vulns[:20], image) # Cap at 20 vulns to fit context window
        progress.update(task2, advance=100)
    
    if patched_dockerfile:
        console.print("\n[bold green]✅ Fixes generated successfully![/bold green]")
        console.print(Panel(patched_dockerfile, title="Secure Dockerfile", border_style="green"))
        
        # Output to disk
        with open("Dockerfile.secure", "w") as f:
            f.write(patched_dockerfile)
        console.print("💾 Wrote patched code to [bold cyan]Dockerfile.secure[/bold cyan]. Build it using [yellow]docker build -f Dockerfile.secure .[/yellow]")

if __name__ == "__main__":
    app()
