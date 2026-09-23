"""
Reset do laboratório — para ensaiar novamente do zero.

O reset é RESTRITO aos arquivos do projeto: ele só recria o banco
instance/mural.db (contas, publicações e comentários de semente) e, ao
recriar, invalida todas as sessões antigas. Não apaga nada fora do projeto.

Uso:
    python reset.py

Depois do reset, será preciso fazer login de novo (as sessões antigas
deixam de valer).
"""
import os

from portal import db
from portal.seed import seed


def main():
    caminho = db.DB_PATH
    if os.path.exists(caminho):
        os.remove(caminho)
        print(f"[reset] banco removido: {caminho}")
    # Recria e popula. Sessões antigas deixam de existir (tabela recriada).
    seed(force=True)
    print("[reset] laboratório reiniciado. Faça login novamente.")


if __name__ == "__main__":
    main()
