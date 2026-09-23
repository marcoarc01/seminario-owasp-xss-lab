"""
Configuração do laboratório — Mural do Campus (portal).

O "modo de laboratório" é escolhido por variável de ambiente / configuração,
NÃO por um botão público na interface. Isso atende ao requisito de não haver
um controle que qualquer visitante use para ligar/desligar proteções.

    LAB_MODE=vulneravel   -> cenário com a falha (padrão)
    LAB_MODE=corrigido    -> proteções ativas

Importante sobre a correção principal do XSS:
    A troca de {{ comentario.conteudo | safe }} por {{ comentario.conteudo }}
    é uma EDIÇÃO DE CÓDIGO real, feita ao vivo (ou aplicando patches/remediation.diff).
    O template pergunta ao modo apenas para decidir o cabeçalho/UX e os
    atributos do cookie/CSP — a linha do |safe existe de verdade no arquivo e
    é ela que se corrige na apresentação. Ver portal/templates/publicacao.html.

Este arquivo concentra, num só lugar, as diferenças de postura de segurança
entre os dois modos, para os apresentadores conseguirem explicar cada uma.
"""
import os

# Hosts esperados. O portal só deve ser servido em localhost (host-only).
# O coletor fica em 127.0.0.1 — um HOST DIFERENTE de propósito, para provar
# que portas diferentes não isolam cookies, mas hosts diferentes sim.
PORTAL_HOST = "localhost"
PORTAL_PORT = 5000
COLLECTOR_ORIGIN = "http://127.0.0.1:9000"   # destino fixo do payload

# Nome do cookie de sessão do portal. Host-only (sem atributo Domain).
COOKIE_NAME = "campus_session"

# Duração da sessão.
SESSION_TTL_HOURS = 8


def lab_mode() -> str:
    mode = os.environ.get("LAB_MODE", "vulneravel").strip().lower()
    if mode not in ("vulneravel", "corrigido"):
        mode = "vulneravel"
    return mode


def is_vulneravel() -> bool:
    return lab_mode() == "vulneravel"


def cookie_flags() -> dict:
    """
    Atributos aplicados EXPLICITAMENTE ao emitir campus_session.

    Como o cookie é criado à mão (response.set_cookie), nada é implícito:
    - No modo vulnerável, HttpOnly fica desligado de propósito, para o
      JavaScript do comentário conseguir ler document.cookie na demonstração.
      (Não é que "o Flask desliga HttpOnly sozinho" — somos nós que o
      definimos aqui, valor por valor.)
    - No modo corrigido, HttpOnly=True impede a leitura por JavaScript.

    SameSite/Secure: ver comentários abaixo e a explicação no README. Eles
    NÃO corrigem XSS; entram como camadas adicionais.
    """
    if is_vulneravel():
        return {
            "httponly": False,   # falha intencional: cookie legível por JS
            "samesite": "Lax",   # padrão razoável; não é o que corrige o XSS
            "secure": False,     # perfil HTTP local
            # sem "domain": cookie host-only (vale só para o host que o emitiu)
        }
    # modo corrigido
    return {
        "httponly": True,        # bloqueia document.cookie
        "samesite": "Lax",       # reduz envio cross-site (não impede XSS)
        # "secure" vira True automaticamente quando servido por HTTPS;
        # ver SECURE_COOKIE abaixo e o perfil HTTPS documentado no README.
        "secure": os.environ.get("PORTAL_HTTPS", "0") == "1",
    }


def content_security_policy() -> str | None:
    """
    Política de CSP. Só é aplicada no modo corrigido.

    - script-src 'self': apenas nossos scripts em arquivos próprios
      (static/portal.js). Nada de 'unsafe-inline' nem 'unsafe-eval' para
      scripts — por isso um <script> injetado inline é bloqueado.
    - style-src 'self': estilos só do nosso arquivo static/portal.css.
    A CSP COMPLEMENTA o escape; não substitui a correção do template.
    """
    if is_vulneravel():
        return None
    return (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self'; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
