import httpx, json, re
def ollama_embed(ollama_url:str, model:str, texts:list[str], timeout:float=180.0)->list[list[float]]:
    vecs=[]
    with httpx.Client(timeout=timeout) as c:
        for t in texts:
            r=c.post(f"{ollama_url}/api/embeddings", json={"model":model,"prompt":t})
            r.raise_for_status()
            data=r.json()
            vec=data.get("embedding")
            if not isinstance(vec,list):
                raise RuntimeError(f"Bad embeddings response: {data}")
            vecs.append(vec)
    return vecs

def ollama_generate_json(ollama_url:str, model:str, prompt:str, timeout:float=240.0)->dict:
    with httpx.Client(timeout=timeout) as c:
        r=c.post(f"{ollama_url}/api/generate", json={"model":model,"prompt":prompt,"stream":False})
        r.raise_for_status()
        txt=r.json().get("response","")
    m=re.search(r"\{.*\}", txt, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON found in model response: {txt[:400]}")
    return json.loads(m.group(0))
