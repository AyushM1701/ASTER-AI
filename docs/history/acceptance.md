# Acceptance stories

1. Ask “What is asthma?” → extractive reference note with a valid server citation,
   source excerpt, snapshot and a primary HTTPS URL. Outside-library questions
   produce insufficient_evidence. Individual medication decisions are blocked.
2. Use synthetic document → real OCR candidates → visually compare/edit → explicit
   confirmation → new revision → applicable metformin label note. Explanation
   without confirmation or with an old revision fails. Omitted duration stays null.
3. Select a permitted reviewed adult AP/PA asset after weight setup → hash and
   technical gates → separate classifier → selected scores labelled research-only.
   This journey's code is implemented; activation and real-image validation are
   pending external assets. No demonstration success for this story is claimed.
4. Corrupt, animated, oversized, unregistered or unsupported inputs abstain before
   OCR or imaging. Urgent guidance works independently of retrieval and Ollama.
5. Clear a session → token revoked and API state removed. Another session's IDs
   never grant access. Expiry during OCR cannot recreate deleted state.
