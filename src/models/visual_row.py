class VisualRow:
    def __init__(self, page_number, y0):
        self.page_number = page_number
        self.y0 = y0
        self.elements = []

    def add_element(self, element):
        self.elements.append(element)

    def get_text(self):
        sorted_elements = sorted(
            self.elements,
            key=lambda element: element.x0
        )

        return " ".join(
            element.text
            for element in sorted_elements
            if element.text.strip()
        )

    def __repr__(self):
        return (
            f"VisualRow("
            f"page={self.page_number}, "
            f"y={self.y0:.2f}, "
            f"text={self.get_text()!r}"
            f")"
        )