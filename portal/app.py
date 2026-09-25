"""
Mural do Campus — portal (Flask).

Servido apenas em loopback, na porta 5000, com nome de host "localhost".
O modo (vulneravel/corrigido) vem de LAB_MODE (ver config.py).

Ponto único e real de emissão do cookie campus_session: a função
_emitir_sessao(), usada no login e no cadastro. É ali que HttpOnly, SameSite
e Secure são aplicados EXPLICITAMENTE, de acordo com o modo. Não presumimos
que uma configuração global do Flask altere um cookie que criamos à mão.
"""
import os
import re
import sqlite3
import sys

from flask import (
    Flask,
    abort,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.security import generate_password_hash

from . import auth, db
from .config import (
    COOKIE_NAME,
    PORTAL_HOST,
    PORTAL_PORT,
    COLLECTOR_ORIGIN,
    content_security_policy,
    cookie_flags,
    is_vulneravel,
    lab_mode,
)

app = Flask(__name__)

# Hosts aceitos pelo portal. localhost é o recomendado (host-only distinto
# do coletor em 127.0.0.1). 127.0.0.1:5000 é tolerado, mas nesse caso o
# portal e o coletor passam a compartilhar o host 127.0.0.1 — o README avisa.
HOSTS_ESPERADOS = {f"localhost:{PORTAL_PORT}", f"127.0.0.1:{PORTAL_PORT}"}


@app.before_request
def _validar_host_e_carregar_usuario():
    # Valida o Host esperado: não servimos para nomes/IPs inesperados.
    if request.host not in HOSTS_ESPERADOS:
        abort(400, "Host não esperado para o laboratório (use http://localhost:5000).")

    # Carrega o usuário atual a partir do cookie (sessão opaca).
    token = request.cookies.get(COOKIE_NAME)
    conn = db.get_conn()
    g.conn = conn
    g.usuario = auth.usuario_da_sessao(conn, token)


@app.teardown_request
def _fechar_conn(exc):
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()


@app.after_request
def _cabecalhos_seguranca(resp):
    # CSP só existe no modo corrigido (complementa o escape, não o substitui).
    csp = content_security_policy()
    if csp:
        resp.headers["Content-Security-Policy"] = csp
    # Um cabeçalho útil e barato nos dois modos:
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.context_processor
def _injeta_contexto():
    # Disponível em todos os templates.
    return {
        "usuario": g.get("usuario"),
        "lab_mode": lab_mode(),
        "vulneravel": is_vulneravel(),
        "collector_origin": COLLECTOR_ORIGIN,
    }


def _emitir_sessao(resp, usuario_id):
    """
    PONTO REAL DE EMISSÃO do cookie campus_session.
    Os atributos vêm de config.cookie_flags() e são aplicados aqui, um a um.
    No modo vulnerável, httponly=False (falha intencional). No corrigido,
    httponly=True. Nada é implícito.
    """
    token = auth.criar_sessao(g.conn, usuario_id)
    flags = cookie_flags()
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=flags["httponly"],
        samesite=flags["samesite"],
        secure=flags["secure"],
        path="/",
        # sem "domain": cookie host-only (vale só para o host que emitiu).
    )
    return resp


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------

