# AI source inspection for the staged foundations candidate

`source-inspection.jsonl` contains 38 explicitly inspected facet bindings from
13 complete units already present in the admitted all-MDS v3 teaching release.
Each binding preserves the complete unit, source identity, original paragraph
coordinates, whole-text/record/source hashes, original item license and rights
snapshot evidence, support rationale and limitations. Review origin is
`ai_source_inspection`, reviewer is `Codex`, and clinical review is false.
No human or faculty attestation is supplied.

`scripts/mds_open_inspect_foundations.py` serializes the fixed, manually read
decisions and verifies them through the actual whole-unit admission checks.
It does not infer facets from terms or expand a topic into every facet.
`withheld-units.jsonl` records the two inherited source holds and nine additional
whole units withheld after inspection. Those units are not repaired by clipping
away an inconvenient sentence. Original active source bytes remain unchanged.

The fixed 150-case developer pilot requests 147 distinct topic/facet cells over
30 entities. This inspection supports eight of those cells and records 139
unsupported cells in `facet-gaps.jsonl`. The additional bindings serve named
reconstructed-core anatomical, developmental and classification facets.
This inventory is not a competency, clinical-accuracy or answer-completion score.
`inspection-report.json` preserves the core gaps, including epithelial layers,
apoptosis/necrosis, leukoplakia, detailed dysplasia criteria and cyst comparisons.

Selected bindings retain CC BY-NC-SA 4.0 conditions (31 bindings) or CC BY 4.0
(seven bindings). Existing project authorization is for local noncommercial
educational retrieval; attribution and share-alike conditions remain mandatory.
This candidate does not authorize commercial use, redistribution or training.
The new default-allowlist open collection remains separate and excludes NC/ND.

The `acquired` folder contains nine additional CC BY 4.0 source alternatives
from a bounded official Europe PMC API run. Their authoritative item rights and
asset omissions were screened, but full contextual source inspection and
TeachingStore admission are pending. They contribute no inspected facet bindings
to this pack. Figures/tables/media without independent compatible asset rights
are withheld. Acquisition has stopped. No original excluded full text is stored.

The parent task owns pack staging with `scripts/stage_mds_inspected_pack.py` and
the frozen developer pilot. This artifact never activates a release, changes an
index, supplies clinical approval, or certifies complete national curriculum
coverage. Independent qualified review remains pending.
