# Local Matching Evaluation

The supplied sample revisions are the first regression fixture.

## Current observed result

- Revision 1: 22 parsed questions
- Revision 2: 18 parsed questions
- 18 logical one-to-one matches
- 4 unmatched questions from revision 1: 8, 9, 10 and 18
- 0 unmatched questions from revision 2

The matching engine uses normalized text, meaningful-token overlap, option/field signals and question-number signals. It is deterministic and runs without a hosted AI service.

## Important limitation

The supplied PDFs are not a complete ground-truth benchmark. The parser is heuristic and the comparison output must be reviewed against actual form semantics before claiming production-level accuracy.

## Recommended benchmark

Create labelled revision pairs covering: added question, removed question, reordered question, renamed question, changed options, changed field type, changed child logic, and cosmetic-only changes. Record expected results so thresholds can be tuned against measurable false positives and false negatives.
