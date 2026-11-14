# تقرير مصنّف النية — SmartDwa

- التدريب: **15998** جملة (قوالب اصطناعية + 3600 سؤالاً طبياً عاماً من MedQA_MA كفئة out_of_scope)
- التحقق val: **3977** (قوالب محجوزة لم يرها النموذج) — اختيار النموذج يتم هنا فقط
- الاختبار gold: **176** جملة مكتوبة يدوياً (ملف `ml/gold_intent.psv`)، صفر تداخل مع التدريب/val. ⚠️ الوسوم وضعها الذكاء الاصطناعي (`label_ai`) وتحتاج مراجعة بشرية قبل الاعتماد الأكاديمي.

## 1) مقارنة النماذج (Macro-F1 / Accuracy)

| النموذج | val F1 | gold F1 | gold Acc | gold مع ضجيج إضافي F1 |
|---|---|---|---|---|
| Rules (expert) | 0.600 | 0.631 | 0.614 | 0.604 |
| LogReg | 0.513 | 0.763 | 0.756 | 0.749 |
| LinearSVC (calibrated) | 0.492 | 0.767 | 0.756 | 0.764 |
| MLP (1 hidden layer, 128) | 0.508 | 0.771 | 0.756 | 0.758 |
| System (model+threshold+rules fallback) | nan | 0.817 | 0.807 | nan |

> قراءة (مهمة): **val منخفض عمداً** لأنه يتكوّن من قوالب صياغة لم يرها النموذج (≈25 قالباً لكل فئة فقط) ⇒ يكشف أن النموذج تعلّم جزئياً صياغات القوالب. أما gold فمكتوب بيد واحدة (بأسلوب قريب من القوالب)، فرقمه **متفائل** ولا يُعتبر تقديراً للأداء مع مستخدمين حقيقيين. الحل الحقيقي: بيانات حقيقية أكثر تنوعاً + نموذج Transformer (انظر `ml/colab_finetune_intent.py`).

## 2) النموذج المعتمد (LogReg) على gold — تفصيل لكل فئة

```
                  precision    recall  f1-score   support

           price      0.818     0.900     0.857        20
     interaction      0.696     0.800     0.744        20
contraindication      0.909     0.500     0.645        20
          dosage      0.882     0.750     0.811        20
    side_effects      0.778     0.778     0.778        18
     alternative      0.923     0.706     0.800        17
       drug_info      0.824     0.778     0.800        18
       emergency      0.824     0.778     0.800        18
    out_of_scope      0.526     0.800     0.635        25

        accuracy                          0.756       176
       macro avg      0.798     0.754     0.763       176
    weighted avg      0.788     0.756     0.758       176

```

## 3) مصفوفة الالتباس (صفوف = الحقيقة، أعمدة = التنبؤ)

```
                  price  interaction  contraindication  dosage  side_effects  alternative  drug_info  emergency  out_of_scope
price                18            1                 0       0             0            0          0          0             1
interaction           0           16                 0       0             1            0          0          0             3
contraindication      0            5                10       0             0            0          0          0             5
dosage                2            1                 0      15             0            0          0          0             2
side_effects          0            0                 1       0            14            0          0          1             2
alternative           0            0                 0       0             0           12          2          1             2
drug_info             0            0                 0       0             1            1         14          0             2
emergency             0            0                 0       2             1            0          0         14             1
out_of_scope          2            0                 0       0             1            0          1          1            20
```

## 4) الثقة والعتبة

| العتبة | تغطية | دقة ضمن المغطّى |
|---|---|---|
| 0.3 | 0.99 | 0.759 |
| 0.45 | 0.94 | 0.794 |
| 0.55 | 0.87 | 0.830 |
| 0.65 | 0.81 | 0.874 |
| 0.8 | 0.74 | 0.885 |

- العتبة المعتمدة في الخدمة 0.55 (محافظة؛ تحت العتبة تُستعمل القواعد).
- Recall فئة الطوارئ على gold: النموذج وحده **0.78**، النظام الكامل (نموذج + قواعد guards) **0.89**.

## 5) أخطاء النموذج على gold

