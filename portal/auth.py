"""
Autenticação e sessão OPACA do portal.

Modelo de sessão (igual nos dois modos — não é isto que a falha do XSS explora):
- No login válido ou no cadastro, geramos um token aleatório imprevisível
  (secrets.token_urlsafe).
- Esse token vai para o cookie campus_session (host-only, sem Domain).
- No servidor, guardamos apenas o HASH sha-256 do token na tabela sessoes,
  associado ao usuário, com data de expiração. O token em claro nunca é gravado.
- Rotas privadas validam o cookie: recalculam o hash, procuram a sessão,
  conferem que não está revogada e que não expirou. É o cookie que prova
  posse do token — não um nome de usuário ou id vindo de formulário.
- logout revoga a sessão no servidor. reset invalida todas as sessões.

Consequência importante para a demonstração C (reutilização):
- Ler a tabela sessoes no DBeaver NÃO revela o token (só o hash), então o
  banco não é atalho para roubar a sessão. Quem tem o token (via XSS) e o
  coloca no cookie campus_session no host do portal passa a ser reconhecido
  como a vítima — porque o hash bate com uma sessão válida.
- NÃO existe rota de "login por id" nem de "importar sessão". A única porta
  de entrada é possuir um token que corresponde a uma sessão realmente válida.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash

from . import db
from .config import SESSION_TTL_HOURS


def _agora():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def hash_token(token: str) -> str:
    """sha-256 do token. É isto — e só isto — que fica no banco."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verificar_credenciais(conn, usuario: str, senha: str):
    """Retorna a linha do usuário se a senha conferir, senão None."""
    row = db.get_usuario_por_nome(conn, usuario)
    if row is None:
        return None
    if not check_password_hash(row["senha_hash"], senha):
        return None
    return row


def criar_sessao(conn, usuario_id: int) -> str:
    """Cria uma sessão e devolve o TOKEN EM CLARO (vai só para o cookie)."""
    token = secrets.token_urlsafe(32)          # imprevisível
    token_hash = hash_token(token)             # só o hash é persistido
    agora = _agora()
    expira = agora + timedelta(hours=SESSION_TTL_HOURS)
    conn.execute(
        "INSERT INTO sessoes (token_hash, usuario_id, criado_em, expira_em, revogada) "
        "VALUES (?, ?, ?, ?, 0)",
        (token_hash, usuario_id, _iso(agora), _iso(expira)),
    )
    conn.commit()
    return token


def usuario_da_sessao(conn, token: str | None):
    """
    Valida o token do cookie e retorna a linha do usuário, ou None.
    Confere: existe? não revogada? não expirada?
    """
    if not token:
        return None
    row = conn.execute(
        "SELECT * FROM sessoes WHERE token_hash = ?",
        (hash_token(token),),
    ).fetchone()
    if row is None or row["revogada"]:
        return None
    try:
        expira = datetime.strptime(row["expira_em"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    if _agora() > expira:
        return None
    return db.get_usuario_por_id(conn, row["usuario_id"])


def revogar_sessao(conn, token: str | None) -> None:
    """logout: revoga a sessão correspondente ao token (server-side)."""
    if not token:
        return
    conn.execute(
        "UPDATE sessoes SET revogada = 1 WHERE token_hash = ?",
        (hash_token(token),),
    )
    conn.commit()


def revogar_todas(conn) -> None:
    """Usado pelo reset: invalida todas as sessões antigas."""
    conn.execute("UPDATE sessoes SET revogada = 1")
    conn.commit()
