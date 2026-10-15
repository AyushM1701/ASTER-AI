# Published reference library

The repository includes the consolidated `artifacts/source-packs/mds-master-evidence-candidate-v5-2026-10-13` library: 7,791 records, 411 sources, metadata, syllabus and 65 prepared explanation units. The 666 original source and license snapshot files referenced by its source manifest are also included at their original paths. Their recorded hashes were verified before publication.

The application code's MIT license does **not** license this material. Each source retains its own license, attribution and publisher terms in `sources.yaml` and the accompanying license snapshots. These include CC BY, CC BY-SA, CC BY-NC and CC BY-NC-SA, and publisher public-domain/reuse statements. Preserve these notices, observe noncommercial restrictions where present, and apply the source's share-alike obligations to adaptations. No publisher endorsement or qualified medical review is implied.

This is a development candidate, not a validated clinical library. The latest source-only pilot returned 20 substantive answers in 111 turns, including 5 complete substantive answers. Publication does not establish complete MDS coverage.

For development use without a downloaded embedding index, put these explicit overrides in your local `.env`:

```dotenv
ENABLE_TEACHING=true
TEACHING_BACKEND=lexical
TEACHING_RELEASE_PATH=artifacts/source-packs/mds-master-evidence-candidate-v5-2026-10-13
TEACHING_EXPLANATIONS_PATH=artifacts/source-packs/mds-master-evidence-candidate-v5-2026-10-13/explanations.json
TEACHING_EXPLANATIONS_SHA256=d8d639ca9a5f9f7433e996232c345efea42d98f035559f0b6845291effa31a93
```

The pretrained conversational model is downloaded separately with `setup-chat.ps1`. No retraining is required to search this reference pack. Historical intermediate libraries, unrelated raw downloads, private data, model weights and generated indexes are outside this publication.
