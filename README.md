# Private Q&A

Ask questions about a company's own documents (PDF, Word, text) and get a short answer with the exact source sentence and page. Each person can only search the documents their groups allow. When the documents do not say, it refuses instead of guessing. Includes an admin library, user and group management, an editable glossary, a question log with a "could not answer" list, an n8n chat version, and an evaluation. The firm and all 12 documents are dummy data generated here.

**Demo videos and write-up:** [ismailmoeen.dev](https://ismailmoeen.dev/#work)

## Run
```
pip install -r requirements.txt
DEMO_MODE=1 INBOUND_KEY=change-me uvicorn app.main:app --port 8000
python scripts/seed.py http://127.0.0.1:8000     # documents, users, glossary, a few logged questions
```
Demo sign-ins (password `welcome123`): ayesha (staff), omar (HR), sara (finance), imran (legal). Admin password in demo mode: `demo`. Without `ADMIN_PASSWORD` or `DEMO_MODE`, a random admin password is printed at start. An unset `INBOUND_KEY` means the chat endpoint is closed, never open.

## How it answers
1. A person's readable set is the documents whose groups include one of theirs (plus "everyone"). A separate search index is built per readable set, so restricted text is never in the index someone queries.
2. Search: BM25 on stemmed words, character n-gram similarity for spelling and word forms, and an editable glossary for company vocabulary ("holiday = annual leave").
3. Refusal gate: the best passage must cover enough of the question's words and score above a threshold, otherwise the answer is "I could not find this in the documents you have access to." The text is identical whether the document is restricted or does not exist.
4. The answer is the best one or two sentences of the best passage (extractive), shown with the document, section and page, and the sentence highlighted in its passage.
5. Every question is logged (who, when, question, answered or not, top document, score). The answer text is not stored.

## Tests and evaluation
```
pip install -r requirements-dev.txt && pytest     # 47 tests, offline
python eval/run_eval.py dev|heldout|fresh [--show]
python data/make_docs.py                           # regenerates the dummy documents
```

## Settings (environment)
`DB_PATH, ADMIN_PASSWORD, INBOUND_KEY, SECRET_KEY, MIN_SCORE, MIN_COVERAGE, TOP_K, MAX_UPLOAD, LLM_PROVIDER` (`rules` or `ollama`; with `ollama` a local model writes the answer but must quote sentences that are present in the passages, otherwise the rules answer is used), `OLLAMA_URL, OLLAMA_MODEL`.

## Limits
Search is lexical (no semantic embeddings were available where this was built), so very different wording needs a glossary entry. The documents are generated, short and clean. The local-model path is tested with a mock only. Scanned PDFs need OCR first. Everything runs on one machine and one SQLite file.
