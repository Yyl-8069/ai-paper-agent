import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "collection.sqlite"
        with self.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS papers(id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT,source_id TEXT,UNIQUE(source,source_id));
            CREATE TABLE IF NOT EXISTS versions(ref TEXT PRIMARY KEY,paper INTEGER,
              version INTEGER,metadata TEXT,collected TEXT,state TEXT);
            CREATE TABLE IF NOT EXISTS artifacts(path TEXT PRIMARY KEY,ref TEXT,kind TEXT,
              sha256 TEXT,size INTEGER,status TEXT);
            CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,kind TEXT,period TEXT,
              path TEXT,refs TEXT,coverage TEXT,created TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,time TEXT,
              run_id TEXT,step TEXT,details TEXT);
            """)
    def connect(self):
        c = sqlite3.connect(self.db, timeout=30)
        c.row_factory = sqlite3.Row
        return c
    def safe_path(self, path):
        p = Path(path)
        p = (p if p.is_absolute() else self.root / p).resolve()
        if not p.is_relative_to(self.root) or p == self.root:
            raise ValueError("路径超出资料库")
        return p
    def directory(self, ref):
        if not re.fullmatch(r"P[0-9]{6,}/v[1-9][0-9]*", ref):
            raise ValueError("无效论文编号")
        return self.safe_path(Path("papers") / ref)
    def register(self, candidate):
        data = dict(candidate)
        if (type(data.get("version")) is not int or data["version"] < 1
                or not data.get("source_id") or not data.get("title")):
            raise ValueError("论文身份或版本无效")
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT id FROM papers WHERE source=? AND source_id=?",
                            (data["source"], data["source_id"])).fetchone()
            n = row[0] if row else c.execute(
                "INSERT INTO papers(source,source_id) VALUES (?,?)",
                (data["source"], data["source_id"])).lastrowid
            ref = f"P{n:06d}/v{data['version']}"
            c.execute("INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?,?)",
                      (ref,n,data["version"],json.dumps(data,ensure_ascii=False),now(),"registered"))
        return ref
    def lookup(self, ref):
        with self.connect() as c:
            row = c.execute("SELECT * FROM versions WHERE ref=?", (ref,)).fetchone()
        if row is None:
            raise KeyError(ref)
        return {**json.loads(row["metadata"]),"ref":ref,"collected":row["collected"],"state":row["state"]}
    def papers(self):
        with self.connect() as c:
            refs = [r[0] for r in c.execute("SELECT ref FROM versions ORDER BY paper,version")]
        return [self.lookup(r) for r in refs]
    def set_state(self, ref, state):
        with self.connect() as c:
            c.execute("UPDATE versions SET state=? WHERE ref=?", (state,ref))
    def record_artifact(self, ref, kind, path):
        p = self.safe_path(path)
        if ref:
            self.lookup(ref)
        if not p.is_file():
            raise FileNotFoundError(p)
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?,?,?)",
                      (p.relative_to(self.root).as_posix(),ref,kind,digest(p),p.stat().st_size,"present"))
    def artifacts(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM artifacts")]
    def record_report(self, report):
        p = self.safe_path(report["path"])
        for ref in report["references"]:
            self.lookup(ref)
        self.record_artifact(None,"summary",p)
        with self.connect() as c:
            c.execute("INSERT INTO reports VALUES(?,?,?,?,?,?,?)",
                      (report["id"],report["kind"],report["period"],
                       p.relative_to(self.root).as_posix(),json.dumps(report["references"]),
                       json.dumps(report["coverage"],ensure_ascii=False),now()))
    def reports(self):
        with self.connect() as c:
            return [{**dict(r),"refs":json.loads(r["refs"]),"coverage":json.loads(r["coverage"])}
                    for r in c.execute("SELECT * FROM reports")]
    def event(self, run_id, step, details):
        with self.connect() as c:
            c.execute("INSERT INTO events(time,run_id,step,details) VALUES(?,?,?,?)",
                      (now(),run_id,step,json.dumps(details,ensure_ascii=False)))
    def export_index(self):
        lines=["# 论文索引","","| 编号 | 标题 | PDF | Markdown |","| --- | --- | --- | --- |"]
        for p in self.papers():
            d=self.directory(p["ref"])
            title=p["title"].replace("|","/").replace("\n"," ")
            pdf="存在" if (d/"original.pdf").is_file() else "无本地文件"
            md="存在" if (d/"paper.md").is_file() else "无本地文件"
            lines.append(f"| {p['ref']} | {title} | {pdf} | {md} |")
        atomic_text(self.root/"index.md","\n".join(lines)+"\n")
