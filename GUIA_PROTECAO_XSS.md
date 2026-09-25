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

### Como explicar a CSP durante a apresentação

Os comentários colocados ao lado das diretivas em `portal/config.py` servem
apenas como lembretes para os apresentadores. Comentários no código não são
executados e não alteram o funcionamento da aplicação nem o cabeçalho enviado
ao navegador.

Para esta demonstração, não é necessário explicar individualmente todas as
diretivas. As duas mais importantes são:

```text
script-src 'self'
connect-src 'self'
```

Uma explicação recomendada é:

> A CSP é uma política enviada pelo servidor e aplicada pelo navegador.
> `script-src 'self'` permite scripts da própria aplicação, mas bloqueia o
> script inline inserido no comentário, porque não permitimos
> `unsafe-inline`. `connect-src 'self'` impede que o JavaScript faça conexões
> com outra origem, como o coletor em `127.0.0.1:9000`.

Se houver tempo, as outras diretivas podem ser resumidas assim:

> A política também restringe estilos, imagens e formulários à própria origem
> e impede que o portal seja colocado dentro de um iframe.

É importante não afirmar que toda CSP sempre bloqueia scripts inline. Neste
laboratório isso acontece porque usamos `script-src 'self'` e não adicionamos
`unsafe-inline` à política.

Resumo para memorizar:

> O escape do Jinja é a correção principal. A CSP é uma segunda camada: ela
> bloqueia o script inline e restringe conexões para outras origens. Se algum
> JavaScript ainda fosse executado, o `HttpOnly` impediria a leitura direta do
> cookie de sessão.

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

## XSS em outras linguagens e frameworks

XSS não é uma falha exclusiva de Python, Flask ou Jinja. Ela pode existir em
qualquer tecnologia que coloque dados não confiáveis dentro de uma página sem
aplicar a proteção adequada ao contexto.

A linguagem usada no servidor não é o ponto principal. O ataque termina no
navegador, porque é o navegador que interpreta HTML, JavaScript, CSS e URLs.

### O padrão que normalmente causa a falha

Quase todo XSS possui três partes:

1. **Fonte:** local de onde chega o dado não confiável, como formulário, URL,
   banco de dados, API, cabeçalho HTTP ou mensagem de outro usuário.
2. **Processamento:** o sistema armazena, copia ou transforma o valor.
3. **Ponto de execução (sink):** o dado é colocado em um local que o navegador
   interpreta como código, como `innerHTML`, um template sem escape ou um
   atributo de evento.

Exemplo conceitual:

```text
entrada do usuário -> banco/API -> template ou DOM -> navegador interpreta
```

O banco não precisa estar vulnerável. Ele pode armazenar corretamente uma
string perigosa e a falha aparecer somente quando essa string é renderizada.

### Tipos mais comuns de XSS

#### Stored XSS ou XSS persistente

O conteúdo malicioso é armazenado no servidor, por exemplo em comentários,
perfis, chamados, mensagens ou nomes de arquivos. Toda pessoa que abre a página
pode receber o conteúdo. É o tipo demonstrado neste laboratório.

```text
atacante publica -> servidor armazena -> vítima abre -> navegador executa
```

#### Reflected XSS ou XSS refletido

O conteúdo vem na própria requisição e é devolvido imediatamente na resposta,
sem ser armazenado. Um exemplo seria uma página de busca que colocasse o termo
da URL diretamente no HTML sem escape.

```text
link preparado -> vítima acessa -> servidor reflete o valor -> navegador executa
```

#### DOM-based XSS

A falha acontece no JavaScript executado no navegador. O servidor pode até
entregar um HTML estático seguro, mas o código da página lê um valor da URL,
do armazenamento local ou de uma mensagem e o envia para uma API perigosa do
DOM.

Exemplo vulnerável:

```javascript
resultado.innerHTML = new URLSearchParams(location.search).get("mensagem");
```

Forma segura para exibir texto:

```javascript
resultado.textContent = new URLSearchParams(location.search).get("mensagem");
```

`textContent` cria texto. `innerHTML` pede ao navegador para interpretar o
valor como HTML.

### JavaScript no navegador

APIs que merecem atenção quando recebem dados não confiáveis:

```javascript
element.innerHTML = valor;
element.outerHTML = valor;
element.insertAdjacentHTML("beforeend", valor);
document.write(valor);
eval(valor);
new Function(valor);
```

Para texto, prefira:

```javascript
element.textContent = valor;
```

Para criar elementos, prefira as APIs estruturadas do DOM:

```javascript
const item = document.createElement("li");
item.textContent = valor;
lista.appendChild(item);
```

Se for realmente necessário aceitar HTML, o conteúdo precisa passar por um
sanitizador mantido e configurado com uma lista pequena de elementos e
atributos permitidos. Sanitização não é a mesma coisa que procurar e remover a
palavra `script`.

### PHP

Exemplo vulnerável:

```php
echo $_POST['comentario'];
```

Para exibir texto dentro de HTML:

```php
echo htmlspecialchars(
    $_POST['comentario'],
    ENT_QUOTES | ENT_SUBSTITUTE,
    'UTF-8'
);
```

`htmlspecialchars` é apropriado para texto no contexto HTML. Para URLs,
JavaScript, CSS ou outros contextos, são necessárias validações e codificações
específicas.

### Node.js com Express e EJS

No EJS, esta forma aplica escape:

```ejs
<%= comentario %>
```

Esta forma envia HTML sem escape e pode causar XSS:

```ejs
<%- comentario %>
```

Concatenar strings manualmente também é perigoso:

```javascript
res.send("<p>" + req.query.mensagem + "</p>");
```

