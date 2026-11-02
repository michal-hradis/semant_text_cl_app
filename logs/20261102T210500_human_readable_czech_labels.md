# Human-readable Czech class labels (DB data change)

- Backup: `backend/db.bak/database.sqlite.before_cs_labels_20261102`.
- In `backend/database.sqlite`, every task's `classes[].label_cs` had underscores replaced by spaces.
  English or non-standard labels were translated or fixed: communicative_mode `other_mode`→`jiný způsob`,
  `uncertain`→`nejasné`; geographic_scope `multi_national_nebo_kontinentální`→`mezinárodní nebo kontinentální`,
  `ne_zeměpisný`→`nezeměpisný`; structural_form `garbage`→`poškozený`;
  textual_stance `neutrální_deskriptivní`→`neutrální popisný`; emotional_tone `laskavý_nebo něžný`→`laskavý nebo něžný`.
- `description_md` prompts were rewritten so that every class reference is the exact backticked `label_cs`.
  This fixed typos, variants and inflected forms (e.g. `vykladový`, `žurnalistický`, `podpořeno_důkazy`,
  `obecným_přehledem`, „…“ quotes) and broken backticks in communicative_mode and textual_stance.
- Class IDs are unchanged, so existing annotations (which store IDs) are unaffected.
- The `prompts/*.md` source files were NOT updated.

## Follow-up: DDC classes added to subject_domain

- Backup: `backend/db.bak/database.sqlite.before_ddc_classes_20261102`.
- Added the 10 DDC classes that the prompt described but the task lacked. IDs follow `prompts/subject_domain.md`
  (`ddc_000_generalia`, `ddc_100_philosophy_psychology`, … `ddc_900_history_geography`). Czech labels are readable
  without the code prefix (`filozofie a psychologie`, …). Descriptions come from the Czech prompt.
- The prompt's `ddc_…` references were replaced with these labels. The `(DDC nnn)` codes stay in the class list.
