"""Serialize explicit whole-unit findings from the completed Codex source reading.

Selections below are manual evidence decisions. No matching or tag inference is
used. This script preserves exact publisher units and records unsupported facets.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from backend.app.services.question_plan import RequestedFacet
from backend.app.services.reviewed_evidence import reviewed_support
from scripts.stage_mds_inspected_pack import load_teacher

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/references/mds/releases/aster-teaching-all-mds-v3-2026-10-10"
OUTPUT = ROOT / "artifacts/source-review/mds-foundations-v2"

# tuple: whole unit, topic, explicitly supported facets, reasoning, limitation,
# exact retained qualification phrases. Full units were read in context.
DECISIONS = [
    ("chunk_445b03532f31ab4dbd17806e", "sulcular_epithelium", ["definition", "structure", "functions", "histopathology"],
     "Identifies crevicular epithelium, its squamous lining, lack of tooth attachment, healthy absence of rete pegs, and relative permeability. These are separate named structural and functional observations.",
     "Normal sulcular teaching account, not diseased histology or a measurement of clinical attachment. The healthy-condition qualifier and deeper-region permeability distinction remain.", ["under healthy conditions", "especially in the deeper regions closer to the junctional epithelium"]),
    ("chunk_90bcc3daa650e0adaa18d9ec", "junctional_epithelium", ["definition", "structure", "functions", "histopathology"],
     "Defines JE, describes hemidesmosomal tooth attachment, fewer desmosomes and leukocyte passage; gives orientation-qualified thinness rather than an unqualified five-layer measurement.",
     "Preserve the direction-of-measurement explanation and lost-attachment condition. This normal-anatomy unit does not establish implant equivalence or periodontal treatment efficacy.", ["relative to the apical-to-basolateral direction of the epithelium, not the apical-to-coronal direction of the tooth", "especially if the epithelial attachment is lost"]),
    ("chunk_46d2a30b72cb2fac1dd7230c", "nonkeratinized_epithelium", ["structure", "histopathology", "anatomical_examples"],
     "Names labial and buccal mucosa with a nonkeratinized stratified squamous epithelial layer and explains focal keratinization where stressed.",
     "Specific examples only; no complete nonkeratinized-layer enumeration. Retain the local exceptions and lining-mucosa context.", ["there can be regions of keratinization where stress occurs"]),
    ("chunk_90f63c78862f2e784567be33", "nonkeratinized_epithelium", ["structure", "anatomical_examples"],
     "Explicitly identifies ventral tongue and mouth floor as thin nonkeratinized stratified squamous epithelial examples.",
     "Normal anatomical examples; sublingual administration mention is explanatory, not dosing or treatment advice.", []),
    ("chunk_fc064ffa84f4bdc84141f936", "nonkeratinized_epithelium", ["structure", "functions", "anatomical_examples"],
     "Identifies soft-palate lining and connects its attachment to deeper muscle to speech and swallowing.",
     "One site-specific structural/function account, not all lining mucosa or an epithelial-layer inventory.", []),
    ("chunk_873c0756c852f7fa4b27866d", "keratinized_epithelium", ["structure", "anatomical_examples"],
     "Identifies hard palate as orthokeratinized stratified squamous epithelium with a mostly absent submucosa and rigid bony attachment.",
     "Retain 'mostly'; no claim that submucosa is absent at every hard-palate site. Does not enumerate keratinized layers.", ["mostly lacks a sub-mucosa"]),
    ("chunk_b95033ee03402b857b906385", "keratinized_epithelium", ["structure", "histopathology", "anatomical_examples"],
     "Attached gingiva is explicitly parakeratinized stratified squamous epithelium; papillae/rete pegs and stippling are described with pigmentation qualification.",
     "Normal tissue description; stippling is not a standalone clinical health test. Pigmentation caveat must remain.", ["which can be described as whitish in the absence of melanin"]),
    ("chunk_46d2a30b72cb2fac1dd7230c", "oral_epithelium", ["anatomical_examples", "histopathology"],
     "Provides exact normal squamous epithelial histology of labial and buccal oral sites, with local stress-associated keratinization exception.",
     "Contributes normal oral-site histology, not a complete oral-epithelium definition, layer inventory or general functional essay.", ["there can be regions of keratinization where stress occurs"]),
    ("chunk_55f91caa759b7ebd78090b88", "tooth_development", ["mechanism", "stages", "epithelial_mesenchymal_interactions"],
     "Describes neuro-mesenchymal morphogen gradients, ectodermal response, FGF/BMP families, inhibitory spacing signals and placode induction in stated order.",
     "The unit explicitly says the initial step is poorly understood, more signals exist, stage terminology varies and human fate mapping is difficult. These qualifications prevent treating this simplified account as a complete proven pathway.", ["The first step is poorly understood.", "There are more signals involved", "Not every book (or exam) includes placode as its own stage", "fate mapping experiments can’t easily be done on humans"]),
    ("chunk_729bd2981690da3db611457e", "tooth_development", ["stages", "histopathology", "architectural_features"],
     "Bud-stage prose identifies ectodermal proliferation, visible bud shape, and denser proliferating neuro-mesenchyme compared with nearby mucosal mesenchyme.",
     "Histopathology here means the requested developmental microscopic description of normal embryonic structures; it does not claim diseased tissue. The plant-bud analogy is retained as an analogy, not literal anatomy.", ["Tooth buds begin to appear around week 6"]),
    ("chunk_75292cc9ca327866fc0a22bc", "tooth_development", ["stages", "histopathology", "architectural_features"],
     "Cap-stage unit describes the epithelial cap around the dental papilla, enamel organ, dental sac and tooth-germ arrangement; second paragraph qualifies successional development and molar exceptions.",
     "Normal developmental microscopy and lineage account, not a diagnostic claim. Retain molar exceptions and variability in tooth-germ movement.", ["Exceptions to this include the 2nd and 3rd molars", "the tooth germ of succedaneous teeth can move as they develop"]),
    ("chunk_8a4b2e2d81200de1cbf81694", "tooth_development", ["mechanism", "epithelial_mesenchymal_interactions"],
     "States reciprocal induction of enamel- and dentin-producing cells and why re-creating those spatial/temporal conditions is difficult; distinguishes neural-crest mesenchyme from germ-layer mesoderm.",
     "High-level reciprocal-induction concept, not a complete molecular pathway. Tooth eruption remains explicitly poorly understood and contested.", ["There are multiple steps which are poorly understood", "scientists disagree on which steps are important"]),
    ("chunk_eaa46b0c37912b6ccd34fe20", "tooth_development", ["stages", "mechanism", "architectural_features"],
     "Describes IEE/OEE cervical loop, HERS extension and its role guiding root pattern with postnatal growth and delayed mineralization.",
     "Retain time differences for primary/succedaneous teeth and the explicit mold analogy; HERS guides the root rather than becoming root tissue. This is normal development, not disease histology.", ["months for primary teeth, and years for succedaneous teeth", "HERS does not become the roots, it guide their shape"]),
    ("chunk_d06db9b355b670c7a21380f1", "tooth_development", ["definition", "stages"],
     "Explicitly defines tooth formation as odontogenesis and places epithelial invagination, dental lamina and early tooth buds in developmental sequence.",
     "Approximate gestational weeks in a 2020 dental-hygiene text; lineage discussion is a simplified developmental model. Not a precise individual timetable or complete molecular mechanism.", ["around weeks 5 to 6", "around weeks 9 to 10"]),
    ("chunk_86636abc4cda9a086af49107", "oral_epithelial_dysplasia", ["definition", "histopathology", "classification", "grading_limitations"],
     "Defines OED as histomorphological epithelial changes with transformation risk, distinguishes architectural/cytological concepts, and discusses three-tier/binary grading and reproducibility limits.",
     "2021 narrative review of then-current classification, not current WHO authority. Table 2 is absent, so the unit does not support enumeration of detailed architectural/cytological criteria. Risk association does not prove inevitable progression.", ["Narrative review; no verified systematic completeness or guideline authority.", "the cutoff between each grade is poorly defined", "not limited to, the epithelial thickness in thirds", "regardless of the system used"]),
    ("chunk_1ea12fcafcb78acc30beb214", "odontogenic_keratocyst", ["definition", "classification"],
     "Explicitly places OKC in the 2022 cyst category, identifies historical tumor/cyst changes, and preserves continuing biological classification debate.",
     "Classification-focused 2022 narrative review only. PTCH mutation associations are not a full causal mechanism; no adequate OKC radiographic or detailed histological comparison is present in this unit.", ["Narrative review; no verified systematic completeness or guideline authority.", "The debate continues."]),
    ("chunk_1ea12fcafcb78acc30beb214", "dentigerous_cyst", ["classification"],
     "Places dentigerous cyst among developmental odontogenic cysts and identifies eruption cyst as a superficial subtype.",
     "Classification only; does not define the attachment to the cementoenamel junction or provide a complete microscopic or radiographic description.", ["Narrative review; no verified systematic completeness or guideline authority."]),
]

EXCLUSIONS = [
    ("chunk_614d6e0b9f4db72b2b152900", "apoptosis", "Generalized RANKL-induced apoptosis and neutralization of acidic mitochondria/lysosomes are not a sound qualification-complete core mechanism; withholding whole unit."),
    ("chunk_44385959c7c7aebec44482c7", "oral_epithelium", "Text reverses ortho/parakeratinized surface nuclear retention and dismisses diagnostic significance. Whole unit withheld."),
    ("chunk_aea2764499f7ed0db2ec19f3", "oral_epithelium", "Whole unit conflates lamina propria and submucosa and overgeneralizes mesodermal connective-tissue lineage. Withheld."),
    ("chunk_c9196e1ebf665f7fad4aac13", "oral_leukoplakia", "Localized increased keratinization is not an adequate exclusion-based leukoplakia definition; therapeutic assertions unappraised. Whole unit withheld."),
    ("chunk_15b8bb71aae00904d1fd31a9", "dentigerous_cyst", "Calls benign ameloblastoma cancer and implies extraction always solves the issue. Full unit withheld."),
    ("chunk_3b3121831adec731da75be43", "tooth_development", "The sequence causing dentin thickness assertion is unsupported; whole unit withheld rather than removing the inconvenient sentence."),
    ("chunk_ae4d29662f5bdff32894b3b8", "necrosis", "Historical narrative describes necrosis as uncontrolled without bound regulated-necrosis context; correction-forward notice concerns cuproptosis attribution only, but this unit remains insufficient for universal core mechanism."),
    ("chunk_386bc7e3ca94e37d1ce343c6", "apoptosis", "Apoptosis pathway details read, but whole unit contains categorical uncontrolled-necrosis claim; withholding until a qualification-complete comparative unit exists."),
    ("chunk_5c730b172d59b99bfa3bf6d1", "oral_leukoplakia", "Definition and clinical features read, but whole unit carries unappraised dated treatment efficacy/generalized interventions; no whole-unit annotation supplied."),
]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    teacher = load_teacher(RELEASE)
    if teacher.error:
        raise ValueError(teacher.error)
    sources = {s["source_id"]: s for s in yaml.safe_load((RELEASE / "sources.yaml").read_text(encoding="utf-8"))["sources"]}
    annotations, excluded = [], []
    try:
        for key, topic, facets, rationale, qualification, retained in DECISIONS:
            row = teacher.references.id_records[key]
            source = sources[row.source_id]
            if teacher.review_flags.get(key):
                excluded.append({"chunk_id": key, "topic_id": topic, "reason": "Inherited release hold", "hold": teacher.review_flags[key]})
                continue
            evidence = {}
            for path_key, hash_key in (("raw_snapshot_path", "raw_sha256"), ("license_snapshot_path", "license_snapshot_sha256")):
                if source.get(path_key):
                    path = ROOT / source[path_key]
                    if hashlib.sha256(path.read_bytes()).hexdigest() != source[hash_key]:
                        raise ValueError("Snapshot changed: " + str(path))
                    evidence[path_key] = source[path_key]
                    evidence[hash_key] = source[hash_key]
            for facet in facets:
                annotation = dict(topic_id=topic, facet=facet, scope="", chunk_id=key, source_id=row.source_id,
                    snapshot_id=row.snapshot_id, section=row.section, section_id=row.section_id,
                    start=0, end=len(row.text), text_sha256=hashlib.sha256(row.text.encode()).hexdigest(),
                    record_sha256=row.content_hash(), source_sha256=row.permission_basis["snapshot_sha256"],
                    review_origin="ai_source_inspection", review_status="source_inspected", reviewer="Codex",
                    clinical_review=False, qualifications_retained=True, retained_qualifications=retained,
                    support_rationale=rationale, qualification_note=qualification,
                    source_context="Complete existing Reference unit read, including adjacent chapter/review units, analogies and explicit exceptions. " + qualification,
                    exact_excerpt=row.text, source_coordinates=teacher.metadata.get(key, {}),
                    source_url=row.url, license=row.permission_basis["license"], license_url=row.permission_basis["license_url"],
                    rights_evidence=evidence, usage_conditions=source.get("terms", "Original item license and attribution retained."),
                    independent_review="pending; AI source inspection is not human, faculty or clinical review")
                context = dict(teacher.metadata.get(key, {}), ai_inspected_facet_bindings=[annotation])
                context.pop("reviewed_facet_bindings", None)
                if not reviewed_support(RequestedFacet(topic_id=topic, facet=facet, scope="", query="manual inspection"), row, context):
                    excluded.append({"chunk_id": key, "topic_id": topic, "facet": facet, "reason": "Whole-unit admission checks rejected this explicit inspection"})
                    continue
                annotations.append(annotation)
        excluded += [dict(chunk_id=k, topic_id=t, reason=r, review_origin="ai_source_inspection", reviewer="Codex") for k, t, r in EXCLUSIONS]
        (OUTPUT / "source-inspection.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in annotations), encoding="utf-8")
        (OUTPUT / "withheld-units.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in excluded), encoding="utf-8")
        report = dict(bindings=len(annotations), units=len({a["chunk_id"] for a in annotations}),
            topics=sorted({a["topic_id"] for a in annotations}), by_license=dict(Counter(a["license"] for a in annotations)),
            whole_unit_check="passed for every exported binding", clinical_review=False, faculty_review="pending",
            incomplete_core_facets=["oral_epithelium definition/layers/functions", "keratinized/nonkeratinized layer inventories",
                "apoptosis intrinsic/extrinsic pathways and all comparison axes", "necrosis complete mechanism and nuclear changes",
                "oral_leukoplakia definition/clinical/histology/dysplasia/investigations", "OED detailed architectural/cytological criterion enumeration",
                "OKC and dentigerous clinical/radiographic/histopathological comparison", "remaining 30-entity pilot topics need separate actual inspection"],
            status="inactive source-inspection artifact; no active source mutation")
        (OUTPUT / "inspection-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=True))
    finally:
        teacher.close()


if __name__ == "__main__":
    main()