Usar consultas SQL parametrizadas não corrige esse problema. SQL injection e
XSS acontecem em interpretadores e contextos diferentes.

### React

React normalmente escapa valores usados na interpolação:

```jsx
<p>{comentario}</p>
```

O ponto perigoso é desativar essa proteção:

```jsx
<div dangerouslySetInnerHTML={{ __html: comentario }} />
```

O nome `dangerouslySetInnerHTML` é proposital: o conteúdo precisa ser confiável
ou sanitizado antes do uso. React também não protege automaticamente código
que manipula o DOM diretamente fora do seu sistema de renderização.

### Vue

Interpolação comum é escapada:

```vue
<p>{{ comentario }}</p>
```

`v-html` interpreta o valor como HTML:

```vue
<div v-html="comentario"></div>
```

Dados de usuários não devem ser enviados para `v-html` sem sanitização
adequada.

### Angular

A interpolação normal trata o valor como texto:

```html
<p>{{ comentario }}</p>
```

Angular aplica sanitização em contextos como `[innerHTML]`, mas essa proteção
pode ser anulada por APIs de confiança explícita, como
`bypassSecurityTrustHtml`. Marcar um valor do usuário como confiável sem
sanitização recria a vulnerabilidade.

Também é preciso cuidado ao usar APIs nativas do DOM diretamente, porque elas
podem ficar fora das proteções oferecidas pelo framework.

### Java com JSP ou Thymeleaf

Em JSP, imprimir valores diretamente pode não fornecer a codificação HTML
necessária. Com JSTL, pode-se usar:

```jsp
<c:out value="${comentario}" />
```

No Thymeleaf, `th:text` trata o valor como texto:

```html
<p th:text="${comentario}"></p>
```

`th:utext` produz texto não escapado e é perigoso com dados não confiáveis:

```html
<p th:utext="${comentario}"></p>
```

### C# com ASP.NET Razor

Razor normalmente codifica valores:

```cshtml
<p>@Model.Comentario</p>
```

`Html.Raw` desativa essa proteção:

```cshtml
<p>@Html.Raw(Model.Comentario)</p>
```

É o equivalente conceitual ao filtro `safe` do Jinja.

### Ruby on Rails

Rails normalmente escapa a interpolação:

```erb
<p><%= @comentario %></p>
```

Métodos que marcam conteúdo como seguro precisam de cuidado:

```erb
<%= raw @comentario %>
<%= @comentario.html_safe %>
```

Usá-los com entrada de usuário pode permitir XSS.

### Go

Para gerar páginas HTML, o pacote recomendado é `html/template`, que faz
escape sensível ao contexto:

```go
template.Must(template.New("pagina").Parse(`<p>{{.Comentario}}</p>`))
```

Usar `text/template` para gerar HTML, montar HTML por concatenação ou converter
entrada do usuário para `template.HTML` pode remover essa proteção.

### Markdown, editores ricos e HTML permitido

Aplicações que transformam Markdown em HTML ou possuem editores WYSIWYG
precisam de atenção especial. O conversor pode permitir HTML embutido,
atributos perigosos, URLs inadequadas ou recursos externos.

Uma estratégia segura é:

1. converter o conteúdo;
2. sanitizar o HTML resultante com uma lista de permissões;
3. remover atributos de evento como `onclick`;
4. validar protocolos de URL;
5. aplicar CSP como defesa adicional.

### A proteção depende do contexto

Escape HTML não é uma solução universal. O mesmo valor pode exigir uma defesa
diferente conforme o local onde é colocado.

| Contexto | Exemplo | Proteção principal |
|---|---|---|
| Texto HTML | `<p>VALOR</p>` | Escape HTML automático |
| Atributo HTML | `<input value="VALOR">` | Escape de atributo e aspas |
| URL | `<a href="VALOR">` | Validar protocolo e construir a URL com API segura |
| JavaScript | `<script>const x = 'VALOR'</script>` | Evitar interpolação; usar serialização segura |
| CSS | `<style>...</style>` | Evitar dados livres e usar valores permitidos |
| DOM | `element.innerHTML = valor` | Usar `textContent` ou sanitizar HTML |

Um valor escapado para HTML pode continuar perigoso se for inserido dentro de
JavaScript ou usado como URL. A defesa precisa ser adequada ao interpretador
que receberá o dado.

### URLs também podem ser perigosas

Escapar aspas não torna toda URL segura. A aplicação também deve aceitar
somente protocolos esperados, normalmente `https` e, quando necessário,
`http`.

Não se deve confiar apenas no fato de a string estar corretamente codificada.
A validação precisa impedir esquemas e destinos não permitidos pela regra de
negócio.

### Regras gerais, independentemente da linguagem

1. Trate toda entrada externa como não confiável.
2. Preserve o autoescape dos templates.
3. Evite funções que marcam conteúdo como seguro ou HTML bruto.
4. Use codificação de saída específica para o contexto.
5. Use `textContent` quando o objetivo for mostrar texto.
6. Sanitização é necessária quando HTML criado pelo usuário for um requisito.
7. Valide URLs e protocolos permitidos.
8. Use CSP como segunda barreira, não como substituta do escape.
9. Proteja cookies de sessão com `HttpOnly`, `Secure` e `SameSite` apropriado.
10. Revogue sessões comprometidas; corrigir o template não invalida tokens já
    roubados.
11. Teste tanto o servidor quanto o comportamento real no navegador.
12. Não confunda consultas parametrizadas com proteção contra XSS.

Em qualquer linguagem, a pergunta principal é:

> Este valor será exibido como texto ou será interpretado como código pelo
> navegador?
