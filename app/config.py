import os
from pathlib import Path
from agents.researcher import Researcher

PROJECT=Path(__file__).resolve().parents[1]

def load_config():
    values={}
    path=PROJECT/".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k,v=line.split("=",1)
                if k in {"DEEPSEEK_API_KEY","DEEPSEEK_MODEL"}:values[k]=v.strip()
    for key in ("DEEPSEEK_API_KEY","DEEPSEEK_MODEL"):
        if os.environ.get(key):values[key]=os.environ[key]
    return values

def researcher():
    c=load_config()
    return Researcher(c.get("DEEPSEEK_API_KEY",""),c.get("DEEPSEEK_MODEL","deepseek-flash"))
