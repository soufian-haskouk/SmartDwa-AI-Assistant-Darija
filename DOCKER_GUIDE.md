# دليل Docker لأول مرة (Windows)

## 0) قبل البدء
- Docker Desktop مثبّت وشغّال (أيقونة الحوت في الشريط، حالتها «Running»).
- Docker Desktop يحتاج WSL2 (يعرضه عليك المُثبّت). وقد تحتاج تفعيل Virtualization من BIOS إن ظهر خطأ بهذا المعنى.

## 1) تحديد ذاكرة Docker (جهازك 7 GB)
أنشئ الملف `C:\Users\<اسمك>\.wslconfig` بهذا المحتوى:
```
[wsl2]
memory=3GB
processors=2
```
ثم في PowerShell: `wsl --shutdown` وأعد تشغيل Docker Desktop.

## 2) تجربة أن Docker يعمل
```
docker --version
docker run hello-world
```
إن ظهرت رسالة «Hello from Docker!» فكل شيء سليم.

## 3) تشغيل المشروع
فك ضغط `smartdwa.zip` (يُفضَّل مسار قصير مثل `C:\smartdwa`، وليس داخل OneDrive)، ثم في PowerShell داخل المجلد:
```
docker compose up --build
```
- أول مرة تستغرق عدة دقائق (تنزيل صورة Python والمكتبات). المرات التالية سريعة.
- انتظر ظهور سطر من نوع `Uvicorn running on http://0.0.0.0:8000` ثم افتح: **http://localhost:8501**
- وثائق الـ API: http://localhost:8000/docs  — حالة النظام: http://localhost:8000/health
- للإيقاف: `Ctrl+C`، ثم `docker compose down`.

## 4) أوامر مفيدة
| الغرض | الأمر |
|---|---|
| تشغيل في الخلفية | `docker compose up -d` |
| عرض السجلات | `docker compose logs -f backend` |
| إعادة البناء بعد تغيير الكود | `docker compose up --build` |
| تشغيل الاختبارات | `docker compose run --rm tests` |
| تحديث AMMPS بعد استبدال `data/raw/ammps_medicaments.csv` | `docker compose run --rm prepare` ثم `curl -X POST http://localhost:8000/admin/reload` |
| إعادة استخراج RCP | `docker compose run --rm rcp-extract` ثم `docker compose run --rm rag-index` |
| إعادة توليد الأسماء العربية | `docker compose run --rm arabic-aliases` |
| قياس الذاكرة | `docker stats` |

## 5) مشاكل شائعة
- **`error during connect ... docker daemon`**: Docker Desktop غير مشغّل؛ شغّله وانتظر حتى يصبح Running.
- **`port is already allocated` (8000 أو 8501)**: برنامج آخر يستعمل المنفذ؛ أغلقه أو غيّر الرقم في `docker-compose.yml` (مثلاً `"8010:8000"`).
- **الحاوية تتوقف بـ `exited with code 137`**: نفاد الذاكرة؛ ارفع `mem_limit` للـ backend في الملف، أو ارفع `memory` في `.wslconfig`.
- **الواجهة تقول Backend ما جاوبش**: انتظر نصف دقيقة (الـ backend يفهرس البيانات عند الإقلاع)، وتحقق من `docker compose logs backend`.
- **WSL لم يُثبَّت**: في PowerShell كمسؤول: `wsl --install` ثم أعد تشغيل الجهاز.

## 6) اختياري: LLM محلي
Ollama يعمل على Windows مباشرة (خارج Docker). بعد تثبيته ونموذجك: `set USE_LLM=true` ثم `docker compose up`. الـ backend يتصل به عبر `host.docker.internal:11434`.