@app.route("/")
def index():
    if g.usuario:
        return redirect(url_for("mural"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        row = auth.verificar_credenciais(g.conn, usuario, senha)
        if row is None:
            erro = "Usuário ou senha inválidos."
        else:
            resp = redirect(url_for("mural"))
            return _emitir_sessao(resp, row["id"])
    return render_template("login.html", erro=erro)


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    erro = None
    dados = {}
    if request.method == "POST":
        campos = ("usuario", "nome", "matricula", "curso", "recado_privado")
        dados = {campo: request.form.get(campo, "").strip() for campo in campos}
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", dados["usuario"]):
            erro = "Usuário: use de 3 a 32 letras, números ou _ (sem espaços)."
        elif not 2 <= len(dados["nome"]) <= 80:
            erro = "Informe um nome com 2 a 80 caracteres."
        elif not 1 <= len(dados["matricula"]) <= 30:
            erro = "Informe uma matrícula com até 30 caracteres."
        elif not 2 <= len(dados["curso"]) <= 80:
            erro = "Informe um curso com 2 a 80 caracteres."
        elif len(dados["recado_privado"]) > 500:
            erro = "O recado privado pode ter até 500 caracteres."
        elif not 6 <= len(senha) <= 128:
            erro = "A senha deve ter de 6 a 128 caracteres."
        elif senha != confirmar_senha:
            erro = "As senhas não conferem."
        else:
            try:
                usuario_id = db.criar_usuario(
                    g.conn,
                    dados["usuario"],
                    generate_password_hash(senha),
                    dados["nome"],
                    dados["matricula"],
                    dados["curso"],
                    dados["recado_privado"],
                )
            except sqlite3.IntegrityError:
                erro = "Este nome de usuário já está em uso."
            else:
                return _emitir_sessao(redirect(url_for("mural")), usuario_id)

    return render_template("cadastro.html", erro=erro, dados=dados)


@app.route("/logout", methods=["POST"])
def logout():
    # Revoga a sessão no servidor e limpa o cookie.
    auth.revogar_sessao(g.conn, request.cookies.get(COOKIE_NAME))
    resp = redirect(url_for("login"))
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@app.route("/mural", methods=["GET", "POST"])
def mural():
    if not g.usuario:
        return redirect(url_for("login"))
    erro = None
    dados = {"titulo": "", "corpo": ""}
    if request.method == "POST":
        dados = {
            "titulo": request.form.get("titulo", "").strip(),
            "corpo": request.form.get("corpo", "").strip(),
        }
        if not 3 <= len(dados["titulo"]) <= 120:
            erro = "O título deve ter de 3 a 120 caracteres."
        elif not 1 <= len(dados["corpo"]) <= 2000:
            erro = "A descrição deve ter de 1 a 2000 caracteres."
        else:
            from datetime import datetime, timezone

            criado_em = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            pub_id = db.criar_publicacao(
                g.conn,
                dados["titulo"],
                dados["corpo"],
                g.usuario["usuario"],
                criado_em,
            )
            return redirect(url_for("publicacao", pub_id=pub_id))
    pubs = db.listar_publicacoes(g.conn)
    return render_template("mural.html", publicacoes=pubs, erro=erro, dados=dados)


@app.route("/publicacao/<int:pub_id>", methods=["GET", "POST"])
def publicacao(pub_id):
    if not g.usuario:
        return redirect(url_for("login"))
    pub = db.get_publicacao(g.conn, pub_id)
    if pub is None:
        abort(404)
    if request.method == "POST":
        conteudo = request.form.get("conteudo", "").strip()
        if conteudo:
            from datetime import datetime, timezone

            criado_em = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            # Grava o texto ORIGINAL, sem sanitizar (parametrizado).
            db.inserir_comentario(
                g.conn, pub_id, g.usuario["usuario"], conteudo, criado_em
            )
        return redirect(url_for("publicacao", pub_id=pub_id))
    comentarios = db.listar_comentarios(g.conn, pub_id)
    return render_template("publicacao.html", pub=pub, comentarios=comentarios)


@app.route("/minha-conta")
def minha_conta():
    # Área privada: exige sessão válida. Mostra o recado privado fictício.
    if not g.usuario:
        return redirect(url_for("login"))
    return render_template("conta.html")


# --------------------------------------------------------------------------
# Inicialização com validação de loopback
# --------------------------------------------------------------------------

def _garantir_banco():
    conn = db.get_conn()
    db.init_schema(conn)
    n = conn.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    conn.close()
    if not n:
        from .seed import seed

        seed(force=False)


def main():
    # Vinculação SOMENTE ao loopback. Nunca 0.0.0.0.
    bind_host = "127.0.0.1"
    if os.environ.get("PORTAL_BIND", bind_host) not in ("127.0.0.1", "localhost"):
        print("Recusando bind fora do loopback.", file=sys.stderr)
        sys.exit(1)

    _garantir_banco()
    print(f"[portal] modo de laboratório: {lab_mode()}")
    print(f"[portal] abra no navegador: http://{PORTAL_HOST}:{PORTAL_PORT}")

    ssl_context = None
    if os.environ.get("PORTAL_HTTPS", "0") == "1":
        # Perfil HTTPS local opcional (para verificar o atributo Secure).
        # Usa certificado self-signed temporário; o navegador vai avisar.
        ssl_context = "adhoc"
        print("[portal] HTTPS local ligado (certificado self-signed).")

    # debug=False: NÃO ativamos o depurador web interativo.
    app.run(host=bind_host, port=PORTAL_PORT, debug=False, ssl_context=ssl_context)


if __name__ == "__main__":
    main()
