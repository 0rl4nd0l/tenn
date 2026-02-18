from datetime import date
from dateutil import parser as dtparser
EXTRACTOR_VERSION="ollama_json_v1"
def build_prompt(text:str)->str:
    clipped=(text or "")[:18000]
    return f"""You are a financial document extraction engine. Output ONLY valid JSON.
Schema:
{{
  "period_type": "Q|H|A|null",
  "period_end": "YYYY-MM-DD|null",
  "metrics": {{
    "revenue": "number|null",
    "ebit": "number|null",
    "np_attributable": "number|null",
    "operating_cf": "number|null",
    "investing_cf": "number|null",
    "financing_cf": "number|null",
    "capex": "number|null",
    "cash_end": "number|null",
    "net_debt": "number|null",
    "shares_outstanding": "number|null"
  }},
  "confidence_metrics": "0..1",
  "risk_summary": "string|null",
  "risk_bullets": "array<string>|null",
  "guidance_summary": "string|null",
  "material_changes": "string|null",
  "confidence_narrative": "0..1"
}}

Document text:
"""+clipped
def parse_period_end(s:str|None)->date|None:
    if not s: return None
    try: return dtparser.parse(s).date()
    except Exception: return None
