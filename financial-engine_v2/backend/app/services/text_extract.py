import fitz

def extract_text_from_pdf(pdf_path:str)->str:
    doc=fitz.open(pdf_path)
    return '\n'.join([p.get_text('text') for p in doc]).strip()
