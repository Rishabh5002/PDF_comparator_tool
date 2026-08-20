# Local Matching Strategy

The comparison engine does not require Gemini or another hosted AI service.
Questions are matched using an explainable score built from multiple local signals:

1. **Normalized text similarity** — case, punctuation and common formatting differences are normalized.
2. **Meaningful-token overlap** — domain-bearing words are weighted more than boilerplate such as `please`, `enter`, and `patient`.
3. **Option similarity** — overlapping extracted options provide supporting evidence.
4. **Field-type similarity** — text, checkbox, dropdown, etc. are compared as structural evidence.
5. **Question-number proximity** — numbering is only a soft signal; it is not the identity of a question.
6. **Neighbor context** — nearby questions are compared to distinguish simple renumbering from a different question.

The matcher performs one-to-one assignment by strongest candidate score first. A candidate must pass a minimum score and either have strong text evidence or meaningful content overlap. This prevents generic form wording from creating arbitrary matches.

## Why this approach

The supplied revisions demonstrate that PDF page/block structure can change substantially while logical questions remain the same. Therefore, page index, text-block identity, and question number alone are insufficient as identifiers.

The local matcher is intentionally deterministic and auditable. Every accepted match can expose its component signals in `matching_diagnostics.json`.

## Future extension

A local embedding model may be added behind the matcher interface if evaluation on a larger corpus shows that lexical/structural matching is insufficient. That would still keep confidential PDF content local. The current project does **not** claim to have trained an LLM from scratch.
