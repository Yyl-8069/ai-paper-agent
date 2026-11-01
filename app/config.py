import os
from pathlib import Path
from agents.researcher import Researcher

PROJECT=Path(__file__).resolve().parents[1]
if PROJECT.drive.casefold() == "c:":
    raise ValueError("项目运行目录不能在 C 盘，请放在 D 盘")
# Direct uvicorn/CLI startup must use the same D-drive temp path as launch scripts.
import tempfile
_runtime_temp = PROJECT/"tmp"
_runtime_temp.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = os.environ["TMP"] = str(_runtime_temp)
tempfile.tempdir = str(_runtime_temp)

def load_config(path=None):
    values={}
    path=Path(path) if path is not None else PROJECT/".env"
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
