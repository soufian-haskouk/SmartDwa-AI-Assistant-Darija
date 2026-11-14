مصادر RCP تُقرأ من مكانين (PDF له الأولوية):
  data/raw/rcp/<stem>.pdf        مثال: acide_acetylsalicylique_aspirine.pdf
  data/raw/rcp_html/<stem>.html  صفحة BDPM محفوظة (/extrait)، ومعها sources.csv (المنتج المختار لكل مادة)
الأسماء (stem): paracetamol, ibuprofene, acide_acetylsalicylique_aspirine, diclofenac, omeprazole, domperidone, loperamide,
amoxicilline, azithromycine, clarithromycine, metformine, levothyroxine, amlodipine, bisoprolol, atorvastatine, furosemide,
salbutamol, loratadine, cetirizine, prednisolone
الناقص الآن: loperamide, azithromycine, levothyroxine.
التشغيل: docker compose run --rm rcp-extract   (أو: python scripts/build_rcp_sections.py)
