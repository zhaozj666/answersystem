class _Para:
    def __init__(self, text: str = ""):
        self.text = text


class Document:
    def __init__(self, path: str):
        self.paragraphs = []
