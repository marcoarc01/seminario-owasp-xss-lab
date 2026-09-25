# Guia de proteção contra Stored XSS

Este laboratório demonstra um Stored XSS: um comentário é salvo no banco e
depois exibido no navegador. A vulnerabilidade acontece quando o comentário é
interpretado como HTML/JavaScript em vez de ser tratado como texto.

## Fluxo do ataque

```text
comentário salvo
    -> HTML interpretado
    -> JavaScript executado
    -> cookie lido
    -> token enviado
    -> sessão reutilizada
```

A proteção é feita em camadas. Cada camada reduz uma parte diferente desse
fluxo.

## 1. Escape na saída: a correção principal

Arquivo: `portal/templates/publicacao.html`.

Estado vulnerável:

```jinja2
<div class="comentario-corpo">{{ comentario.conteudo | safe }}</div>
```

O filtro `safe` desliga o escape automático do Jinja. Assim, um comentário como
`<script>alert(1)</script>` pode ser interpretado pelo navegador como código.

Estado corrigido:

```jinja2
<div class="comentario-corpo">{{ comentario.conteudo }}</div>
```

Sem `safe`, o autoescape do Jinja transforma os caracteres HTML em entidades.
O comentário continua armazenado no banco, mas aparece como texto e não como
elemento executável.

Não usamos regex para remover a palavra `script`. A defesa correta é fazer
codificação de saída no contexto HTML. Se uma aplicação precisar aceitar HTML
formatado, deve usar um sanitizador com lista explícita de tags e atributos
permitidos.

## 2. Content Security Policy (CSP)

No modo corrigido, o portal envia:

```text
default-src 'self';
script-src 'self';
style-src 'self';
img-src 'self';
connect-src 'self';
base-uri 'self';
form-action 'self';
frame-ancestors 'none'
```

Essa política é configurada em `portal/config.py` e adicionada às respostas em
`portal/app.py`.

- `script-src 'self'` permite somente scripts da própria aplicação.
- A ausência de `unsafe-inline` bloqueia `<script>` injetado e handlers inline.
- A ausência de `unsafe-eval` bloqueia mecanismos como `eval()`.
- `connect-src 'self'` restringe `fetch` e conexões a outras origens.
- `base-uri 'self'` dificulta alteração da URL-base da página.
- `form-action 'self'` restringe o destino de formulários.
- `frame-ancestors 'none'` impede que o portal seja embutido em um iframe.

CSP é uma camada adicional. Ela não substitui o escape do comentário.

## 3. Cookie `HttpOnly`

No modo corrigido, o cookie `campus_session` é emitido com:

```python
httponly=True
```

Isso impede que JavaScript leia o valor com `document.cookie`.

`HttpOnly` não impede o XSS de executar nem impede todas as ações feitas pelo
navegador da vítima. Ele apenas impede a leitura direta do cookie. Por isso o
escape continua sendo a correção principal.

Depois de iniciar o modo corrigido, é necessário fazer login novamente para o
cookie ser emitido com o novo atributo.

## 4. `SameSite`, `Secure` e host-only

O cookie usa `SameSite=Lax`, que reduz o envio em algumas requisições
cross-site e ajuda contra CSRF. Isso não corrige XSS, porque o XSS executa na
origem do próprio portal.

`Secure=True` faz o cookie ser enviado somente por HTTPS. No laboratório HTTP
local ele fica desligado para a demonstração funcionar. Em produção, o portal
deve usar HTTPS e `Secure=True`.

O cookie não define `Domain`, portanto é host-only: o cookie de
`localhost:5000` não é enviado automaticamente para `127.0.0.1:9000`.

## 5. Sessões opacas, expiração e revogação

O login cria um token aleatório com `secrets.token_urlsafe(32)`. No banco é
guardado apenas o hash SHA-256 do token, nunca o token em claro.

Cada sessão:

- expira depois de oito horas;
- é validada a cada requisição protegida;
- pode ser revogada no logout;
- é invalidada pelo `reset.py`.

Se um token já tiver sido capturado, corrigir o código não o invalida sozinho.
É necessário revogar as sessões comprometidas e exigir novo login.

## 6. Senhas e banco

As senhas são armazenadas somente como hash usando Werkzeug/scrypt.

As consultas ao SQLite usam placeholders (`?`). Isso protege contra SQL
injection, que é diferente de XSS. A parametrização protege o banco; o escape
protege o navegador.

O comentário é armazenado sem sanitização propositalmente. O ponto seguro é a
renderização: dados não confiáveis devem ser escapados no momento da saída.

## 7. Outras camadas do laboratório

O portal:

- aceita somente hosts esperados;
- escuta apenas no loopback, não em `0.0.0.0`;
- envia `X-Content-Type-Options: nosniff`;
- exige sessão para acessar mural, publicações e conta;
- mantém o coletor separado do banco do portal;
- limita o coletor ao ambiente local e a um corpo pequeno.

Essas medidas restringem o laboratório e reduzem exposição, mas não substituem
a correção do template.

## Como demonstrar a correção

1. No modo vulnerável, publique:

   ```html
   <script>alert(1)</script>
   ```

   O alerta demonstra a execução do Stored XSS.

2. Pare o portal com `Ctrl+C`.

3. Remova `| safe` em `portal/templates/publicacao.html`.

4. Reinicie no modo corrigido:

   ```powershell
   $env:LAB_MODE="corrigido"
   python run_portal.py
   ```

5. Faça login novamente.

6. Recarregue a publicação. O payload deve aparecer como texto, sem alerta.

7. No console do navegador, execute `document.cookie`. O cookie
   `campus_session` não deve aparecer.

8. No DevTools, confirme os cabeçalhos `Content-Security-Policy` e
   `X-Content-Type-Options: nosniff`.

Se houve captura durante o teste:

```powershell
python reset.py
```

Esse comando recria o banco local, remove os dados criados manualmente e
invalida as sessões antigas.

## O que dizer na apresentação

> A correção principal é nunca interpretar conteúdo não confiável como código.
> O escape transforma o comentário em texto. CSP e HttpOnly são barreiras
> adicionais: a primeira restringe scripts e conexões, e a segunda impede que
> JavaScript leia o cookie. Se uma sessão já foi capturada, precisamos revogá-la
> no servidor; corrigir o código não invalida tokens antigos automaticamente.

## Onde está o Jinja?

O Jinja não foi instalado diretamente por este projeto. Ele vem como
dependência do Flask:

```text
requirements.txt -> Flask -> Jinja2
```

Os templates Jinja estão em:

```text
portal/templates/
```

Exemplos:

- `portal/templates/publicacao.html`
- `portal/templates/base.html`
- `portal/templates/login.html`
- `portal/templates/conta.html`

O Flask localiza essa pasta automaticamente porque ela está dentro do pacote
`portal`. Os templates são renderizados pelas chamadas `render_template(...)`
em `portal/app.py`, por exemplo:

```python
return render_template("publicacao.html", pub=pub, comentarios=comentarios)
```

O Jinja processa expressões como:

```jinja2
{{ comentario.conteudo }}
```

e comandos como:

```jinja2
{% for comentario in comentarios %}
{% if not vulneravel %}
```

O Flask entrega ao Jinja os dados do banco e o Jinja gera o HTML final que o
navegador recebe. Por isso o problema não está no `INSERT` do comentário: está
na decisão do template de renderizar o valor com `| safe` ou com autoescape.

