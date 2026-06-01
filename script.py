import os
from pathlib import Path

def create_project_structure():
    # Define the base directory
    base_dir = Path("incident-iq")
    
    # Define the structure as a list of paths
    structure = [
        base_dir / "data" / "logs",
        base_dir / "scripts",
        base_dir / "src" / "incident_iq",
    ]
    
    # Define files to create
    files = [
        base_dir / "pyproject.toml",
        base_dir / ".env.example",
        base_dir / ".gitignore",
        base_dir / "scripts" / "generate_logs.py",
        base_dir / "src" / "incident_iq" / "__init__.py",
        base_dir / "src" / "incident_iq" / "agent.py",
        base_dir / "src" / "incident_iq" / "log_reader.py",
        base_dir / "src" / "incident_iq" / "reporter.py",
        base_dir / "main.py",
    ]
    
    # Create directories
    for folder in structure:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {folder}")
        
    # Create empty files
    for file in files:
        file.touch(exist_ok=True)
        print(f"Created file: {file}")

if __name__ == "__main__":
    create_project_structure()