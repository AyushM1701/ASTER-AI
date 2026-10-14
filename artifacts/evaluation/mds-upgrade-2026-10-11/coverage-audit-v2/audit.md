# Locked pilot contract audit v2

This is a read-only developer audit of the preserved `cpu-reviewed` run: 150 candidate prompts, 0 complete, 2/357 validated expected bindings. The bank and scorer remain unchanged. Input hashes, the recorded runtime checksum map and every case's evidence appear in `audit.json`.

## Actionable runtime defects

| Issue | Affected cases | Required regression |
|---|---:|---|
| histology_architecture_alias | 27 | Architecture becomes structure rather than architectural_features despite explicit histopathological context. |
| explicit_histopathology_discarded | 27 | Explicit histopathology is removed when cytological or architectural features are also requested. |
| pedagogic_cell_instruction_as_scope | 30 | The response instruction 'in each cell' is appended as a required source scope. |
| comparison_axis_in_entity | 12 | An unresolved comparison entity includes 'along definition and histopathology' in its local ID. |
| compound_entity_shadowed | 6 | Explicit amelogenesis imperfecta is resolved as the shorter process amelogenesis. |
| mechanism_subject_is_article | 12 | Unresolved mechanism subject becomes local:the rather than the noun phrase after 'mechanism of'. |
| subject_facet_collision | 2 | A facet word inside the explicit entity suppresses/truncates that entity (inflammation or exfoliative cytology). |
| research_setup_instead_of_appraisal | 3 | Source-backed appraisal request is routed to research setup without the requested topic/facet contract. |

Unknown-topic essays also lose the response plan (see the per-case rows). Preserve explicit noun phrases across definition, mechanism, essay and research instructions; facets inside an entity name are not automatically requested operations. Keep true clinical scopes such as children, pregnancy and population restrictions. Parent runtime owners must separately address source-backed appraisal routing and authentic source readiness.

## Evaluation contract limits

The 27 histology prompts say 'where applicable', while their frozen descriptors require architecture, cytology and histopathology for every entity. Qualified reviewers must assess applicability before describing clinical completeness; no expected facet is removed here. The three appraisal descriptors omit the explicitly requested diagnostic limitations from their expected facets. Exact topic-word relevance can miss legitimate synonyms and is a separate signal from completion. No observed response satisfied all validated expected facets with canonical complete yet was rejected by completion scoring, so this audit does not establish an actual medically correct answer falsely scored incomplete.

## Source and review gate

All cases still require evidence adequacy assessment. Recorded rejection reasons are engineering observations, not proof that authoritative knowledge is absent. The active release has no production reviewed_facet_bindings. Correct topic/facet parsing is necessary but cannot turn tangential research paragraphs into foundational teaching units. Stage only permitted, authentic sources with their qualifications and coordinate bindings; independent qualified review remains pending F03. Neither this audit nor passing tests constitutes human source approval.

## Per-case reasons

| Case | Operation | Validated / expected facets | Reason codes |
|---|---|---:|---|
| pilot-001 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-002 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-003 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-004 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-005 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-006 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-007 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-008 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-009 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-010 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-011 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-012 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-013 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-014 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-015 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-016 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-017 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-018 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-019 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-020 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-021 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-022 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-023 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-024 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-025 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-026 | definition | 0/1 | subject_facet_collision, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-027 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-028 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-029 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-030 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-031 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-032 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-033 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-034 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, compound_entity_shadowed, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-035 | essay | 1/3 | partial_validated_support |
| pilot-036 | definition | 0/1 | compound_entity_shadowed, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-037 | mechanism | 0/1 | compound_entity_shadowed, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-038 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, compound_entity_shadowed, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-039 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, compound_entity_shadowed, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-040 | essay | 0/3 | compound_entity_shadowed, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-041 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-042 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-043 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-044 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-045 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-046 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-047 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-048 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-049 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-050 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-051 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-052 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-053 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-054 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-055 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-056 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-057 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-058 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-059 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-060 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-061 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-062 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-063 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-064 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-065 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-066 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-067 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-068 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-069 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-070 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-071 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-072 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-073 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-074 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-075 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-076 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-077 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-078 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-079 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-080 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-081 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-082 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-083 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-084 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-085 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-086 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-087 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-088 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-089 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-090 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-091 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-092 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-093 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-094 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-095 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-096 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-097 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-098 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-099 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-100 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-101 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-102 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-103 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-104 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-105 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-106 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-107 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-108 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-109 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-110 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-111 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-112 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-113 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-114 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-115 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-116 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-117 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-118 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-119 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-120 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-121 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-122 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-123 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-124 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-125 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-126 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-127 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-128 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-129 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-130 | essay | 1/3 | partial_validated_support |
| pilot-131 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-132 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-133 | histology | 0/3 | histology_architecture_alias, explicit_histopathology_discarded, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-134 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-135 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-136 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-137 | mechanism | 0/1 | no_validated_support_in_recorded_response |
| pilot-138 | research_appraisal | 0/2 | no_response_plan, research_setup_instead_of_appraisal, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-139 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-140 | essay | 0/3 | no_validated_support_in_recorded_response |
| pilot-141 | definition | 0/1 | subject_facet_collision, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-142 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-143 | research_appraisal | 0/2 | no_response_plan, research_setup_instead_of_appraisal, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-144 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, comparison_axis_in_entity, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-145 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-146 | definition | 0/1 | no_validated_support_in_recorded_response |
| pilot-147 | mechanism | 0/1 | mechanism_subject_is_article, expected_pairs_absent_from_plan, unrequested_facets_in_plan, no_validated_support_in_recorded_response |
| pilot-148 | research_appraisal | 0/2 | no_response_plan, research_setup_instead_of_appraisal, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
| pilot-149 | comparison | 0/4 | pedagogic_cell_instruction_as_scope, no_validated_support_in_recorded_response |
| pilot-150 | essay | 0/3 | no_response_plan, expected_pairs_absent_from_plan, no_validated_support_in_recorded_response |
