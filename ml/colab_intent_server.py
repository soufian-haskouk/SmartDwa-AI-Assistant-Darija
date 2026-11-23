"""Serveur d'intention XLM-R (127.0.0.1 uniquement ; exposé seulement via le proxy à jeton : POST /intent {"text": "..."} -> {"label","confidence","top":[[label,p],...]}).
Usage : python intent_server.py <dossier best_model> <port> <max_len>"""
import http.server, socketserver, json, sys, threading, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
path, port, max_len = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
dev = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(path)
m = AutoModelForSequenceClassification.from_pretrained(path, torch_dtype=torch.float32).to(dev).eval()
lock = threading.Lock()


class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path == "/ping": return self._send(200, {"ok": True, "device": dev})
        self._send(404, {})

    def do_POST(self):
        if self.path != "/intent": return self._send(404, {})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0 or n > 4000: return self._send(413, {"error": "bad size"})
            text = str(json.loads(self.rfile.read(n))["text"])[:1000]
            enc = {k: v.to(dev) for k, v in tok(text, return_tensors="pt", truncation=True, max_length=max_len).items()}
            with lock, torch.no_grad():
                pr = torch.softmax(m(**enc).logits[0].float(), -1).cpu()
            idx = pr.argsort(descending=True)[:3].tolist()
            top = [[m.config.id2label[i], round(float(pr[i]), 4)] for i in idx]
            self._send(200, {"label": top[0][0], "confidence": top[0][1], "top": top})
        except Exception as e:
            self._send(400, {"error": type(e).__name__})

    def log_message(self, *a): pass


class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True


print("intent server prêt sur", dev, flush=True)
S(("127.0.0.1", port), H).serve_forever()
