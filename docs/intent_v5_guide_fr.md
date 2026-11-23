# Classifieur d'intention v5 — données, intégration XLM-R et vraies questions

> Outil éducatif. Aucune dose, aucun diagnostic, aucune prescription ; urgences prioritaires.

## 1) Ce qui est fait et ce qui ne l'est PAS (honnêteté)
| Élément | État |
|---|---|
| Données v5 (`colab_v5/intent_v5_dataset.csv`), politique P1–P8 vérifiée automatiquement (0 violation sur tous les splits) | **Exécuté** |
| Baseline TF-IDF + régression logistique sur v5 (CPU) : val 0,851 / test 0,840 / gold 0,881 / **fresh 0,890** | **Exécuté** (ce n'est pas XLM-R) |
| Entraînement XLM-R v5 | **NON exécuté** (pas de GPU ici) : à lancer sur Colab. Script testé seulement en `--dry-run` et en `--smoke` sur CPU avec un mini-modèle aléatoire (pipeline OK, chiffres sans valeur) |
| Mode `INTENT_BACKEND=remote` du backend (tests avec serveur simulé + chaîne réelle proxy → serveur d'intention avec mini-modèle) | **Exécuté** : 89 tests passent (16 nouveaux) |
| Colab réel : serveur d'intention XLM-R + tunnel cloudflared | **NON exécuté** (la partie proxy/serveur a été testée en local, pas sur Colab) |
| Précision ≥ 95 % | **Non atteinte et non garantie** (v4 : test_free 0,872, gold 0,903) |

## 2) Nouveautés des données v5
- **Gabarits ciblés** (`V5_EXTRA` dans `ml/intent_v5_data.py`) sur les confusions vues avec v4 : out_of_scope ↔ symptoms_query/price/drug_info, « شحال » prix vs dosage, urgences manquées (douleur thoracique en arabizi, convulsions, étouffement, inconscience, ingestion accidentelle).
- **`test_free` (v4, 407 phrases) devient du développement** : ajouté au train (phrases + 4 variantes bruitées = 966 lignes, source `free_dev`). Il ne peut donc plus servir de test.
- **Nouveau test `test_fresh` : 301 phrases** (`ml/test_v5_intent.psv`, ≈ 30 par classe), écrites après v4 avec d'autres médicaments/tournures, jamais utilisées pour l'entraînement.
- Les gabarits et leur découpage (graine 53) sont régénérés ; `test_gold` (176) est conservé.
- **Lexique RED** : couverture mesurée **avant** toute modification sur les 30 urgences de `test_fresh` = **16/30 (53 %)**. Je l'ai ensuite étendu (motifs : douleur/serrement thoracique, difficulté à respirer, étouffement, inconscience, ingestion « par erreur », idées d'automutilation…), puis resserré (le seul « تنميل » trop large a été retiré ; « النزيف ديال الأنف » après un médicament reste `side_effects`). **Après cette extension, la couverture sur `test_fresh` (30/30) est circulaire : elle ne prouve rien.** 18 questions MedQA contenant un drapeau rouge ont été retirées du train.
- ⚠️ Tout est écrit par l'IA. Intervalle de confiance d'un test de 301 phrases à ~90 % : ± 3,4 points.

## 3) Entraîner (Colab, GPU T4/L4, jamais TPU)
1. Dézipper `smartdwa_intent_v5_colab_pack.zip` (il contient le dossier `colab_v5`), ouvrir `SmartDwa_intent_v5_xlmr.ipynb`.
2. Exécuter dans l'ordre : GPU → upload du pack → `--dry-run` → (optionnel) `real_questions.csv` → `--smoke` → entraînement 3 graines (7, 11, 23) → résumé → zips.
3. Résultats sauvés sur Drive : `smartdwa_intent_v5/xlmr` ; envoyer `results_intent_v5.zip`. Les poids restent sur Drive (`best_model`).
4. Splits évalués : val (sélection du meilleur modèle/graine, uniquement), test, test_gold, **test_fresh**, + test_real si fourni.

## 4) Brancher le modèle (même tunnel que Atlas)
1. Lancer `SmartDwa_Ollama_Colab_Tunnel.ipynb` (version mise à jour) : il démarre Ollama **et** le serveur d'intention (il prend le `best_model` de la version la plus récente dans Drive : `smartdwa_intent_v*/xlmr/best_model`). Un seul proxy à jeton, 2 routes autorisées : `POST /api/chat` et `POST /intent`.
2. La dernière cellule affiche les lignes `.env` ; ajouter :
```
INTENT_BACKEND=remote
INTENT_URL=https://xxxx.trycloudflare.com
# INTENT_TOKEN = HEALTH_GEN_TOKEN par défaut
# optionnels : INTENT_TIMEOUT=8  INTENT_MIN_CONF=0.5
```
3. `docker compose up -d --build`, puis `GET /health` doit montrer `intent_backend: "remote"` et `intent_remote_error: null` (après une requête).
4. **Par défaut rien ne change** (`INTENT_BACKEND=local` = sklearn + règles). Si le serveur distant tombe (Colab coupé) : repli automatique sur sklearn/règles, sans erreur.

### Règles de sécurité du mode remote
- `app/safety/redflags.py` : drapeau rouge ⇒ `emergency` **avant** le modèle (le modèle ne peut pas l'écraser) ; faux positifs possibles, assumés.
- Si P(emergency) ≥ 0,35 mais pas première : emergency. Confiance < `INTENT_MIN_CONF` : on garde le label des règles.
- `symptoms_query` : sans médicament → générateur Atlas (si `USE_HEALTH_GENERATOR=true`) sinon message « consulte le médecin/pharmacien ».
- Le serveur d'intention n'écoute que sur 127.0.0.1 ; seul le proxy à jeton l'expose.

## 5) Vraies questions (le seul chiffre vraiment indépendant)
1. Collecter **30 à 100 vraies questions** (famille, amis, pharmacien, étudiants), telles qu'elles les écrivent (fautes, arabizi, mélange). Ne pas les reformuler.
2. Les étiqueter vous-même avec la politique P1–P8 (`docs/politique_labels_intent_fr.md`) dans `real_questions.csv` (colonnes `text,label`, modèle : `colab_v5/real_questions_template.csv`). Étiqueter **sans regarder** ce que le modèle prédit.
3. Vérifier : `python ml/check_real_questions.py real_questions.csv` (labels valides, doublons, fuite avec le dataset, drapeaux rouges mal étiquetés, répartition, intervalle de confiance).
4. Dans le notebook, uploader `real_questions.csv` à la cellule prévue : évalué sous `test_real`, jamais utilisé pour choisir le modèle.
5. Avec n = 50 et une acc. de 90 %, l'intervalle à 95 % est ≈ ± 8 points : ne pas sur-interpréter.

## 6) Critère d'intégration proposé
Garder `local` en production tant que XLM-R v5 ne bat pas sklearn sur test_gold **et** test_fresh **et** test_real (si fourni), et que le recall `emergency` (modèle + guard) reste ≥ 0,9 sur test_fresh. v4 battait déjà sklearn sur test_gold (0,903 vs 0,807) : le choix final vous appartient.
