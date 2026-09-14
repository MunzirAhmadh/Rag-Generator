# How to run this in 45 minutes

## Files, in order

| # | File | Budget |
|---|------|--------|
| 0 | `00_BRIEF.md` | 0 min (context only, paste first) |
| 1 | `01_core_pipeline.md` | ~15 min |
| 2 | `02_streamlit_ui.md` | ~10 min |
| 3 | `03_tests_and_readme.md` | ~15 min |
| — | your own manual smoke test | ~5 min |

## Steps

```bash
mkdir rag-generator && cd rag-generator
opencode
```
Paste `00_BRIEF.md` first. Then paste `01_core_pipeline.md`,
`02_streamlit_ui.md`, `03_tests_and_readme.md` in order, one at a time,
letting each finish and report its acceptance criteria before pasting
the next. Don't run them in parallel or skip ahead — this set is
deliberately small (3 stages, 2 code files) specifically so it fits the
time budget; the value of staging is still "verify before proceeding,"
just compressed.

## If you're already behind schedule mid-build

- Cut scope further inside a stage rather than abandoning tests — e.g.
  in Stage 3, 5 solid tests beat 10 rushed ones.
- The one thing not to cut: the not-found test. It's the single most
  specific, checkable requirement in the brief ("not found" behavior),
  so if you're triaging, protect that one.
- If Ollama isn't installed/running in your environment yet, do that in
  parallel with Stage 1 — don't let it block code review, but you do
  need it working before your Stage 2 manual smoke test.

## After Stage 3

1. `ollama pull nomic-embed-text && ollama pull llama3.2` (if not already
   done), `ollama serve`, `streamlit run app.py` — do one real end-to-end
   pass yourself: upload `company_handbook.txt`, ask a real question,
   confirm citations; swap to `product_faq.txt`, rebuild, ask again; ask
   something off-topic, confirm the not-found message.
2. Export the opencode session transcript into `transcripts/`.
3. `git push`, submit via the form.
