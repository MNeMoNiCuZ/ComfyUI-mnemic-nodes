import os
from pathlib import Path
from dotenv import load_dotenv
import shutil

def get_project_root():
    """Get the absolute path to the project root directory."""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent

def ensure_env_file():
    """Ensure .env file exists, create from template if it doesn't."""
    root_dir = get_project_root()
    env_file = root_dir / '.env'
    env_example = root_dir / '.env.example'
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("Created new .env file from template. Please edit it with your API key.")

def get_api_key():
    """Get the Groq API key from environment variables."""
    root_dir = get_project_root()
    load_dotenv(root_dir / '.env')
    
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        raise ValueError("Please set your GROQ_API_KEY in the .env file")
    
    return api_key 