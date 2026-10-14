# Controlled local teaching model benchmark

This compares installed `qwen3-vl:2b-instruct` with the official explicit `qwen3:4b-q4_K_M` tag using the same 13 developer-authored educational questions and supplied factual synopses. The active text/vision models and `.env` are not changed.

Source URLs, question types, required relational facts and contradiction patterns are pinned in `configs/mbbs_model_benchmark.json`. The model sees only the reference synopses and questions; it does not see the scorer rubric. Sources are NIH/NIDDK/NHLBI/ODS, CDC and HHS OHRP. Attribution and snapshot limitations are recorded in `source-snapshots/source-register.json` and `source-mapping-review.json`. Text is paraphrased from government educational material; third-party media are excluded. Current OpenStax text was excluded because its page explicitly prohibits AI/LLM ingestion without permission.

The hardware audit identifies a 23.7 GiB machine with an i5-13450HX and an RTX4050 laptop (6141 MiB VRAM). Available RAM during selection was roughly 8.1 GiB. The 4B Q4 model's 2.6 GB download leaves more headroom than an 8B model. The explicit tag is used because the registry's mutable `qwen3:4b` alias now resolves to another thinking revision. Official model metadata: [Ollama registry](https://ollama.com/library/qwen3:4b-q4_K_M), [Qwen publisher card](https://huggingface.co/Qwen/Qwen3-4B). The installed signed Ollama runtime is used; download authorization does not activate a new model in the application.

Run after both models are installed and local embedding/index workloads are finished:

```powershell
.venv/Scripts/python.exe scripts/benchmark_mbbs_models.py
```

The script reads the validated loopback endpoint through `Settings`, checks installed model digests against pinned registry prefixes, and creates an exclusive timestamped artifact directory. Each row contains the exact prompt, raw/decoded model response, error, digest, output counts, load/generation/wall time, process working-set peak, CPU deltas, minimum available RAM, and Ollama's reported loaded-model/GPU offload state. A SHA256 manifest covers all run artifacts. Previous runs are never overwritten. Model caches are unloaded between comparisons; models are not deleted.

`required_fact_recall` matches complete bounded relations in the structured claims. Missing facts, contradictions, extra unmapped claims, wrong MCQ options, invalid schema and truncated generations prevent a bounded pass. Positive relationships reject negated matches; rules representing negative or qualified facts have explicit exceptions and contradiction patterns. `citation_quote_support` requires the cited source, a genuine verbatim substring of the supplied synopsis, and correspondence between the quote and mapped relational fact. Merely copying source terms or adding an invented quote cannot earn a complete pass.

These are lexical reference metrics, not general clinical correctness. Paraphrase sensitivity can produce false negatives, unseen contradiction phrasings and prose outside the structured claims can require manual review, and one fixed-order trial cannot establish robust performance. All cases are educational; no real patient dosing or diagnosis is requested. `clinical_correctness` remains null and `faculty_review` is `not_performed`. There is no claim of MBBS mastery, faculty certification or universal accuracy.

Process memory is sampled every 250 ms and summed across the identified Ollama service and descendants. Shared pages may be double-counted and brief peaks missed. GPU offload allocation from `/api/ps` is not a sampled peak device-VRAM measurement. CPU time misses early execution before first observation. First prompt timings include model loading; subsequent prompts describe warm behavior. Both models use seed42, temperature0, 2048-token context, 768 output-token limit, two CPU threads, identical JSON constraints and disabled thinking; different native templates/tokenizers remain a confounder.

Focused scorer/schema/artifact tests and the full test run are recorded separately. The full run initially passed 226 tests with one existing Starlette test-client deprecation warning; the parent integration task owns final combined verification.

A brief final teaching-v2 CPU embedding build may overlap the live run; this is recorded in the immutable configuration snapshot as a timing/resource limitation.
