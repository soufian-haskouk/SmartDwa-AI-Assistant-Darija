# Phase 1 - drug master (CNOPS 2014 + AMMPS + BDPM)

Command
    python scripts/build_drug_master.py --cnops data/raw/cnops/ref-des-medicaments-cnops-2014.xlsx \
        --bdpm-dir data/raw/bdpm --ammps data/raw/ammps_medicaments.csv --out data/processed

Output
- data/processed/drug_master.csv      2,515 rows = 1,498 AMMPS + 1,017 CNOPS-2014, one row per (product x Level-A substance), column `source` tells the registry.
- data/processed/substances_reference.csv   per substance: BDPM figures (cis, routes, forms), French prescription flags.
- data/processed/coverage_report.csv        per substance and per source: rows, brands, missing prices, AMMPS "Commercialisé" rows.
- *_cnops2014_only.csv / alias_table_v1.csv / eval/linker_eval_report_v1.md = state BEFORE AMMPS, kept for comparison.

What each source brings
- AMMPS (Moroccan regulator, 9,908 rows): status (Commercialisé / Non commercialisé / Retiré du marché / AMM sans prix / AO), AMM status, P/G (PP/GN), laboratory, therapeutic class, PPV/PH. NO date of collection in the file.
- CNOPS 2014: reimbursement rate (TAUX_REMBOURSEMENT), PPV from 2014. Only ~45% of its products match AMMPS by name+dose+form (merge report of the DwaTalk project), so the two registries are kept as separate rows, NOT merged.
- BDPM: French reference only (substance facts, prescription lists).

Parsing rules (AMMPS)
- Prices are written "133,30 DH" or "1.141.00 DH" (dot thousands + dot decimals) or "SANSPPV DH" (no price, 1,097 rows) -> `parse_price`.
- Several active substances are separated by " // ".
- Statuses: only "Commercialisé" is treated as available in pharmacies. "Commercialisé AO" / "AO / Export" probably means tender/hospital/export (ASSUMPTION, not stated in the file).
- Synonym added by the AI (to confirm with a pharmacist): acétylsalicylate (e.g. lysine salt: Aspegic) counts as acetylsalicylic acid.

Observations (coverage_report.csv)
- AMMPS is richer for atorvastatine (52 vs 13 rows), bisoprolol (30 vs 9), paracétamol (141 vs 71), ibuprofène (57 vs 37); poorer for amoxicilline (150 vs 157) and aspirin.
- 9 substances have <=10 AMMPS "Commercialisé" mono-ingredient rows (e.g. lopéramide 1, lévothyroxine 4).

Limits
- The ranking "princeps / generic" is the registry's own (PP / GN), not verified.
- Unknown date of the AMMPS scrape: prices and status may be out of date. Say so in the report.
- BDPM `fr_rx_flags_any` is "any product has this list" (misleading): use `fr_pct_cis_with_rx_condition`.
