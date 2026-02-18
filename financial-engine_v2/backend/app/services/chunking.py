def simple_chunk(text:str, max_chars:int=4500):
    text=(text or '').strip()
    return [text[i:i+max_chars] for i in range(0,len(text),max_chars)] if text else []
