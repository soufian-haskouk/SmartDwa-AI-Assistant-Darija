import sys
from . import config

# drug_linker.py يعيش في scripts/ (نسخة واحدة للمشروع)
sys.path.insert(0, str(config.ROOT / "scripts"))
from drug_linker import DrugLinker  # noqa: E402

def load_linker() -> DrugLinker:
    cw = config.PROCESSED / "common_words.txt"
    return DrugLinker(str(config.PROCESSED / "alias_table.csv"),
                      common_words_file=str(cw) if cw.exists() else None)
