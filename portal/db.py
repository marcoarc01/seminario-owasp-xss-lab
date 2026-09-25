"""
Acesso ao banco SQLite do portal.

Regras deste módulo:
- Caminho fixo e documentado: <projeto>/instance/mural.db
- TODAS as consultas usam placeholders "?" (parametrizadas). Nunca montamos
  SQL concatenando valores vindos do usuário. Isso previne SQL injection —
  que é um problema diferente do XSS deste laboratório.
- Guardamos o texto ORIGINAL dos comentários, inclusive scripts, sem alterar.
"""
import os
import sqlite3

# instance/mural.db ao lado da pasta portal/
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
DB_PATH = os.path.join(_PROJECT_ROOT, "instance", "mural.db")
SCHEMA_PATH = os.path.join(_HERE, "schema.sql")


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()


# ----------------------- usuários -----------------------

def get_usuario_por_nome(conn, usuario):
    return conn.execute(
        "SELECT * FROM usuarios WHERE usuario = ?", (usuario,)
    ).fetchone()


def get_usuario_por_id(conn, usuario_id):
    return conn.execute(
        "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()


def criar_usuario(conn, usuario, senha_hash, nome, matricula, curso, recado_privado):
    cursor = conn.execute(
        "INSERT INTO usuarios (usuario, senha_hash, nome, matricula, curso, recado_privado) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (usuario, senha_hash, nome, matricula, curso, recado_privado),
    )
    conn.commit()
    return cursor.lastrowid


# ----------------------- publicações --------------------

def listar_publicacoes(conn):
    return conn.execute(
        "SELECT * FROM publicacoes ORDER BY id ASC"
    ).fetchall()


def criar_publicacao(conn, titulo, corpo, autor, criado_em):
    cursor = conn.execute(
        "INSERT INTO publicacoes (titulo, corpo, autor, criado_em) VALUES (?, ?, ?, ?)",
        (titulo, corpo, autor, criado_em),
    )
    conn.commit()
    return cursor.lastrowid


def get_publicacao(conn, pub_id):
    return conn.execute(
        "SELECT * FROM publicacoes WHERE id = ?", (pub_id,)
    ).fetchone()


# ----------------------- comentários --------------------

def listar_comentarios(conn, pub_id):
    return conn.execute(
        "SELECT * FROM comentarios WHERE publicacao_id = ? ORDER BY id ASC",
        (pub_id,),
    ).fetchall()


def inserir_comentario(conn, pub_id, autor, conteudo, criado_em):
    # Parametrizado. "conteudo" é gravado EXATAMENTE como recebido — inclusive
    # se contiver <script>. A vulnerabilidade está na renderização, não aqui.
    conn.execute(
        "INSERT INTO comentarios (publicacao_id, autor, conteudo, criado_em) "
        "VALUES (?, ?, ?, ?)",
        (pub_id, autor, conteudo, criado_em),
    )
    conn.commit()
