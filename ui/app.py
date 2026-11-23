"""SmartDwa - واجهة Streamlit (RTL مع عزل مقاطع LTR: أسماء الأدوية الفرنسية والأرقام والأسعار)."""
import html
import os
import re

import httpx
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
st.set_page_config(page_title="SmartDwa", page_icon="💊", layout="centered")

# ------------------------------------------------------------------ CSS
st.markdown(
    """
<style>
/* لا نفرض rtl على الحاوية كلها؛ كل فقرة تحمل اتجاهها الصريح */
.sd-p   { margin: 0 0 .55rem 0; line-height: 1.9; unicode-bidi: isolate; white-space: pre-wrap; overflow-wrap: anywhere; }
.sd-p[dir="rtl"] { text-align: right; }
.sd-p[dir="ltr"] { text-align: left; }
.sd-p bdi        { unicode-bidi: isolate; }      /* عزل مقاطع LTR داخل الجملة العربية */
.sd-src  { font-size: .85rem; color: #5b6773; }
.sd-note { font-size: .78rem; color: #8a94a0; margin-top: .3rem; }
.sd-ps   { direction: ltr; text-align: left; unicode-bidi: isolate; font-size: .9rem; line-height: 1.6;
           background: rgba(127,127,127,.08); border-radius: 6px; padding: .5rem .7rem; margin-bottom: .6rem; white-space: pre-wrap; }
/* مربع الإدخال: الاتجاه يتبع أول حرف يكتبه المستخدم */
textarea[data-testid="stChatInputTextArea"] { unicode-bidi: plaintext; text-align: start; }
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ Bidi helpers
_TOK = r"\(*[A-Za-zÀ-ÿ0-9§][A-Za-zÀ-ÿ0-9§.,:;/%+\-'’°µ&]*\)*"
LTR_RUN = re.compile(rf"{_TOK}(?:[ \t]+{_TOK})*")
AR = re.compile(r"[؀-ۿ]")
LAT = re.compile(r"[A-Za-zÀ-ÿ]")


def base_dir(text: str) -> str:
    """اتجاه الفقرة: rtl إذا كانت الحروف العربية >= 25% من الحروف (لا نعتمد على أول حرف)."""
    a, l = len(AR.findall(text)), len(LAT.findall(text))
    return "rtl" if a and a >= 0.25 * (a + l) else "ltr"


def _isolate(m: re.Match) -> str:
    run = m.group(0)
    lead = trail = ""
    # علامات الترقيم الختامية تبقى خارج المقطع اللاتيني (تتبع اتجاه الجملة العربية)
    while run and run[-1] in ".,:;":
        trail = run[-1] + trail
        run = run[:-1]
    # أقواس غير متوازنة تبقى خارجاً حتى تُعكَس بشكل صحيح
    while run.endswith(")") and run.count(")") > run.count("("):
        trail = ")" + trail
        run = run[:-1]
    while run.startswith("(") and run.count("(") > run.count(")"):
        lead += "("
        run = run[1:]
    if not run:
        return lead + trail
    return f'{lead}<bdi dir="ltr">{html.escape(run)}</bdi>{trail}'


def bidi(text: str) -> str:
    """نص عادي -> HTML: فقرات بالاتجاه الصحيح + عزل كل مقطع لاتيني/أرقام داخل الجمل العربية."""
    out = []
    for para in re.split(r"\n+", text.strip()):
        if not para.strip():
            continue
        d = base_dir(para)
        # نهرب HTML أولاً ثم نعزل المقاطع اللاتينية (الهروب لا يمس الحروف اللاتينية والأرقام)
        esc = html.escape(para, quote=False)
        body = LTR_RUN.sub(_isolate, esc) if d == "rtl" else esc
        out.append(f'<div class="sd-p" dir="{d}">{body}</div>')
    return "".join(out)


def show_html(markup: str):
    (st.html if hasattr(st, "html") else (lambda m: st.markdown(m, unsafe_allow_html=True)))(markup)


def render_assistant(r: dict):
    show_html(bidi(r.get("answer", "")))
    if r.get("sources"):
        show_html(bidi("المصادر: " + " · ".join(x.replace(" (", " — ").replace(")", "") for x in r["sources"])).replace('class="sd-p"', 'class="sd-p sd-src"', 1))
    if r.get("disclaimer"):
        show_html(f'<div class="sd-p sd-note" dir="rtl">{html.escape(r["disclaimer"])}</div>')
    if r.get("passages"):
        with st.expander(f"📄 المقاطع من نشرة RCP ({len(r['passages'])})"):
            for ps in r["passages"]:
                head = html.escape(f"{ps['source']} · {ps.get('product', '')}")
                show_html(f'<div class="sd-ps"><b>{head}</b><br>{html.escape(ps["text"])}</div>')
    with st.expander("التفاصيل (للمطور)"):
        st.json({k: r.get(k) for k in ("route", "drugs", "interactions", "rag_used")})


# ------------------------------------------------------------------ Sidebar
with st.sidebar:
    st.subheader("حالة النظام")
    try:
        h = httpx.get(f"{BACKEND}/health", timeout=5).json()
        st.success("Backend شغال")
        st.json(h)
    except Exception as e:
        st.error(f"Backend ما جاوبش: {e}")
    st.caption("جرّب: «واش نقدر ناخد clarithromycin مع domperidone؟»")

# ------------------------------------------------------------------ Page
st.title("💊 SmartDwa — مساعد الصيدلي بالدارجة")
st.warning("أداة تعليمية: ما كنعطيش جرعات ولا تشخيص. سول الصيدلي أو الطبيب دائماً.")

if "msgs" not in st.session_state:
    st.session_state.msgs = []

for m in st.session_state.msgs:
    with st.chat_message(m["role"]):
        if m["role"] == "user":
            show_html(bidi(m["text"]) if base_dir(m["text"]) == "rtl" else
                      f'<div class="sd-p" dir="ltr">{html.escape(m["text"])}</div>')
        else:
            render_assistant(m["resp"])

if q := st.chat_input("كتب سؤالك هنا..."):
    st.session_state.msgs.append({"role": "user", "text": q})
    with st.chat_message("user"):
        show_html(bidi(q) if base_dir(q) == "rtl" else f'<div class="sd-p" dir="ltr">{html.escape(q)}</div>')
    try:
        r = httpx.post(f"{BACKEND}/chat", json={"message": q}, timeout=120).json()
    except Exception as e:
        r = {"answer": f"خطأ في الاتصال بالـ backend: {e}", "route": "error"}
    with st.chat_message("assistant"):
        render_assistant(r)
    st.session_state.msgs.append({"role": "assistant", "resp": r})
