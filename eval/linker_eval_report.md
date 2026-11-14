# Drug linker evaluation (Phase 3)

## A. Synthetic typos (225 CNOPS brand/DCI names, Latin, length>=6)

| edits | Top-1 | Top-3 | found anything | wrong Top-1 |
|---|---|---|---|---|
| 0 | 100.0% | 100.0% | 100.0% | 0.0% |
| 1 | 97.3% | 97.3% | 97.3% | 0.0% |
| 2 | 68.4% | 69.3% | 69.8% | 1.3% |

Caveat: the noisy words come from the same vocabulary the linker knows, so this is an upper bound.

## B. Hand-written cases (62)

strict = only actionable hits count; lenient = low-confidence/ambiguous hits count too.

| kind | n | strict exact | lenient exact | wrong actionable hits | needs confirmation |
|---|---|---|---|---|---|
| arabic | 16.0 | 75% | 100% | 0.0 | 4.0 |
| arabizi | 6.0 | 83% | 100% | 0.0 | 1.0 |
| latin_brand | 11.0 | 91% | 100% | 0.0 | 1.0 |
| latin_dci | 1.0 | 100% | 100% | 0.0 | 0.0 |
| latin_typo | 8.0 | 75% | 100% | 0.0 | 2.0 |
| negative | 10.0 | 100% | 100% | 0.0 | 0.0 |
| sentence | 10.0 | 80% | 100% | 0.0 | 2.0 |

**Overall:** strict 84%, lenient 100%, wrong actionable hits: 0


Caveat: these cases were written by an AI, not by a native Darija speaker. Review them and add real user messages.

## C. MedQA_MA sample (4000 patient questions)

- questions with any drug hit: 129 (3.2%)
- in-scope hits: 57 (actionable 22, ambiguous 5, low-confidence 34)
- out-of-scope drug hits (handled safely): 94

**Manual review (done by the AI assistant on the seed=7 sample of 4000, so a Moroccan reader should re-check):**
- all 22 *actionable* in-scope hits were genuine drug mentions;
- of the 35 non-actionable (need confirmation) hits: 5 clearly false (e.g. a hair-removal 'flash', marjoram, sulpiride, glibenclamide, 'baby'), 4 undecidable, ~26 plausible real mentions (mostly Arabic spellings of brands).
- Lesson: ordinary words collide with brand names by sound, so Arabic-script matches that are not exact DCI/CNOPS names must be confirmed with the user.
