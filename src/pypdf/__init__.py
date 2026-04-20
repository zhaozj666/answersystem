class _Page:
    def __init__(self, text: str = ""):
        self._text = text

    def extract_text(self):
        return self._text


class PdfReader:
    def __init__(self, path: str):
        self.pages = []
