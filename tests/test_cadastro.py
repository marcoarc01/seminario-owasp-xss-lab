"""Cadastro e login usando um SQLite temporário, sem tocar no banco do laboratório."""
import os
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import check_password_hash

from portal import db
from portal.app import app


class CadastroTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, "DB_PATH", os.path.join(self.tempdir.name, "mural.db"))
        self.db_patch.start()
        conn = db.get_conn()
        db.init_schema(conn)
        conn.close()
        self.client = app.test_client()
        self.base_url = "http://localhost:5000"
        self.dados = {
            "usuario": "nova_aluna",
            "nome": "Nova Aluna",
            "matricula": "20260001",
            "curso": "Sistemas de Informação",
            "recado_privado": "Recado de teste",
            "senha": "senha-ficticia",
            "confirmar_senha": "senha-ficticia",
        }

    def tearDown(self):
        self.db_patch.stop()
        self.tempdir.cleanup()

    def test_cadastro_persiste_hash_e_permite_login(self):
        login_page = self.client.get("/login", base_url=self.base_url)
        self.assertIn(b'href="/cadastro"', login_page.data)

        resposta = self.client.post("/cadastro", data=self.dados, base_url=self.base_url)
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/mural")
        self.assertIn("campus_session=", resposta.headers["Set-Cookie"])

        conta = self.client.get("/minha-conta", base_url=self.base_url)
        self.assertIn(b"Recado de teste", conta.data)

        conn = db.get_conn()
        row = db.get_usuario_por_nome(conn, "nova_aluna")
        self.assertIsNotNone(row)
        self.assertNotEqual(row["senha_hash"], self.dados["senha"])
        self.assertTrue(check_password_hash(row["senha_hash"], self.dados["senha"]))
        conn.close()

        outro_navegador = app.test_client()
        login = outro_navegador.post(
            "/login", data={"usuario": "nova_aluna", "senha": "senha-ficticia"},
            base_url=self.base_url,
        )
        self.assertEqual(login.status_code, 302)
        self.assertEqual(login.headers["Location"], "/mural")

    def test_usuario_duplicado_e_campos_invalidos_nao_criam_conta(self):
        self.client.post("/cadastro", data=self.dados, base_url=self.base_url)
        duplicado = self.client.post("/cadastro", data=self.dados, base_url=self.base_url)
        self.assertEqual(duplicado.status_code, 200)
        self.assertIn("já está em uso".encode(), duplicado.data)

        invalido = dict(self.dados, usuario="a;DROP", senha="123")
        resposta = self.client.post("/cadastro", data=invalido, base_url=self.base_url)
        self.assertEqual(resposta.status_code, 200)
        conn = db.get_conn()
        total = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        conn.close()
        self.assertEqual(total, 1)


if __name__ == "__main__":
    unittest.main()
