# Phase 5a - reading the RCP interaction sections (before Prolog)

Pipeline
1. data/raw/rcp/*.pdf  (20 RCP PDFs, downloaded from base-donnees-publique.medicaments.gouv.fr, one per Level-A substance)
2. scripts/extract_rcp_sections.py -> data/processed/rcp_sections/<substance>_4.3.txt / _4.5.txt
   -> data/processed/interaction_candidates.csv  (98 rows: 30 by substance name, 68 by drug class) - all TO_REVIEW
3. data/processed/interactions_reviewed.csv      (52 findings: 23 from the 30 name-matched candidates + 29 from the 68 class-matched ones)
4. data/processed/class_matches_not_applied.csv  (class matches that turned out NOT to concern our substances, with the reason)
5. data/processed/interaction_pairs.csv           (29 unordered pairs = the table the Prolog engine will read)

Columns of interactions_reviewed.csv
- rcp_category: the heading under which the RCP lists the interaction (ANSM structure: contre-indiquées / déconseillées / précautions d'emploi / à prendre en compte).
  Some RCP (amlodipine, atorvastatine, azithromycine, omeprazole) have no such headings -> "non classé".
- engine_level (PROPOSED by the AI, to be validated): 4 contraindicated, 3 avoid, 2 caution, 1 consider, 0 no interaction found.
  level_basis says how it was decided: rcp_heading | rcp_heading_combined | rcp_wording | ai_default (no RCP category: weakest).
- condition: dose/population condition stated in the RCP (matters: aspirin at anti-inflammatory vs antiplatelet doses gives different levels).
- evidence_quote: short verbatim extract (<15 words) to check against the PDF.
- text_clarity: garbled_table = the PDF table was mangled by text extraction -> check the PDF by eye.
- use_in_rules = no for "no interaction found" rows (kept as evidence, not as rules).

Rules of the game
- Nothing here is medical validation. Every row is AI_READ_NEEDS_HUMAN_CHECK: ideally a pharmacist/pharmacy student checks them.
- When two RCP disagree on the level for the same pair (ibuprofen/aspirin, clarithromycin/atorvastatin), the engine will use the MORE cautious one and show both sources.
- These RCP are French. Moroccan product leaflets may differ.
- Class-level matches (e.g. 'AINS', 'diurétiques', 'corticoïdes') were read too: 68 rows = 49 distinct passages.
  Many were NOT valid: 'macrolide' in the clarithromycin RCP refers to clarithromycin itself; 'diurétiques hyperkaliémiants' is not furosemide;
  'bêta-bloquants non sélectifs' does not name bisoprolol. These are listed in class_matches_not_applied.csv, never silently dropped.
- A class mention is applied to one of our substances only if the substance belongs to the class AND the text does not restrict it
  (examples named in the text, selectivity, dose). Doubtful cases are use_in_rules=review.

interaction_pairs.csv (input of Phase 5b = Prolog)
- engine_level_max: highest level among the sources (the engine is deliberately the cautious one); levels_seen + level_conflict show disagreements between RCP
  (6 pairs, e.g. aspirin/diclofenac: 1, 2 or 3 depending on the aspirin dose).
- dose_dependent = a condition (dose, patient risk) is attached: the engine must display it, not just the level.
- needs_review = at least one low-confidence or 'review' row (4 pairs). Two pairs have no level on purpose (aspirin/metformin, bisoprolol/salbutamol): a pharmacist must decide.
- Result: 1 pair level 4 (clarithromycin + domperidone), 5 pairs level 3, 16 pairs level 2, 5 pairs level 1.

Not covered yet
- Interactions with drugs OUTSIDE the 20 substances (warfarin, lithium, methotrexate, ACE inhibitors...). The engine will say "not in my knowledge base" for those.
- Section 4.3 (contraindications by condition: pregnancy, severe asthma with bisoprolol, renal failure...) - next step, same method.
