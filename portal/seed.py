"""
Semente de dados fictícios do laboratório.

Cria (ou recria) o banco instance/mural.db com duas contas fictícias de
demonstração. O mural começa vazio: as publicações e os comentários são
criados interativamente durante a apresentação.

Todas as credenciais são de demonstração e estão no README. As senhas são
gravadas apenas como hash (werkzeug). Nada aqui é real.

Uso:
    python -m portal.seed          # cria o banco se não existir
    python -m portal.seed --force  # apaga e recria (também via reset.py)
"""
import sys
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash

from . import db


# Contas fictícias de demonstração (usuário, senha, nome, matrícula, curso, recado privado)
USUARIOS = [
    (
        "aluno",
        "aluno123",
        "Ana Vitima da Silva",
        "2023100045",
        "Sistemas de Informação",
        "Recado privado da Ana: reservei a sala 204 para o grupo na quinta às 19h. "
        "Minha nota de Cálculo saiu 8,5 — não contei pra ninguém ainda.",
    ),
    (
        "atacante",
        "atacante123",
        "Beto Atacap Souza",
        "2023100099",
        "Ciência da Computação",
        "Recado privado do Beto: preciso devolver o livro da biblioteca até sexta.",
    ),
]

PUBLICACOES = []

COMENTARIOS = []


def _iso_agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def seed(force: bool = False):
    import os

    if force and os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)

    conn = db.get_conn()
    db.init_schema(conn)

    ja_tem = conn.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    if ja_tem and not force:
        print(f"[seed] Banco já populado em {db.DB_PATH} (use --force para recriar).")
        conn.close()
        return

    agora = _iso_agora()
    for usuario, senha, nome, matricula, curso, recado in USUARIOS:
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, nome, matricula, curso, recado_privado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (usuario, generate_password_hash(senha), nome, matricula, curso, recado),
        )
    for titulo, corpo, autor in PUBLICACOES:
        conn.execute(
            "INSERT INTO publicacoes (titulo, corpo, autor, criado_em) VALUES (?, ?, ?, ?)",
            (titulo, corpo, autor, agora),
        )
    for pub_id, autor, conteudo in COMENTARIOS:
        conn.execute(
            "INSERT INTO comentarios (publicacao_id, autor, conteudo, criado_em) "
            "VALUES (?, ?, ?, ?)",
            (pub_id, autor, conteudo, agora),
        )
    conn.commit()
    conn.close()
    print(f"[seed] Banco criado e populado em {db.DB_PATH}")


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
