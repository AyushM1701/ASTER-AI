# Local MBBS teaching model comparison

Keep the existing text/vision configuration. This small controlled test did not establish a quality gain from activating the downloaded 4B model; both models achieved 5/13 strict lexical/structured passes, and 4B took about twice as long on warm prompts. Clinical correctness is unknown; qualified faculty review was not performed.

| Measurement | qwen3-vl:2b-instruct | qwen3:4b-q4_K_M |
|---|---:|---:|
| Controlled cases | 13 | 13 |
| Strict bounded reference passes | 5 | 5 |
| API/decode/truncation errors | 0 | 0 |
| Median warm wall time (s) | 3.130 | 6.304 |
| First model load (s) | 4.497 | 7.506 |
| Median generated tokens/s | 122.90 | 59.96 |
| Sampled peak process working set (GiB) | 1.333 | 1.706 |
| Model GPU offload allocation (GiB) | 1.620 | 2.792 |
| Minimum available system RAM (GiB) | 6.786 | 6.195 |

Both models receive the same 13 source-backed prompts: anatomy, physiology, biochemistry, microbiology, immunology, pharmacology, pathology, clinical medicine, community medicine, ethics, MCQ, fictional case and unavailable evidence. References are short developer-authored synopses of official government text. They are supplied directly; this is separate from the end-to-end teaching retrieval evaluation.

Controls: two CPU threads, seed 42, temperature 0, 2048-token context, 768 output-token ceiling, non-thinking mode and the same JSON schema. Publisher templates and tokenizers differ. Installed Ollama 0.35.1 uses the validated Settings loopback endpoint http://127.0.0.1:11434. NVIDIA RTX 4050 laptop has 6141 MiB device memory; 4B was fully offloaded according to /api/ps. The official pull verified SHA256 before writing its manifest. Exact digests:

- `qwen3-vl:2b-instruct`: `ea422f1e73652a95479954d8572d3c8c6022f628ce2d38a1a04aae1b7f2d5300`
- `qwen3:4b-q4_K_M`: `2bfd38a7daaf4b1037efe517ccb73d1a3bbd4822cf89f1a82be1569050a114e0`

The strict pass count is not an answer-accuracy percentage. It requires complete relational facts in the claim list, exact source quotes, no recognized contradictions or unmapped claims, correct MCQ selection and evidence availability. Manual review exposed conservative scorer false positives: 4B insulin deficiency was wrongly interpreted as insulin blocking uptake; 2B MCV was marked contradictory while rejecting an incorrect premise. Correct paraphrases, split relations and additional supported facts also fail narrow rules. Non-MCQ choice letters are recorded as separate protocol deviations and are not included in the strict score.

The developer inspected all 26 raw outputs for source/prompt deviations. Examples: 2B passive-immunity prose mistakenly mentions a vaccine as a source of transferred antibodies; its antibiotic fact list repeats the false premises despite corrective prose. 4B gives a cleaner passive-immunity explanation, but alters two purported exact quotes and invents a citation identifier in the sickle-cell answer. Its plain B12 explanation also misspells a substrate while the detail section is correct. Both abstain on the fictional unsupported drug. Detailed findings and unscored protocol issues are in `developer-review.json`; these observations are not a medical faculty evaluation.

One fixed-order trial cannot establish robustness. First-prompt wall times were 6.934 s and 26.672 s, including loading, preparation and generation. A brief final teaching-v2 CPU embedding build may overlap the comparison; exact overlap was not sampled. Memory is 250 ms sampled process working set, which can double-count shared pages and miss brief peaks; GPU offload allocation is not peak device VRAM. All latency/resource results depend on background desktop workload.

Official model/license metadata: [Ollama4B registry](https://ollama.com/library/qwen3:4b-q4_K_M), [Qwen publisher card](https://huggingface.co/Qwen/Qwen3-4B). The explicit Q4 tag has 4.02B parameters, about 2.6 GB download and Apache-2.0 license. It was selected over 8B because available RAM was about 8.1 GiB during selection. Source provenance: `../source-snapshots/source-register.json`, `../source-mapping-review-final.json`; [CDC reuse policy](https://www.cdc.gov/other/agencymaterials.html), [NIH FAQ copyright policy](https://www.nih.gov/about-nih/frequently-asked-questions), [NIDDK copyright](https://www.niddk.nih.gov/copyright). Third-party media are excluded. ODS/HHS/NIH FAQ raw downloads returned403 while official content was verified in the research browser; those raw-snapshot gaps are explicit. Current OpenStax material was excluded due to its AI-ingestion restriction.

The 18 focused tests passed and Ruff is clean. A full suite run during development passed 226 tests with one existing Starlette deprecation warning; final combined verification belongs to the parent integration task. The stronger model remains installed for future evaluation; active configuration and vision model remain unchanged.
