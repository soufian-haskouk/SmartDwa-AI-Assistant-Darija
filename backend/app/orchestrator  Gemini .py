from . import config, guards, llm, rag
from .intent import IntentClassifier

DISCLAIMER = "هادشي أداة تعليمية؛ ماشي تشخيص ولا وصفة. سول الصيدلي أو الطبيب."

def _lvl_text(level):
    return {None: "كاين احتمال تداخل (الخطورة ما تحدداتش)", 0: "تداخل خفيف", 1: "تداخل خفيف", 2: "تداخل متوسط — احتاط",
            3: "تداخل خطير — ما تخلطهمش بلا استشارة", 4: "تداخل خطير جداً — ما تخلطهمش"}.get(level, "تداخل محتمل")

def _short_pres(p: str) -> str:
    return p.replace("BOITE DE ", "").replace("BOITE D'", "").replace("BOITE ", "").strip().lower()[:45]

def fmt_items(items, n=4) -> str:
    return "، ".join(f"{i['nom']} {i['dosage']} ({_short_pres(i['presentation'])}): {i['ppv_dh']:g} درهم" for i in items[:n])

class Orchestrator:
    def __init__(self, linker, store):
        self.linker, self.store = linker, store
        self.intent = IntentClassifier()

    def link(self, text):
        return self.linker.find_drugs(text)

    def chat(self, text: str) -> dict:
        res = dict(route="", answer="", drugs=[], interactions=[], presentations=[], passages=[], catalog=[], sources=[],
                   rag_used=False, disclaimer=DISCLAIMER, intent=None)
        if guards.is_emergency(text):
            res.update(route="emergency", answer=config.EMERGENCY_TEXT); return res

        hits = self.link(text)
        res["drugs"] = hits
        cat = self.store.catalog
        cm = cat.find(text) if cat else []
        it_ = self.intent.predict(text, has_drug=bool(hits or cm))
        intent = it_["label"]
        res["intent"] = dict(label=intent, confidence=round(it_["confidence"], 3), source=it_["source"], top=it_["top"])
        if intent == "emergency":                      # النموذج أو القواعد (الأولوية للـ recall)
            res.update(route="emergency", answer=config.EMERGENCY_TEXT); return res
        if intent == "dosage" or guards.asks_dose(text):
            res.update(route="refuse_dose",
                       answer="ما نقدرش نعطيك الجرعة. الجرعة كتختلف من شخص لآخر (السن، الوزن، المرض). سول الطبيب أو الصيدلي.")
            return res
        # أدوية خارج الـ20 مادة وجدناها في كتالوج AMMPS (مطابقة حرفية فقط تُنفَّذ تلقائياً)
        cat_out = [m for m in cm if m["exact"] and not cat.in_scope(m["rows"])]
        cat_fuzzy = [m for m in cm if not m["exact"]]

        oos = [h for h in hits if h["out_of_scope"]]
        unsure = [h for h in hits if not h["out_of_scope"] and (h["confidence"] == "low" or h["ambiguous"])]
        if unsure:
            h = unsure[0]
            res.update(route="confirm", answer=f"واش كتقصد «{self.store.display_name(h['substance_id'])}»؟ إلا كان هو، عاود كتب سؤالك بهاد السمية.")
            return res
        ok = [h for h in hits if not h["out_of_scope"]]
        if not ok:
            if cat_out:
                return self._price_only(res, cat, cat_out, text)
            if cat_fuzzy:
                m = cat_fuzzy[0]
                res.update(route="confirm", answer=f"واش كتقصد «{cat.display(m)}»؟ إلا كان هو، عاود كتب سؤالك بهاد السمية.")
                return res
            if oos:
                res.update(route="out_of_scope", answer="هاد الدوا ماشي من الأدوية اللي كنغطي دابا. سول الصيدلي."); return res
            if intent == "out_of_scope" and it_["source"] == "model":
                if config.USE_LLM and not guards.asks_dose(text):
                    gen = llm.rewrite_in_darija(
                        text,
                        "أجب عن سؤال المريض بالدارجة المغربية البسيطة وبشكل آمن وعام. لا تعطِ جرعات ولا تشخيصاً ولا وصف دواء، ولا تطلب صوراً أو معلومات شخصية، وانصح بسؤال الصيدلي أو الطبيب عند الحاجة.",
                    )
                    if gen and not guards.asks_dose(gen) and not guards.is_emergency(gen):
                        res.update(route="general_health", answer=gen)
                        return res
                res.update(
                    route="not_a_drug_question",
                    answer="سؤالك ماشي على الأدوية اللي كنغطي (الثمن، التداخلات، موانع الاستعمال). للأسئلة الطبية العامة سول الطبيب أو الصيدلي.",
                )
                return res
            res.update(route="clarify", answer="ما فهمتش أي دوا كتقصد. كتب سمية الدوا (بالحروف اللاتينية أحسن، بحال Doliprane أو Abilify).")
            return res

        ids = list(dict.fromkeys(h["substance_id"] for h in ok))
        names = [self.store.display_name(i) for i in ids]
        facts, parts = [], []

        if len(ids) >= 2 and intent in ("price", "alternative") and not res["interactions"]:
            for sid_, nm_ in zip(ids, names):
                pr_, lb_ = self._scope_prices(sid_, nm_, cm, text, ok, generic=(intent == "alternative"))
                if pr_ and pr_["items"]:
                    parts.append(f"{lb_}: {fmt_items(pr_['items'])}. (الثمن للعموم PPV)"); res["presentations"] += pr_["items"]
            facts += parts; res["sources"].append(f"AMMPS (PPV، استخراج {config.AMMPS_DATE})"); res["route"] = intent
        elif len(ids) >= 2:
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    it = self.store.interaction(ids[i], ids[j])
                    if it:
                        res["interactions"].append(it)
                        res["sources"] += [s.strip() for s in it["sources"].split(";")]
                        note = _lvl_text(it["level"]) + (" (حسب الجرعة)" if it["dose_dependent"] else "")
                        note += " — ⚠️ مستوى الخطورة اقتراح ما راجعوش صيدلي بعد"
                        parts.append(f"{names[i]} + {names[j]}: {note}.")
                        facts.append(f"{names[i]} + {names[j]}: {note}. المصدر: {it['sources']}")
            if not res["interactions"]:
                parts.append(f"ما لقيتش تداخل مسجل بين {' و '.join(names)} فقاعدتي، ولكن هادشي ما كيعنيش أنه ما كاينش. سول الصيدلي.")
            res["route"] = "interaction"
        elif intent == "side_effects":
            parts.append(f"{names[0]}: ما عنديش دابا معلومات على الأعراض الجانبية (كنقرا غير من §4.3 موانع الاستعمال و§4.5 التداخلات د RCP). سول الصيدلي أو شوف نشرة الدوا.")
            res["route"] = "side_effects_unavailable"
        elif intent == "contraindication":
            parts.append(f"موانع استعمال {names[0]} (مقاطع حرفية من نشرة RCP):")
            res["route"] = "contraindication"
        else:
            generic = intent == "alternative"
            pres, label = self._scope_prices(ids[0], names[0], cm, text, ok, generic=generic)
            res["presentations"] = pres["items"] if pres else []
            if generic and pres and pres["items"]:
                parts.append(f"بدائل بنفس المادة الفعالة ({names[0]}) من AMMPS، الأرخص أولاً: {fmt_items(pres['items'])}. ⚠️ نفس المادة الفعالة ماشي دائماً نفس الجرعة/الشكل؛ شاور الصيدلي قبل ما تبدّل.")
                facts.append(parts[-1]); res["sources"].append(f"AMMPS (PPV، استخراج {config.AMMPS_DATE})")
            elif pres and pres["items"]:
                parts.append(f"{label}: من الأنواع المتوفرة وأرخصها: {fmt_items(pres['items'])}. (الثمن للعموم PPV)")
                facts.append(parts[-1])
                res["sources"].append(f"AMMPS (PPV، استخراج {config.AMMPS_DATE})")
            elif pres and pres["n_total"]:
                parts.append(f"{label}: كاين فسجل AMMPS ولكن ماشي مسوَّق دابا ({pres['n_not_marketed']} مستحضر).")
            else:
                parts.append(f"لقيت {names[0]} ولكن ما عنديش أسعار متوفرة ليه.")
            res["route"] = "alternative" if generic else ("price" if intent == "price" else "drug_info")

        seen, parts_main, parts = set(), parts, []
        for m in cat_out:                       # دواء ثانٍ في السؤال خارج النطاق: نقول بصراحة أننا لا نتحقق منه
            nm = cat.display(m)
            if nm not in seen:
                seen.add(nm)
                parts.append(f"⚠️ «{nm}» خارج النطاق ديالي: ما نقدرش نتحقق من التداخل أو الموانع معاه، سول الصيدلي.")
        for h in oos:
            if h["span"] not in seen and not any(h["span"].lower() in x.lower() for x in seen):
                seen.add(h["span"]); parts.append(f"⚠️ «{h['span']}» خارج النطاق ديالي: ما نقدرش نتحقق منو، سول الصيدلي.")
        parts += parts_main                       # التحذير أولاً ثم المعلومة
        res["catalog"] = self._catalog_summary(cat, cat_out, text)

        chunks = [] if (intent in ("price", "alternative", "side_effects") and len(ids) == 1) else rag.retrieve(text, ids, intent=intent)
        if res["route"] == "contraindication" and not chunks:
            parts.append("ما لقيتش مقطع واضح فنشرة RCP لهاد السؤال. سول الصيدلي.")
        if chunks:
            res["rag_used"] = True
            res["passages"] = [dict(source=c["source"], product=c["product"], text=c["text"]) for c in chunks]
            facts += [c["text"] for c in chunks]
            res["sources"] += [c["source"] for c in chunks]

        template = " ".join(parts)
        if res["passages"]:
            template += " (شوف المقاطع الحرفية من نشرة RCP الفرنسية تحت.)"
        res["answer"] = llm.rewrite_in_darija(text, "\n".join(facts)) or template
        res["sources"] = list(dict.fromkeys(res["sources"]))
        return res

    # ------------------------------------------------------------------ الكتالوج
    def _scope_prices(self, sid, name, cm, text="", hits=(), generic=False):
        cat = self.store.catalog
        if cat is None:
            return None, name
        rows = cat.rows_for_substance(sid)
        label = name
        if generic:                            
            return cat.presentations(rows, dose_hint=text), label
        for h in hits:                         # الـ linker حدد أن ما كُتب علامة تجارية (حتى مع خطأ إملائي/كتابة عربية)
            if h["substance_id"] == sid and str(h.get("alias_type", "")).startswith("brand"):
                b = cat.brand_rows_for_span(sid, h["span"])
                if b:
                    return cat.presentations(b[1], dose_hint=text), f"{cat.df.nom[b[1][0]]} ({name})"
        for m in cm:                          
            if m["exact"] and m["kind"] == "brand":
                br = [i for i in m["rows"] if sid in cat.df.scope_ids[i]]
                if br: rows, label = br, f"{cat.display(m)} ({name})"; break
        return cat.presentations(rows, dose_hint=text), label

    def _catalog_summary(self, cat, ms, text=""):
        out = []
        for m in ms:
            p = cat.presentations(m["rows"], dose_hint=text)
            out.append(dict(name=cat.display(m), kind=m["kind"], n_total=p["n_total"], n_available=p["n_available"], items=p["items"]))
        return out

    def _price_only(self, res, cat, ms, text=""):
        parts, summ = [], self._catalog_summary(cat, ms, text)
        for s_ in summ:
            if s_["items"]:
                parts.append(f"«{s_['name']}» لقيتو فسجل AMMPS: {fmt_items(s_['items'])}. (الثمن للعموم PPV)")
            else:
                parts.append(f"«{s_['name']}» كاين فسجل AMMPS ولكن ماشي مسوَّق دابا ولا بلا ثمن.")
        parts.append("⚠️ هاد الدوا خارج النطاق ديالي: ما عنديش معلومات على التداخلات ولا الموانع، سول الصيدلي.")
        res.update(route="price_only", catalog=summ, presentations=summ[0]["items"],
                   sources=[f"AMMPS (PPV، استخراج {config.AMMPS_DATE})"], answer=" ".join(parts))
        return res