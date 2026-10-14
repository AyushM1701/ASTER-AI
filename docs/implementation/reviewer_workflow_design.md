# Local review workflow

Use a separate local SQLite registry for private reviewer qualification declarations, randomized blind case mappings, per-reviewer assignments and immutable submissions. Packet exports omit model/baseline labels and private reviewer identities; original question, answer, source/span identity and any separately authored reference rubric remain fixed and hashed. Missing reference rubrics remain null. All transfer stays manual and local unless separately authorized.

Assignment-specific bearer tokens authorize imports; store only token hashes. Bind the submitted packet, rubric and each case to exact hashes. Validate an entire import before its transaction commits. Require a distinct third assigned reviewer for adjudication after two submissions, preserve original disagreements, and calculate nominal Cohen kappa only from paired nonmissing dimensions. Revisions require a new batch; never overwrite a score or silently change a blinded answer.

Tokens establish possession of an assignment, not a dentist's identity or qualification. Qualification records are declarations, externally unverified. No workflow action closes F03, creates reference labels, authenticates medical credentials, or changes the production evidence registry. Actual specialist review, independent rubrics and credential verification remain external dependencies.
