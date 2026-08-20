# PDF Structural Analysis

## Finding 1 — PDF Widgets

The sample PDFs contain no detectable PDF widgets.

Therefore, the parser cannot rely on AcroForm/widget metadata.

## Finding 2 — Text Blocks

A single text block can contain multiple questions.

Therefore, one block cannot be directly mapped to one Question object.

## Finding 3 — Question Numbers

Question numbers are embedded within extracted text and can sometimes appear separately from their question text.

Question numbers can therefore be used as an important parsing signal, but not as the only signal.

## Finding 4 — Word Coordinates

PyMuPDF word extraction provides bounding-box coordinates.

These coordinates will be required to associate question numbers, question text, and options based on their spatial relationship.

## Finding 5 — Drawings

The sample contains a large number of drawing objects.

Many appear to represent page layout elements such as borders, lines, and rectangles. Drawings should therefore initially be treated as supporting structural information rather than directly mapped to form controls.

## Finding 6 — Sections

The form contains identifiable sections such as "Demographics" and "Outcomes Registry".

The domain model should therefore represent Sections separately from Questions.

## Initial Parsing Strategy

PDF
→ text/graphic extraction
→ normalized raw elements
→ spatial grouping
→ question detection
→ option association
→ structured Question/Section objects

## Finding 7 — Revision Structure Differs

R6.0 contains 2 pages while R7 contains 5 pages.

Therefore, page-to-page comparison cannot be used as the primary matching strategy.

## Finding 8 — Text Block Granularity Differs

R6.0 frequently groups multiple questions into a single text block.

R7 contains much more granular question-level blocks.

Therefore, block identity cannot be used as the question identity.

## Finding 9 — Checkbox Indicators

Choice options in R7 are extracted with a checkbox-like character
(\uf06f) followed by the option text.

Therefore, option extraction can initially be performed from text
rather than relying exclusively on vector drawings or OCR.

## Finding 10 — Drawings Are Inconsistent

R6 contains hundreds of drawing objects, while several R7 pages
contain zero drawings.

Therefore, drawings should be treated as secondary structural
information rather than the primary source for question extraction.

## Updated Parsing Strategy

PDF
↓
Text + coordinates
↓
Normalize extracted elements
↓
Detect question numbers
↓
Group text around question numbers
↓
Detect and associate options
↓
Create structured Question objects
↓
Compare revisions
↓
Use LLM only for semantic interpretation and summary