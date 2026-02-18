from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import re
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from urllib.parse import urljoin

ASX_ANNOUNCEMENTS_URL="https://www.asx.com.au/asx/v2/statistics/announcements.do"
ASX_BASE_URL="https://www.asx.com.au"

@dataclass
class DiscoveredDoc:
    ticker:str
    exchange:str
    doc_class:str
    doc_subtype:str
    title:str
    source_url:str
    published_at:Optional[datetime]=None
    period_end:Optional[datetime]=None

def _classify(title:str)->Tuple[str,str]:
    t=(title or "").lower()
    if "appendix 4c" in t: return "quarterly","4C"
    if "appendix 4d" in t: return "half_year","4D"
    if "appendix 4e" in t: return "annual","4E"
    if any(k in t for k in ["half year","half-year","interim"]): return "half_year","report"
    if any(k in t for k in ["annual","full year","year ended","annual report"]): return "annual","report"
    if any(k in t for k in ["quarterly","quarter","activities","cashflow","cash flow","production"]): return "quarterly","activities"
    return "quarterly","other"

def _try_period_end(title:str)->Optional[datetime]:
    m=re.search(r"(?:ended|year ended|half year ended|quarter ended)\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", title or "", flags=re.I)
    if not m: return None
    try: return dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
    except Exception: return None


def _clean_title(raw:str)->str:
    title=(raw or "").strip()
    title=re.sub(r"\s+"," ",title)
    title=re.sub(r"\b\d+\s*pages?.*$","",title, flags=re.I).strip()
    return title or "ASX Announcement"

class ASXProvider:
    def __init__(self, timeout:float=60.0):
        self.timeout=timeout
    def discover(self, ticker:str, start:datetime, end:datetime)->List[DiscoveredDoc]:
        ticker=ticker.upper()
        docs:List[DiscoveredDoc]=[]
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as c:
            seen=set()
            years=range(start.year, end.year+1)
            for year in years:
                params={"asxCode":ticker,"by":"asxCode","timeframe":"Y","year":str(year)}
                r=c.get(ASX_ANNOUNCEMENTS_URL, params=params, headers={"User-Agent":"Mozilla/5.0"})
                r.raise_for_status()
                soup=BeautifulSoup(r.text,"lxml")
                anchors=soup.find_all("a", href=True)
                pdf=[
                    a
                    for a in anchors
                    if (
                        a["href"].lower().endswith(".pdf")
                        or "displayannouncement.do" in a["href"].lower()
                    )
                ]
                if not pdf: break
                for a in pdf:
                    url=urljoin(ASX_BASE_URL, a["href"])
                    if url in seen: 
                        continue
                    seen.add(url)
                    title=_clean_title(a.get_text(" ", strip=True) or a.get("title") or "ASX Announcement")
                    published=None
                    row=a.find_parent(["tr","div"])
                    if row:
                        txt=row.get_text(" ", strip=True)
                        m=re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", txt)
                        if m:
                            try: published=dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                            except Exception: published=None
                        else:
                            m2=re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", txt)
                            if m2:
                                try: published=dtparser.parse(m2.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                                except Exception: published=None
                    if published and (published<start or published>end):
                        continue
                    doc_class, doc_subtype=_classify(title)
                    docs.append(DiscoveredDoc(ticker=ticker,exchange="ASX",doc_class=doc_class,doc_subtype=doc_subtype,title=title,source_url=url,published_at=published,period_end=_try_period_end(title)))
        return docs
