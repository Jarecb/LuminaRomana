Verbbank: Tests and code updates

Summary

This document records changes made to add English translations to Verbbank entries and the corresponding test updates.

Code changes

- app/models/domain.py
  - VerbbankEntry now includes an optional translation: str = "" field.
- app/storage/sqlite.py
  - verbbank table schema extended with: translation TEXT NOT NULL DEFAULT ''
  - Upsert and search SQL updated to persist and query translation
  - Repository now returns the translation on read
- app/services/learning.py
  - When auto-upserting verbbank entries from lesson tokens, the service attempts to populate translation from:
    1. an existing WordbankEntry definition if present
    2. AIService.generate_glosses when available
- app/ui/web.py
  - Verbbank listing now renders the English translation next to each verb.

Tests updated/added

- tests/test_storage_sqlite.py
  - Extended the verbbank storage test to upsert an entry with a translation and assert it is persisted and returned by search.
  - Ensures search still finds entries by conjugation tokens.
- tests/test_web.py
  - Added test_verbbank_shows_translation_from_ai: monkeypatches AIService.generate_conjugations and generate_glosses and asserts the /verbbank page shows the English gloss.

Notes for maintainers

- Backwards compatibility: VerbbankEntry.translation has a default of empty string so existing code that constructs VerbbankEntry without translation continues to work.
- DB migration: To add the translation column to existing SQLite databases, run:

  ALTER TABLE verbbank ADD COLUMN translation TEXT NOT NULL DEFAULT '';

- Tests: run locally (PowerShell 6+ required for CI tooling in this environment):

  python -m pytest -q

Contact

If anything breaks or additional test coverage is desired (e.g., testing migration, or more UI formatting), open an issue or request further changes.
