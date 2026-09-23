"""
Verificação de navegador REAL (Chromium via Playwright) do laboratório.

Cobre os critérios de aceite:
  A. Stored XSS: alert(1) dispara e persiste ao recarregar.
  B. Captura: o payload real (no navegador) envia SÓ campus_session ao coletor;
     o token recebido pelo coletor é igual ao cookie real da vítima.
  C. Reutilização: definir campus_session no host do PORTAL dá acesso à conta
     e ao recado privado da vítima. Sem senha, sem backdoor.
  - Coletor não registra captura só por ser visitado (sem payload).
  - Token inválido e token revogado são negados.
  - Isolamento de host: cookie do portal é host-only (localhost), não vai
    automaticamente ao coletor (127.0.0.1).
  - Escape corrigido: mesmos comentários, sem alerta e sem nova captura.
  - HttpOnly isolado: cookie some de document.cookie no modo corrigido.
  - CSP isolada: com |safe ainda presente mas CSP ativa, o <script> inline é
    bloqueado (violação no console), sem confundir com a correção pelo escape.

Este script sobe e derruba o portal em diferentes modos/versões de template
por conta própria, e sobe um coletor uma única vez para contar capturas.

Rodar:  python -m tests.verificacao_navegador   (a partir da raiz do projeto)
"""
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTAL_URL = "http://localhost:5000"
PORTAL_MINHA = PORTAL_URL + "/minha-conta"
COLLECTOR_URL = "http://127.0.0.1:9000"
TPL_ATIVO = os.path.join(RAIZ, "portal", "templates", "publicacao.html")
TPL_VULN = os.path.join(RAIZ, "portal", "templates", "_publicacao_vuln.bak")
TPL_SEGURO = os.path.join(RAIZ, "patches", "secure", "publicacao.html")

resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, ok, detalhe))
    marca = "PASS" if ok else "FALHA"
    print(f"[{marca}] {nome}" + (f" — {detalhe}" if detalhe else ""), flush=True)


def porta_livre(host, porta):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, porta)) != 0


def espera_ate(url, timeout=15):
    fim = time.time() + timeout
    while time.time() < fim:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def inicia_portal(mode, template):
    """(Re)inicia o portal no modo e template pedidos. Retorna o processo."""
    shutil.copyfile(template, TPL_ATIVO)
    env = dict(os.environ, LAB_MODE=mode)
    p = subprocess.Popen(
        [sys.executable, "run_portal.py"],
        cwd=RAIZ, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if not espera_ate(PORTAL_URL + "/login"):
        raise RuntimeError("portal não subiu")
    return p


def para(p):
    if p and p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        try:
            p.wait(timeout=5)
        except Exception:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)


def coletor_capturas():
    """Lê a página do coletor e extrai (contagem, [tokens])."""
    html = urllib.request.urlopen(COLLECTOR_URL, timeout=3).read().decode()
    m = re.search(r"Capturas reais:\s*<strong>(\d+)</strong>", html)
    n = int(m.group(1)) if m else -1
    tokens = re.findall(r"<code>([A-Za-z0-9_\-]+)</code>", html)
    return n, tokens


def fecha_modal(page):
    """No modo vulnerável, o aviso repetitivo cobre a página. Fecha se estiver visível."""
    try:
        botao = page.locator("#modal-ok")
        if botao.count() and page.locator("#modal-aviso").is_visible():
            botao.click()
            page.wait_for_selector("#modal-aviso", state="hidden", timeout=2000)
    except Exception:
        pass


def login(page, usuario, senha):
    page.goto(PORTAL_URL + "/login")
    page.fill("#usuario", usuario)
    page.fill("#senha", senha)
    page.click(".formulario button[type=submit]")
    page.wait_for_load_state("networkidle")


def publica_comentario(page, pub_id, texto):
    page.goto(f"{PORTAL_URL}/publicacao/{pub_id}")
    fecha_modal(page)
    page.fill("#conteudo", texto)
    page.click(".formulario-comentario button[type=submit]")
    page.wait_for_load_state("networkidle")


