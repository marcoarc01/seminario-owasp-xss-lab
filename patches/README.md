# Correções — pontos de alteração ao vivo

Este laboratório separa **duas coisas** de propósito, e isso é o que permite
testar cada defesa isoladamente:

1. **O escape do comentário** é uma **edição de código** no template
   (`portal/templates/publicacao.html`). É a correção principal do XSS.
2. **Cookie (HttpOnly), CSP e UX** são controlados pelo **modo de laboratório**
   (`LAB_MODE=corrigido`), implementados em `portal/config.py` e
   `portal/app.py`. O código que os liga está à vista e é explicável.

Assim é possível, por exemplo, rodar em modo `corrigido` **sem** aplicar o
escape para ver a **CSP bloqueando** o script sozinha, ou aplicar o escape
**sem** o modo corrigido para ver o **escape** resolvendo sozinho.

---

## 1. Correção principal — escape do comentário (Stored XSS)

Arquivo: `portal/templates/publicacao.html`

```diff
- <div class="comentario-corpo">{{ comentario.conteudo | safe }}</div>
+ <div class="comentario-corpo">{{ comentario.conteudo }}</div>
```

O texto original **continua no banco** — só muda a renderização: com o
autoescape do Jinja ligado, `<script>` vira texto exibido, não código.
**Não** usamos regex nem removemos a palavra "script": isso seria frágil e
não é a defesa correta. A defesa é tratar o dado como **texto no contexto HTML**.

Formas de aplicar:

- **Ao vivo (recomendado na apresentação):** abra o arquivo e apague ` | safe`
  na linha do corpo do comentário. Salve. O Flask recarrega sozinho.
- **Por patch:** `patch -p1 < patches/remediation.diff` (Git Bash / macOS /
  Linux). Reverter: `patch -p1 -R < patches/remediation.diff`.
- **Por cópia:** copie `patches/secure/publicacao.html` sobre
  `portal/templates/publicacao.html`. Para voltar ao estado vulnerável,
  restaure a versão original (guarde uma cópia antes, ou use o patch reverso).

Reteste: recarregue a publicação com `<script>alert(1)</script>` — aparece
como texto, sem alerta. Comentários normais continuam legíveis.

---

## 2. Cookie — HttpOnly no ponto real de emissão

Arquivos: `portal/config.py` (função `cookie_flags`) e `portal/app.py`
(função `_emitir_sessao`, que chama `response.set_cookie`).

O cookie é criado **à mão** com `set_cookie`, então **nada é implícito**: os
atributos são passados um a um. Não presumimos que uma configuração global
(por ex. `SESSION_COOKIE_HTTPONLY`) altere um cookie que criamos manualmente —
ela só afeta o cookie de sessão nativo do Flask, que **não** é o nosso.

```python
# modo vulnerável:  httponly=False   (cookie legível por document.cookie)
# modo corrigido:   httponly=True    (JavaScript não lê o cookie)
resp.set_cookie(COOKIE_NAME, token,
                httponly=flags["httponly"],
                samesite=flags["samesite"],
                secure=flags["secure"],
                path="/")   # sem domain => host-only
```

**Verificação:** é preciso **reemitir o cookie** (novo login) para o atributo
valer. Depois, no DevTools → Application → Cookies, `campus_session` mostra
`HttpOnly = ✓`, e `document.cookie` no console **não** traz o cookie.

**Limite honesto:** HttpOnly impede a **leitura** do cookie por JavaScript.
Ele **não** impede o XSS de executar, nem impede o script de fazer outras
ações em nome do usuário (por ex. postar comentários via `fetch` com as
credenciais da sessão). Por isso HttpOnly é uma **camada**, não a correção
do XSS — a correção do XSS é o escape.

---

## 3. CSP — Content-Security-Policy restritiva

Arquivos: `portal/config.py` (`content_security_policy`) e `portal/app.py`
(`_cabecalhos_seguranca`, no `after_request`).

