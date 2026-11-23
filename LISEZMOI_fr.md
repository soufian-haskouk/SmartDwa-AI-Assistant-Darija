# Patch : intention XLM-R distante (mode `remote`) + garde « drapeaux rouges »

Copier ces fichiers par-dessus votre projet (mêmes chemins), puis `docker compose up -d --build`.
**Aucun changement de comportement par défaut** : `INTENT_BACKEND=local` (sklearn + règles).

Contenu : `backend/app/{intent,config,orchestrator,main}.py`, `backend/app/safety/redflags.py`, `docker-compose.yml` (variables `INTENT_*`), `tests/test_intent_remote.py` (+16 tests ; 89 au total chez moi), `docs/intent_v5_guide_fr.md` (lire en premier), `ml/` (données v5, validateur de vraies questions, serveur d'intention).

⚠️ `orchestrator.py` et `main.py` : si vous les avez modifiés vous-même depuis mes derniers patchs, fusionnez à la main (changements : `intent in ("out_of_scope","symptoms_query")`, source `remote_model`, `intent == "symptoms_query"` → générateur, `/health` montre `intent_backend`).

Activation (après entraînement XLM-R et lancement du notebook tunnel) :
```
INTENT_BACKEND=remote
INTENT_URL=https://xxxx.trycloudflare.com
```
(`INTENT_TOKEN` = `HEALTH_GEN_TOKEN` par défaut.)
