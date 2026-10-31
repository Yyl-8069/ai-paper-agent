import json
import re
from pathlib import Path
import httpx
from tools.credentials import validate_api_key

PROMPTS=Path(__file__).resolve().parents[1]/"prompts"

class Researcher:
    def __init__(self,key,model="deepseek-flash",client=None):
        if not key:raise ValueError("请先配置 DEEPSEEK_API_KEY")
        self.key=validate_api_key(key);self.model=model;self.client=client

    def summarize(self,materials,kind):
        if not materials:
            return {"sections":[],"coverage":{},"usage":[]}
        missing=[m for m in materials if not m["text"].strip()]
        if missing:
            present=[m for m in materials if m["text"].strip()]
            result=self.summarize(present,kind)
            for m in missing:
                result["sections"].append({"heading":"Missing content", "text":"Local full text and abstract are unavailable; no research conclusions generated.","refs":[m["ref"]]})
                result["coverage"][m["ref"]]="missing_content"
            return result
        if len(materials)>120:raise ValueError("本批材料过多，请缩小总结范围")
        allowed={m["ref"] for m in materials}
        budget=max(500,60000//len(materials))
        coverage={}
        supplied=[]
        for m in materials:
            text=m["text"]
            cov=m.get("coverage","extracted_unverified")
            if len(text)>budget:cov+=";excerpt"
            coverage[m["ref"]]=cov
            supplied.append({"ref":m["ref"],"title":m.get("title",""),
                             "coverage":cov,"text":text[:budget],
                             "evidence":m.get("evidence",{})})
        system=(PROMPTS/"constraints.md").read_text(encoding="utf-8")+"\n"+(PROMPTS/(kind+".md")).read_text(encoding="utf-8")
        body={"model":self.model,"messages":[{"role":"system","content":system},
              {"role":"user","content":json.dumps(supplied,ensure_ascii=False)}],
              "response_format":{"type":"json_object"},"thinking":{"type":"disabled"},
              "temperature":0.2,"max_tokens":5000,"stream":False}
        owned=self.client is None
        client=self.client or httpx.Client(timeout=120,trust_env=False)
        try:
            response=client.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization":"Bearer "+self.key},json=body)
            if response.status_code>=400:
                raise RuntimeError(f"DeepSeek 请求失败 HTTP {response.status_code}，请检查密钥、余额和模型配置")
            payload=response.json()
            if payload["choices"][0].get("finish_reason")=="length":
                raise ValueError("模型输出超长而被截断")
            result=json.loads(payload["choices"][0]["message"]["content"])
        finally:
            if owned:client.close()
        sections=result.get("sections")
        if not isinstance(sections,list) or not sections:raise ValueError("模型缺少 sections")
        for section in sections:
            if (not isinstance(section,dict) or not isinstance(section.get("heading"),str)
                    or not isinstance(section.get("text"),str) or not section["text"].strip()
                    or not isinstance(section.get("refs"),list) or not section["refs"]
                    or any(not isinstance(r,str) for r in section["refs"])):
                raise ValueError("模型输出结构无效")
            embedded=set(re.findall(r"P[0-9]{6,}/v[1-9][0-9]*",section["text"]))
            if not set(section["refs"])<=allowed or not embedded<=allowed:
                raise ValueError("invalid reference in model output")
        return {"sections":sections,"coverage":coverage,
                "usage":[{"model":self.model,"tokens":payload.get("usage"),"cost":"unknown"}]}
