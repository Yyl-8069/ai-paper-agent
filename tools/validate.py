from pathlib import Path
from pymarkdown.api import PyMarkdownApi

def validate_markdown(path):
    path=Path(path)
    api=PyMarkdownApi()
    # Academic equations, extracted headings, and table lines require content review.
    for rule in ["MD013","MD024","MD025","MD033","MD041"]:
        api.disable_rule_by_identifier(rule)
    result=api.scan_path(str(path.resolve()))
    issues=[{"file":f.scan_file,"line":f.line_number,"rule":f.rule_id,
             "name":f.rule_name,"description":f.rule_description} for f in result.scan_failures]
    return {"path":str(path),"status":"issues" if issues else "passed","issues":issues}