```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self';
connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

- `script-src 'self'`: só executam scripts vindos de **arquivos próprios**
  (`static/portal.js`). **Sem** `unsafe-inline` e **sem** `unsafe-eval` para
  scripts. Por isso todo o nosso JavaScript legítimo mora em arquivo separado.
- Um `<script>` inline injetado num comentário é **bloqueado** pela CSP, com
  erro no console: *"Refused to execute inline script..."*.

**Testar a CSP isolada:** rode em modo `corrigido` **com o template ainda
vulnerável** (`|safe`). O comentário `<script>alert(1)</script>` é emitido cru,
mas **não executa** — quem barra é a CSP, e o console mostra a violação.
Não confunda isso com a correção pelo escape: aqui o escape está desligado
de propósito, só para ver a CSP trabalhando.

**Limite honesto:** CSP **complementa** o escape, não o substitui. Uma CSP mal
configurada (com `unsafe-inline`) não protegeria. E a CSP não desfaz um token
já capturado.

---

## 4. SameSite e Secure — o que fazem (e o que NÃO fazem)

Arquivo: `portal/config.py` (`cookie_flags`).

- **SameSite** (`Lax`/`Strict`): controla se o cookie é enviado em requisições
  **cross-site**. Reduz risco de CSRF. **Não corrige XSS**: o script injetado
  roda **na própria origem** do portal, então SameSite não o impede de ler ou
  usar a sessão.
- **Secure**: faz o navegador só enviar o cookie por **HTTPS**. **Não** impede
  o JavaScript de ler o cookie (quem faz isso é o HttpOnly) — Secure é sobre o
  **transporte**, não sobre leitura no navegador.

**Perfil HTTP local (padrão):** a demonstração roda em HTTP no loopback;
`Secure` fica desligado para o cookie funcionar.

**Perfil HTTPS local (opcional) para verificar o Secure:**

```
# instale a dependência opcional
pip install cryptography

# Windows/PowerShell
$env:LAB_MODE="corrigido"; $env:PORTAL_HTTPS="1"; python run_portal.py
# macOS/Linux
LAB_MODE=corrigido PORTAL_HTTPS=1 python run_portal.py
```

O portal sobe com certificado **self-signed** temporário (`ssl_context="adhoc"`).
O navegador vai avisar do certificado — aceite **apenas para este localhost**.
Abra `https://localhost:5000`, faça login e veja `Secure = ✓` no cookie.
**Não** desabilite a validação TLS do sistema/navegador globalmente; o aviso
é local e esperado.

---

## 5. UX — remover o aviso repetitivo

Arquivos: os templates (o bloco do modal em `base.html` e o `data-aviso`) e
`portal/static/portal.js`. No modo `corrigido`, o aviso repetitivo do modal
**não** aparece; no lugar dele, o mural e a publicação mostram uma **orientação
discreta e contextual** ("os comentários são exibidos como texto").

A fadiga de alerta era só um comportamento de UX pedido para observação. Ela
**não é necessária** para o XSS executar: a causa técnica do XSS é o comentário
ser interpretado como **código**. Tirar os avisos não muda a segurança — muda a
experiência.

---

## Resposta a uma sessão já comprometida

Ativar HttpOnly ou CSP **não invalida** um token que já foi capturado antes da
correção. A resposta correta a uma sessão comprometida inclui **revogar** as
sessões (logout server-side / `reset.py`, que invalida as sessões antigas) e,
se fosse um sistema real, forçar novo login.

E lembre: **consultas parametrizadas** (que usamos em todo o projeto) previnem
**SQL injection**, não XSS. São defesas para problemas diferentes.

---

## Referências oficiais (verificadas em setembro/2026)

- OWASP Top 10:2025 — **A05:2025 Injection**, que **inclui Cross-Site Scripting**
  (na edição de 2021 era **A03:2021 Injection**):
  https://owasp.org/Top10/2025/A05_2025-Injection/
- OWASP Cross Site Scripting Prevention Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- OWASP Content Security Policy Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- Flask — segurança / cookies de sessão e `set_cookie`:
  https://flask.palletsprojects.com/en/stable/security/
- Jinja — autoescape e o filtro `safe`:
  https://jinja.palletsprojects.com/en/stable/templates/#working-with-automatic-escaping
