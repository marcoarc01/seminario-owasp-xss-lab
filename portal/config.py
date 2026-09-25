import os


PORTAL_HOST = "localhost"
PORTAL_PORT = 5000
COLLECTOR_ORIGIN = "http://127.0.0.1:9000"

# Nome do cookie de sessão do portal.
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
    if is_vulneravel():
        return {
            "httponly": False,   # falha intencional: cookie legível por JS
            "samesite": "Lax",   # padrão razoável; não é o que corrige o XSS
            "secure": False,     # perfil HTTP local
        }
    # modo corrigido
    return {
        "httponly": True,        # bloqueia document.cookie
        "samesite": "Lax",       # reduz envio cross-site (não impede XSS)
        # "secure" vira True automaticamente quando servido por HTTPS;
        "secure": os.environ.get("PORTAL_HTTPS", "0") == "1",
    }

# CSP
def content_security_policy() -> str | None:
    if is_vulneravel():
        return None
    return (
        "default-src 'self'; "       # padrão: recursos só da própria origem
        "script-src 'self'; "        # scripts locais; bloqueia script inline
        "style-src 'self'; "         # estilos só da própria aplicação
        "img-src 'self'; "           # imagens só da própria aplicação
        "connect-src 'self'; "       # fetch/conexões só para a mesma origem
        "base-uri 'self'; "          # impede trocar a URL-base por outra origem
        "form-action 'self'; "       # formulários só enviam para a própria origem
        "frame-ancestors 'none'"     # impede abrir o portal dentro de iframe
    )
