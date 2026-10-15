# Third-party materials in Aster

Aster's own code is MIT-licensed by its owner (`LICENSE`). That licence does not cover third-party material.

For v2 releases (0.2.0 and later):

- Component inventory with licence, source and how Aster obtains each component:
  [packaging/notices/THIRD_PARTY_COMPONENTS.md](packaging/notices/THIRD_PARTY_COMPONENTS.md). The installed app
  ships this file and the licence texts in `notices/`, plus the licence files of every frozen Python package in
  `notices/python-packages/`.
- Rights register with the redistribution basis per component: [packaging/asset-rights-v2.csv](packaging/asset-rights-v2.csv).
  Licence checks were automated and AI-reviewed. **The owner's review of each row is still pending.**
- Reference library packs: each pack's `NOTICE.md` and `documents.jsonl` record the licence, licence URL,
  attribution and source URL of every document.
  - The core pack holds only CC0, CC BY, CC BY-SA and US public-domain material.
  - CC BY-NC and CC BY-NC-SA material is isolated in the optional noncommercial pack.
  - No-derivatives (ND) licences are excluded.
  - MedlinePlus A.D.A.M. encyclopedia and ASHP drug monographs are excluded.

No publisher, model author or dataset provider endorses Aster. Nothing in these notices is clinical validation.

The v1 inventory (ValidationOnly builds) is kept in [docs/history/README-2026-10-11.md](docs/history/README-2026-10-11.md)
and `packaging/asset-rights.csv`.
