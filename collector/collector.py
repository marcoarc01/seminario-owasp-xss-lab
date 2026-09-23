"""
Coletor do laboratório — "receptor do atacante".

Programa SEPARADO do portal. Roda em http://127.0.0.1:9000 (loopback).
Não tem, e não deve ter, acesso ao banco de usuários/sessões do portal:
ele só sabe o que o payload envia explicitamente.

Papel didático:
- Recebe, num endpoint local, APENAS o formato esperado da demonstração
  (campo "token" enviado pelo payload), com tamanho limitado.
- Mostra no TERMINAL cada captura real: horário, origem da conexão, token
  fictício recebido e o total de capturas reais. O terminal é a evidência
  principal pedida pelo professor.
- Distingue verificações de saúde/teste das capturas reais e NÃO registra
  sucesso fictício.
- NÃO trata o cabeçalho Cookie recebido como prova: contamos apenas envios
  explícitos feitos pelo payload (campo "token" no corpo).
- Uma página opcional (/) lista as capturas em tabela ESCAPADA, com botão
  "Copiar token". É a "página do atacante" — sem dashboard elaborado.

Isolamento de host (importante): o portal usa o host "localhost" e o coletor
usa "127.0.0.1". São hosts diferentes, então o navegador NÃO envia o cookie
campus_session do portal para cá automaticamente. Só chega aqui o que o
payload ler de document.cookie e mandar de propósito.
"""
import sys
from datetime import datetime, timezone

from flask import Flask, abort, render_template, request

COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 9000
HOSTS_ESPERADOS = {f"127.0.0.1:{COLLECTOR_PORT}", f"localhost:{COLLECTOR_PORT}"}

# Limites do formato esperado.
MAX_BODY_BYTES = 4096      # corpo pequeno; demo não precisa de mais
MAX_TOKEN_LEN = 512

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

# Estado em memória (nada é persistido; nada vem do portal).
CAPTURAS = []              # apenas envios explícitos do payload
_saude = {"n": 0}         # contador de verificações de saúde/teste


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _origem():
    # Origem da conexão para o terminal. remote_addr é o IP de loopback;
    # Origin/Referer ajudam a mostrar de qual host partiu o pedido.
    origin = request.headers.get("Origin") or request.headers.get("Referer") or "-"
    return f"{request.remote_addr} (Origin: {origin})"


@app.before_request
def _validar_host():
    if request.host not in HOSTS_ESPERADOS:
        abort(400, "Host não esperado para o coletor (use http://127.0.0.1:9000).")


@app.route("/health")
def health():
    # Verificação de saúde: NÃO é captura. Serve para provar, antes do reteste,
    # que o coletor está no ar — assim um terminal vazio no reteste significa
    # "defesa funcionou", e não "coletor caído".
    _saude["n"] += 1
    print(f"[saude ] {_agora()} · origem={_origem()} · verificacao #{_saude['n']} "
          f"(NAO e captura)", flush=True)
    return {"status": "ok", "capturas": len(CAPTURAS)}, 200


@app.route("/collect", methods=["GET", "POST"])
def collect():
    """
    Só conta como captura um POST com o campo 'token' dentro do limite.
    Qualquer outra coisa (GET, ausência de token) é tratada como teste/saúde
    e NÃO vira captura. O cabeçalho Cookie eventualmente presente é ignorado
    de propósito — ele não prova ataque nenhum.
    """
    token = request.form.get("token") if request.method == "POST" else None

    if not token:
        _saude["n"] += 1
        print(f"[teste ] {_agora()} · origem={_origem()} · requisicao sem token "
              f"(NAO e captura)", flush=True)
        return {"status": "sem-token"}, 200

    if len(token) > MAX_TOKEN_LEN:
        print(f"[recusa] {_agora()} · origem={_origem()} · token acima do limite", flush=True)
        abort(413)

    origem_host = request.form.get("origin", "-")[:128]
    captura = {
        "hora": _agora(),
        "origem": _origem(),
        "origem_host": origem_host,
        "token": token,
    }
    CAPTURAS.append(captura)
    print("[CAPTURA] " + "-" * 52, flush=True)
    print(f"          hora   : {captura['hora']}", flush=True)
    print(f"          origem : {captura['origem']}", flush=True)
    print(f"          host   : {origem_host}", flush=True)
    print(f"          token  : {token}", flush=True)
    print(f"          total de capturas reais: {len(CAPTURAS)}", flush=True)
    print("          " + "-" * 52, flush=True)

    # Resposta mínima. O payload usa mode:'no-cors' e não lê esta resposta,
    # então NÃO liberamos CORS com credenciais nem nada global.
    return {"status": "ok"}, 200


@app.route("/")
def painel():
    # Página do atacante: tabela escapada + botão copiar. Tudo que veio de fora
    # é exibido via autoescape do Jinja, evitando XSS no próprio coletor.
    return render_template(
        "painel.html",
        capturas=list(reversed(CAPTURAS)),
        total=len(CAPTURAS),
        saude=_saude["n"],
    )


def main():
    print(f"[coletor] recebendo em http://{COLLECTOR_HOST}:{COLLECTOR_PORT}")
    print("[coletor] terminal e a evidencia principal. Ctrl+C para encerrar.")
    # debug=False: sem depurador interativo. Bind somente loopback.
    app.run(host=COLLECTOR_HOST, port=COLLECTOR_PORT, debug=False)


if __name__ == "__main__":
    main()
