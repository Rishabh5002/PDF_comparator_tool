import pymupdf

def explore_page(page):
    blocks = page.get_text("blocks")
    words = page.get_text("words")
    drawings = page.get_drawings()
    widgets = list(page.widgets() or [])

    print("=" * 70)
    print(f"PAGE {page.number + 1}")
    print("=" * 70)

    print(f"Blocks   : {len(blocks)}")
    print(f"Words    : {len(words)}")
    print(f"Drawings : {len(drawings)}")
    print(f"Widgets  : {len(widgets)}")

    print("\n--- BLOCKS ---")

    for index, block in enumerate(blocks):
        print(f"\nBlock {index}")
        print(block)

    print("\n--- WORDS ---")

    for index, word in enumerate(words[:30]):
        print(f"Word {index}: {word}")

    print("\n--- DRAWINGS ---")

    for index, drawing in enumerate(drawings[:10]):
        print(f"\nDrawing {index}")
        print(drawing)

    print("\n--- WIDGETS ---")

    for index, widget in enumerate(widgets):
        print(f"\nWidget {index}")
        print(widget)

def main():
    document = pymupdf.open("data/samples/samplev2.pdf")

    print(f"File: {document.name}")
    print(f"Pages: {document.page_count}")

    for page in document:
        explore_page(page)

    document.close()


if __name__ == "__main__":
    main()