def main():
    # Pré-condições de porta.
    if not porta_livre("127.0.0.1", 5000) or not porta_livre("127.0.0.1", 9000):
        print("Portas 5000/9000 ocupadas — encerre processos antigos primeiro.")
        sys.exit(2)

    # Backup do template vulnerável ativo (para restaurar no fim).
    shutil.copyfile(TPL_ATIVO, TPL_VULN)

    # Banco limpo.
    subprocess.run([sys.executable, "reset.py"], cwd=RAIZ, check=True,
                   stdout=subprocess.DEVNULL)

    # Coletor (uma vez).
    coletor = subprocess.Popen(
        [sys.executable, "run_collector.py"], cwd=RAIZ,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    espera_ate(COLLECTOR_URL + "/health")

    portal = None
    try:
        with sync_playwright() as pw:
            navegador = pw.chromium.launch()

            # ============================================================
            # FASE 1 — modo vulnerável, template vulnerável (|safe)
            # ============================================================
            portal = inicia_portal("vulneravel", TPL_VULN)

            # ---- A) Stored XSS: alert dispara e persiste --------------
            ctx_vitima = navegador.new_context()
            page = ctx_vitima.new_page()
            alertas = {"n": 0, "msg": None}
            page.on("dialog", lambda d: (alertas.__setitem__("n", alertas["n"] + 1),
                                          alertas.__setitem__("msg", d.message),
                                          d.dismiss()))
            login(page, "aluno", "aluno123")
            # publicação 1 recebe o alerta (separada da captura)
            publica_comentario(page, 1, "<script>alert(1)</script>")
            checa("A: alert(1) dispara ao renderizar o comentário",
                  alertas["n"] >= 1, f"mensagem={alertas['msg']!r}")
            # persistência: recarrega
            n_antes = alertas["n"]
            page.reload()
            page.wait_for_load_state("networkidle")
            checa("A: alerta persiste após recarregar (dado no banco)",
                  alertas["n"] > n_antes)

            # token real da vítima (cookie) — usado para conferir a captura
            cookies = ctx_vitima.cookies()
            camp = [c for c in cookies if c["name"] == "campus_session"]
            token_vitima = camp[0]["value"] if camp else None
            checa("Isolamento: cookie campus_session é host-only (domínio localhost)",
                  bool(camp) and camp[0]["domain"] in ("localhost", ".localhost"),
                  f"domain={camp[0]['domain'] if camp else None}")

            # ---- coletor não captura só por ser visitado --------------
            n0, _ = coletor_capturas()
            pv = ctx_vitima.new_page()
            pv.goto(COLLECTOR_URL)          # visita a página do atacante
            pv.wait_for_load_state("networkidle")
            pv.close()
            n1, _ = coletor_capturas()
            checa("Coletor não registra captura só por visita (sem payload)",
                  n1 == n0, f"antes={n0} depois={n1}")

            # ---- B) Captura real via payload no navegador -------------
            with open(os.path.join(RAIZ, "payloads", "2_captura_sessao.txt")) as fh:
                payload = fh.read()
            # publicação 2 recebe o payload de captura (separada do alerta).
            # Ao publicar, o redirect já re-renderiza a publicação 2 e executa
            # o payload uma vez (é assim que o XSS persistente atinge quem abre).
            publica_comentario(page, 2, payload)
            time.sleep(1.0)
            n2, tokens = coletor_capturas()
            checa("B: coletor registra nova captura do payload real (1 render = 1 captura)",
                  n2 == n1 + 1, f"antes={n1} depois={n2}")
            checa("B: token capturado == cookie real da vítima",
                  token_vitima in tokens,
                  f"token_vitima={str(token_vitima)[:12]}...")

            # ---- C) Reutilização da sessão ----------------------------
            ctx_atk = navegador.new_context()
            pa = ctx_atk.new_page()
            pa.goto(PORTAL_MINHA)          # sem sessão -> vai para login
            pa.wait_for_load_state("networkidle")
            checa("C: atacante sem sessão é mandado ao login",
                  "/login" in pa.url or pa.locator("#usuario").count() > 0)
            # aplica o token recebido no host do PORTAL (localhost)
            ctx_atk.add_cookies([{
                "name": "campus_session", "value": token_vitima,
                "domain": "localhost", "path": "/",
            }])
            pa.goto(PORTAL_MINHA)
            pa.wait_for_load_state("networkidle")
            corpo = pa.content()
            checa("C: atacante vê identidade da vítima (nome)",
                  "Ana Vitima da Silva" in corpo)
            checa("C: atacante vê o recado privado da vítima",
                  "reservei a sala 204" in corpo)

            # ---- token inválido e token revogado ----------------------
            ctx_inv = navegador.new_context()
            ctx_inv.add_cookies([{
                "name": "campus_session", "value": "token-invalido-xyz",
                "domain": "localhost", "path": "/",
            }])
            pi = ctx_inv.new_page()
            pi.goto(PORTAL_MINHA)
            pi.wait_for_load_state("networkidle")
            checa("Token inválido é negado (vai ao login)",
                  "#usuario" in pi.content() or "/login" in pi.url)
            ctx_inv.close()

            # revogação: cria sessão nova, faz logout, tenta reutilizar
            ctx_rev = navegador.new_context()
            pr = ctx_rev.new_page()
            login(pr, "atacante", "atacante123")
            tok_rev = [c["value"] for c in ctx_rev.cookies()
                       if c["name"] == "campus_session"][0]
            pr.goto(PORTAL_URL + "/mural")
            fecha_modal(pr)
            pr.click("form[action$='/logout'] button")   # logout revoga no servidor
            pr.wait_for_load_state("networkidle")
            ctx_rev2 = navegador.new_context()
            ctx_rev2.add_cookies([{"name": "campus_session", "value": tok_rev,
                                   "domain": "localhost", "path": "/"}])
            pr2 = ctx_rev2.new_page()
            pr2.goto(PORTAL_MINHA)
            pr2.wait_for_load_state("networkidle")
            checa("Token revogado (após logout) é negado",
                  "#usuario" in pr2.content() or "/login" in pr2.url)
            ctx_rev.close(); ctx_rev2.close()
            ctx_vitima.close(); ctx_atk.close()
            para(portal); portal = None

            # ============================================================
            # FASE 2 — correção do escape (template seguro), modo vulnerável
            #          para ISOLAR o efeito do escape
            # ============================================================
            n_pre_fix, _ = coletor_capturas()
            portal = inicia_portal("vulneravel", TPL_SEGURO)
            ctx2 = navegador.new_context()
            p2 = ctx2.new_page()
            al2 = {"n": 0}
            p2.on("dialog", lambda d: (al2.__setitem__("n", al2["n"] + 1), d.dismiss()))
            login(p2, "aluno", "aluno123")
            p2.goto(f"{PORTAL_URL}/publicacao/1")   # mesma publicação do alerta
            p2.wait_for_load_state("networkidle")
            time.sleep(0.5)
            checa("Escape: comentário antigo NÃO dispara alerta", al2["n"] == 0)
            checa("Escape: comentário aparece como TEXTO (escapado)",
                  "&lt;script&gt;alert(1)&lt;/script&gt;" in p2.content()
                  or "<script>alert(1)</script>" in p2.inner_text("body"))
            # comentário normal continua visível
            p2.goto(f"{PORTAL_URL}/publicacao/2")
            p2.wait_for_load_state("networkidle")
            time.sleep(0.8)
            n_pos_fix, _ = coletor_capturas()
            checa("Escape: nenhuma NOVA captura com o template corrigido",
                  n_pos_fix == n_pre_fix, f"antes={n_pre_fix} depois={n_pos_fix}")
            ctx2.close()
            para(portal); portal = None

            # ============================================================
            # FASE 3 — HttpOnly isolado (modo corrigido)
            # ============================================================
            portal = inicia_portal("corrigido", TPL_SEGURO)
            ctx3 = navegador.new_context()
            p3 = ctx3.new_page()
            login(p3, "aluno", "aluno123")
            p3.goto(PORTAL_URL + "/mural")
            dc = p3.evaluate("document.cookie")
            checa("HttpOnly: campus_session NÃO aparece em document.cookie",
                  "campus_session" not in dc, f"document.cookie={dc!r}")
            ctx3.close()
            para(portal); portal = None

            # ============================================================
            # FASE 4 — CSP isolada: modo corrigido MAS template vulnerável
            #          (|safe) -> o <script> inline é bloqueado pela CSP
            # ============================================================
            portal = inicia_portal("corrigido", TPL_VULN)
            ctx4 = navegador.new_context()
            p4 = ctx4.new_page()
            csp_msgs = []
            al4 = {"n": 0}
            p4.on("dialog", lambda d: (al4.__setitem__("n", al4["n"] + 1), d.dismiss()))
            p4.on("console", lambda m: csp_msgs.append(m.text))
            login(p4, "aluno", "aluno123")
            p4.goto(f"{PORTAL_URL}/publicacao/1")   # tem <script>alert(1)</script> cru
            p4.wait_for_load_state("networkidle")
            time.sleep(0.6)
            # cabeçalho CSP presente
            resp = urllib.request.urlopen(PORTAL_URL + "/login")
            tem_csp_header = "Content-Security-Policy" in resp.headers
            checa("CSP: cabeçalho Content-Security-Policy presente", tem_csp_header)
            checa("CSP: <script> inline injetado NÃO executa (sem alerta)",
                  al4["n"] == 0)
            bloqueio = any(("Content Security Policy" in m) or ("Refused to execute" in m)
                           or ("script-src" in m) for m in csp_msgs)
            checa("CSP: violação registrada no console do navegador",
                  bloqueio, f"msgs={[m[:60] for m in csp_msgs][:3]}")
            ctx4.close()
            para(portal); portal = None

            navegador.close()
    finally:
        para(portal)
        if coletor.poll() is None:
            os.killpg(os.getpgid(coletor.pid), signal.SIGTERM)
        # restaura o template vulnerável ativo e limpa backup
        if os.path.exists(TPL_VULN):
            shutil.copyfile(TPL_VULN, TPL_ATIVO)
            os.remove(TPL_VULN)

    total = len(resultados)
    ok = sum(1 for _, b, _ in resultados if b)
    print("\n==================== RESUMO ====================")
    print(f"{ok}/{total} verificações passaram.")
    for nome, b, det in resultados:
        if not b:
            print(f"  FALHA: {nome} — {det}")
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
