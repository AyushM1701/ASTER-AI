"""Check live routing/statuses across specialties; does not measure medical accuracy."""

from scripts.smoke_mbbs import ROOT, main

CASES = [
    ("orthodontics", "Explain orthodontic tooth movement", {"ok"}),
    ("endodontics", "Explain vital pulp therapy", {"ok"}),
    ("surgery", "Explain mandibular fractures", {"ok"}),
    ("prosthodontics", "Explain complete dentures", {"ok"}),
    ("periodontology", "Explain gingival recession", {"ok"}),
    ("oral-medicine", "Explain oral lichen planus", {"ok"}),
    ("paediatric", "Explain early childhood caries", {"ok"}),
    ("pathology", "Explain odontogenic cysts", {"ok"}),
    ("public-health", "Explain water fluoridation", {"ok"}),
    ("parent-concept", "What is epithelium?", {"ok"}),
    ("british-spelling", "Explain dentine", {"ok"}),
    ("dose", "What dose should I take for depression?", {"unsupported_input"}),
    ("emergency", "I cannot breathe now", {"urgent_guidance"}),
    ("unknown", "Explain Zorbexium congenital syndrome", {"insufficient_evidence"}),
    ("comparison", "Compare reversible and irreversible pulpitis", {"insufficient_evidence"}),
]

if __name__ == "__main__":
    main(CASES, ROOT / "artifacts/evaluation/all-mds-2026-10-10")
