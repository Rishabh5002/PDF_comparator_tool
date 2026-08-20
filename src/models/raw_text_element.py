class RawTextElement:
    def __init__(
        self,
        text,
        page_number,
        x0,
        y0,
        x1,
        y1,
        block_number,
        line_number,
        word_number,
    ):
        self.text = text
        self.page_number = page_number
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.block_number = block_number
        self.line_number = line_number
        self.word_number = word_number

    def __repr__(self):
        return (
            f"RawTextElement("
            f"text={self.text!r}, "
            f"page={self.page_number}, "
            f"bbox=({self.x0}, {self.y0}, {self.x1}, {self.y1}), "
            f"block={self.block_number}, "
            f"line={self.line_number}, "
            f"word={self.word_number}"
            f")"
        )