| الجملة | الحقيقة | التنبؤ | الثقة |
|---|---|---|---|
| كيفاش نعرف ثمن ديال دوا بلا ما نمشي للصيدلية | price | out_of_scope | 0.96 |
| is Smecta expensive? | price | interaction | 0.25 |
| واش الحليب كيمنع تأثير ديال Augmentin | interaction | out_of_scope | 0.67 |
| واش ندير الباراسيتامول والإيبوبروفين مجموعين | interaction | out_of_scope | 0.84 |
| واش هاد جوج دوايات كيتناقضو مع بعضهم | interaction | out_of_scope | 0.56 |
| chno kaysra ila khdit Daflon m3a l'aspirine | interaction | side_effects | 0.97 |
| Doliprane et grossesse | contraindication | interaction | 0.33 |
| ما كيمشيش مع الربو Voltarène؟ | contraindication | interaction | 0.58 |
| واش كاينين ناس ما خاصهمش ياخدو ديكلوفيناك | contraindication | out_of_scope | 0.93 |
| شكون ما يمكنش ياخد الأسبرين | contraindication | out_of_scope | 0.96 |
| ma3endi 7ata 7assasiya mn penicilline wach nakhod Clamoxyl | contraindication | interaction | 0.64 |
| Is Abilify safe for people with heart problems? | contraindication | interaction | 0.85 |
| من هما الحالات اللي ممنوع فيها Levothyrox | contraindication | out_of_scope | 0.53 |
| واش الدوا هادا خطير على الكلى؟ | contraindication | out_of_scope | 0.4 |
| Can pregnant women take loperamide? | contraindication | interaction | 0.59 |
| أنا عندي ضغط مرتفع واش نستعمل Sudafed | contraindication | out_of_scope | 0.97 |
| شحال ندير للطفل ديالي ديال الدوا ديال الحمى | dosage | out_of_scope | 0.39 |
| Posologie de Zithromax svp | dosage | price | 0.34 |
| كل شحال ساعة نعاود نشرب Efferalgan | dosage | price | 0.48 |
| ghadi nakhod 1000mg wach bzaf ? | dosage | interaction | 0.6 |
| كم يوما نكمل العلاج بالمضاد الحيوي | dosage | out_of_scope | 0.99 |
| شنو هي الأعراض الجانبية ديال Augmentin | side_effects | out_of_scope | 0.88 |
| is it normal to feel sleepy after taking Xanax | side_effects | emergency | 0.62 |
| Smecta provoque-t-il de la constipation | side_effects | contraindication | 0.53 |
| شنو الأعراض اللي خاصني نبلغ بها الطبيب ملي نستعمل الدوا | side_effects | out_of_scope | 0.98 |
| واش كاين دوا آخر بحال Spasfon وأرخص | alternative | out_of_scope | 0.51 |
| Levothyrox ما لقيتوش فالصيدلية شنو نبدلو بيه | alternative | out_of_scope | 0.67 |
| remplaçant de l'Efferalgan | alternative | emergency | 0.35 |
| another brand with same active ingredient as Doliprane | alternative | drug_info | 0.6 |
| واش Amoxil هو نفسو Clamoxyl | alternative | drug_info | 0.69 |
| principe actif du Daflon ? | drug_info | alternative | 0.81 |
| kifach kay5dem Abilify f jism | drug_info | out_of_scope | 0.31 |
| واش Ventoline كيتاخد بالفم ولا بالنفخ | drug_info | out_of_scope | 0.53 |
| chno howa l'aspegic | drug_info | side_effects | 0.35 |
| wldi bela3 bzaf dial les comprimés | emergency | dosage | 0.49 |
| عندي حكة بزاف وتنفخ لساني بعد الدوا | emergency | out_of_scope | 0.96 |
| surdosage de paracétamol que faire | emergency | dosage | 0.49 |
| rassi kaydour bzaf w ghadi nghma 3lia mn ba3d ma khdit l'ibuprofene | emergency | side_effects | 0.46 |
| ghadi nmchi l tbib wla pharmacie | out_of_scope | price | 0.97 |
| comment devenir pharmacien ? | out_of_scope | price | 0.42 |
| pourquoi j'ai mal au dos le matin | out_of_scope | emergency | 0.8 |
| how do vaccines work | out_of_scope | drug_info | 0.97 |
| j'ai mal à la tête depuis hier qu'est-ce que j'ai | out_of_scope | side_effects | 0.64 |

## 6) حدود صريحة
- بيانات التدريب اصطناعية في معظمها؛ لا تعكس بالضرورة كلام الصيادلة والزبائن الحقيقي. الحل: جمع أسئلة حقيقية (log التطبيق بعد موافقة) وإعادة التدريب.
- gold صغير (176) ⇒ هامش خطأ كبير (±5–7 نقاط)، ومكتوب بأسلوب كاتب واحد.
- فئة out_of_scope تعتمد على MedQA (أسئلة طبية عامة) + محادثة عادية؛ قد تخطئ في أسئلة صيدلانية غير مألوفة.
- baseline القواعد كُتب بعد الاطلاع على أسلوب gold (دون ضبط تكراري عليه) ⇒ قد يكون متفائلاً قليلاً لصالح القواعد.
- النموذج يصنّف النية فقط؛ الحقائق (أسعار/تداخلات/موانع) تأتي من AMMPS وRCP وليس منه.