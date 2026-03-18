import fitz


def extract_text_from_pdf(pdf_path: str) -> str:
    with fitz.open(pdf_path) as doc:
        return "\n".join([p.get_text("text") for p in doc]).strip()
