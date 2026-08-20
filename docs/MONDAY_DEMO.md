# Monday Demo Checklist

## 1. Normal comparison

Run:

```bash
python app.py data/samples/samplev1.pdf data/samples/samplev2.pdf --json output/comparison.json --html output/comparison.html
```

Show:
- removed questions
- renumbered questions
- field-type changes
- option-set changes
- text changes

## 2. Offline demonstration

Disable Wi-Fi and run the same command. The comparison should still complete because the active path has no cloud API dependency.

## 3. Confidentiality explanation

Explain:

> The current comparison path processes PDF content locally. We do not require Gemini/OpenAI or another hosted AI service for the core comparison, so confidential document content does not need to leave the machine.

Do not claim the system is fully enterprise-secure or audited.

## 4. Password-protected PDF

Explain that encrypted PDFs require the correct password and are authenticated locally. Wrong/missing passwords stop processing. No password bypass is attempted.

## 5. LLM question

If asked whether we trained an LLM:

> No. Training a foundation LLM from scratch is outside the scope of this prototype. We moved the core comparison intelligence into our own deterministic local pipeline. A local pretrained/fine-tuned model can be integrated later behind the matcher if the dataset and evaluation results justify it.


## What to show if asked how matching works

The current prototype does not claim to have trained an LLM. It creates a structured representation locally and matches questions using normalized text, token overlap, option similarity, field type and question-number signals. The CLI can export ranked matching diagnostics with `--diagnostics` so the team can inspect why two questions were paired.

For a future semantic layer, a locally deployed pretrained embedding model can be placed behind the matcher interface. That would still keep document contents on the local machine during inference.


## Offline/security demonstration

1. Run the comparison with Wi-Fi disabled.
2. Show the JSON `mode`, `security`, and `offline_verification` fields.
3. Explain that the core reads the PDFs locally and does not create temporary
   extraction copies.
4. For encrypted PDFs, demonstrate a correct password and an incorrect
   password. The latter stops processing; no bypass is attempted.
5. For enterprise deployment, state explicitly that host/container network
   controls and a security review are still required.
