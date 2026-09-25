# Mural do Campus — laboratório local de XSS persistente (Stored XSS)

Laboratório acadêmico **local e autorizado** para uma apresentação de
cibersegurança. Demonstra como um comentário armazenado sem higienização pode
executar JavaScript no navegador de **outra** conta de teste, capturar uma
**sessão fictícia** e permitir acesso indevido **dentro da própria aplicação
de teste** — e depois mostra como **corrigir** o problema (escape, CSP, cookie
protegido) e repetir os testes.

> **Limites deste laboratório (existem no código, não só no aviso).** Tudo roda
> em **uma máquina**, vinculado **somente ao loopback**. O portal valida o host
> esperado e recusa outros; nenhum serviço escuta em `0.0.0.0`. O payload de
> captura só envia **um** cookie (`campus_session`) ao **coletor local fixo**
> (`127.0.0.1:9000`), sem destino configurável para terceiros, sem coletar
> senhas, sem ofuscação. Todas as contas, senhas, mensagens e tokens são
> **fictícios**, criados para a demonstração. Não há alvos externos, coleta de
> contas reais nem publicação na internet.

---

## 1. Componentes

- **Portal "Mural do Campus"** — `http://localhost:5000` (Flask + Jinja + SQLite).
  Login, mural compartilhado, página de publicação com comentários, e "Minha
  conta" (protegida) com um recado privado por conta.
- **Coletor (receptor do atacante)** — `http://127.0.0.1:9000`. Programa
  **separado**, sem acesso ao banco do portal. Mostra as capturas no
  **terminal** (evidência principal) e tem uma página opcional com tabela e
  botão "Copiar token".

O portal usa o host **`localhost`** e o coletor usa **`127.0.0.1`** de
propósito: são **hosts diferentes**. Portas diferentes **não** isolam cookies,
mas hosts diferentes **sim** — por isso o coletor **não** recebe o cookie do
portal automaticamente.

---

## 2. Requisitos

- **Python 3.10+** (testado em 3.11).
- Um navegador moderno (Chrome, Edge ou Firefox).
- **Dois navegadores ou dois perfis independentes** (ex.: uma janela normal e
  uma janela anônima, ou dois perfis do Chrome) — um para a **vítima**, outro
  para o **atacante**. Isso mantém cookies separados.
- Depois de instalar as dependências, a apresentação funciona **sem internet**
  (sem CDN, sem fontes externas).
- **Não** são necessários Docker, Kali nem máquina virtual.

---

## 3. Instalação (com ambiente virtual)

Abra um terminal na pasta do projeto (onde está este `README.md`).

### Windows / PowerShell

```powershell
cd "C:\Users\Pedro\Desktop\seminario-owasp-xss-lab"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o PowerShell bloquear a ativação ("execution of scripts is disabled"),
> rode uma vez:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ative de novo.

### macOS / Linux

```bash
cd "/caminho/para/seminario-owasp-xss-lab"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O banco `instance/mural.db` é criado e populado **automaticamente** no primeiro
início do portal. Para criar/recriar manualmente: `python reset.py`.
O banco e o ambiente `.venv` são locais e ignorados pelo Git.

---

## 4. Execução

Use **dois terminais** (os dois com o `.venv` ativado). O modo padrão é o
**vulnerável**.

**Terminal 1 — coletor:**

```bash
python run_collector.py
# recebendo em http://127.0.0.1:9000  (deixe este terminal à vista: é a evidência)
```

**Terminal 2 — portal (modo vulnerável):**

```bash
python run_portal.py
# abra no navegador: http://localhost:5000
```

Para rodar o portal no **modo corrigido**:

```powershell
# Windows/PowerShell
$env:LAB_MODE="corrigido"; python run_portal.py
```
```bash
# macOS/Linux
LAB_MODE=corrigido python run_portal.py
```

> **Sempre acesse o portal por `http://localhost:5000`** (não por `127.0.0.1`).
> Isso mantém o portal (`localhost`) e o coletor (`127.0.0.1`) em hosts
> diferentes, que é o que garante o isolamento de cookie demonstrado.

---

## 5. Contas de demonstração (fictícias)

| Papel     | Usuário    | Senha         | Nome fictício          |
|-----------|------------|---------------|------------------------|
| Vítima    | `aluno`    | `aluno123`    | Ana Vitima da Silva    |
| Atacante  | `atacante` | `atacante123` | Beto Atacap Souza      |

As senhas são gravadas **apenas como hash** (werkzeug/scrypt). A conta `aluno`
tem um **recado privado** que o atacante conseguirá ler ao reutilizar a sessão.

Para criar contas na hora da apresentação, abra `http://localhost:5000`,
clique em **Criar conta** na tela de login e preencha usuário, nome, matrícula,
curso, senha e, se quiser, um recado privado fictício. O cadastro salva a
conta em `instance/mural.db` e já entra nela. Para criar outra conta no mesmo
perfil, clique em **Sair** e volte a **Criar conta**. Use perfis de navegador
separados para manter as sessões da vítima e do atacante independentes.
O comando `python reset.py` apaga também as contas criadas manualmente.

---

## 6. Banco de dados e DBeaver

- Arquivo: **`instance/mural.db`** (SQLite), caminho fixo dentro do projeto.
- No DBeaver: **New Database Connection → SQLite →** aponte o *Path* para
  `instance/mural.db`.
- Tabelas: `usuarios`, `publicacoes`, `comentarios`, `sessoes`.
- Consultas prontas: veja **`consultas_dbeaver.sql`**. As principais:

```sql
-- comentários com o texto ORIGINAL (o <script> aparece salvo aqui)
SELECT id, publicacao_id, autor, conteudo, criado_em FROM comentarios ORDER BY id;

-- localizar o payload de XSS
SELECT id, autor, conteudo FROM comentarios WHERE conteudo LIKE '%<script%';

-- sessões: só o HASH do token é guardado (o banco NÃO entrega a sessão)
SELECT id, usuario_id, token_hash, expira_em, revogada FROM sessoes;
```

O comentário é **armazenado exatamente como enviado** — a vulnerabilidade está
em **como o template renderiza** esse texto, não no banco. As sessões guardam
só o **hash** do token, então ler o banco no DBeaver **não** dá a sessão da
vítima.

---

## 7. Demonstração completa

Prepare: coletor no Terminal 1; portal (modo vulnerável) no Terminal 2; um
navegador para a **vítima** (`aluno`) e outro navegador/perfil para o
**atacante** (`atacante`).

### A) Prova inicial — o comentário vira código

1. No navegador da **vítima**, entre como `aluno` e abra a publicação
   **"Grupo de estudos de Algoritmos"**.
2. No campo **Novo comentário**, cole (arquivo `payloads/1_prova_alert.txt`):
   `<script>alert(1)</script>` e clique **Publicar**.
3. A página recarrega e aparece o **`alert(1)`**. Clique OK.
4. No **DBeaver**, rode a consulta 4/5 (acima): o texto do `<script>` está
   salvo **igual** ao que foi digitado.
5. Abra a **mesma publicação** no navegador do **atacante** (logado como
   `atacante`): o **alerta dispara também**. **Atualize** a página → dispara de
   novo: é **persistente** (veio do banco, não de um clique).

> Use a publicação do alerta **separada** da publicação da captura (a seguir),
> porque o `alert()` trava a página até você clicar OK.

### B) Captura real da sessão de laboratório

1. Ainda no **modo vulnerável**, abra **outra** publicação (ex.: **"Semana de
   Tecnologia"**).
2. Cole o payload de captura (arquivo `payloads/2_captura_sessao.txt`) e
   **Publicar**. Ele lê **apenas** `campus_session` de `document.cookie` e
   envia esse valor ao coletor (`127.0.0.1:9000`) por uma requisição simples.
3. Quando a **vítima** abrir essa publicação, olhe o **Terminal 1**: aparece um
   bloco **`[CAPTURA]`** com horário, origem, o **token** e o total de capturas.
4. (Opcional) Abra `http://127.0.0.1:9000` — a **página do atacante** lista a
   captura com um botão **Copiar token**.

Por que funciona com as regras reais do navegador: a requisição é "simples"
(`POST` `application/x-www-form-urlencoded`, `mode:'no-cors'`,
`credentials:'omit'`), então é enviada sem *preflight* e sem precisar ler a
resposta — sem liberar CORS com credenciais.

### C) Reutilização da sessão (acesso indevido dentro da aplicação)

1. No navegador do **atacante**, abra **"Minha conta"**. Você vê a identidade
   do **atacante** (ou é mandado ao login, se não estiver logado).
2. Copie o token realmente recebido (botão **Copiar token** no coletor, ou o
   bloco `[CAPTURA]` do terminal).
3. Abra o **DevTools** no navegador do **atacante**, na aba do **PORTAL**
   (`http://localhost:5000`): **Application → Storage → Cookies →
   `http://localhost:5000`**. Edite/crie o cookie:
   - **Name:** `campus_session`
   - **Value:** *(cole o token capturado)*
   - **Domain:** `localhost`
   - **Path:** `/`
   - deixe `HttpOnly`/`Secure` como estão (no modo vulnerável, sem HttpOnly).
4. Recarregue **"Minha conta"**: agora aparece o **nome, matrícula, curso e o
   recado privado da VÍTIMA** — sem nunca ter a senha dela.

> **Não faça logout da vítima** entre a captura e a reutilização: o logout
> **revoga** a sessão no servidor e o token deixa de valer.
>
> Repare no que **não** existe: não há rota de "login por id", não há
> "importar sessão", não há backdoor. A aplicação do cookie é **manual**, no
> host do portal. O coletor, em outro host, **não** consegue definir o cookie
> do portal — só o apresentador, manualmente, no DevTools do portal.

---

## 8. Correção ao vivo e reteste

Detalhes e trechos de código em **`patches/README.md`**. Resumo:

1. **Escape (correção principal):** em `portal/templates/publicacao.html`,
   troque `{{ comentario.conteudo | safe }}` por `{{ comentario.conteudo }}`.
   Salve (o Flask recarrega). O comentário antigo agora aparece como **texto**,
   sem alerta e sem nova captura. O texto continua no banco.
   - Alternativa: `patch -p1 < patches/remediation.diff` (reverter com `-R`),
     ou copiar `patches/secure/publicacao.html` sobre o template.
2. **Cookie HttpOnly:** rode em `LAB_MODE=corrigido` e **faça login de novo**
   (o cookie precisa ser reemitido). No DevTools o cookie mostra `HttpOnly ✓`,
   e `document.cookie` não traz mais o `campus_session`.
3. **CSP:** no modo corrigido, o cabeçalho `Content-Security-Policy` é enviado
   com `script-src 'self'` (sem `unsafe-inline`). Um `<script>` inline injetado
   é **bloqueado**, com erro no console.
4. **SameSite/Secure:** explicados em `patches/README.md`. Há um **perfil HTTPS
   local opcional** (`PORTAL_HTTPS=1`, requer `pip install cryptography`) para
   verificar o atributo `Secure`, sem desabilitar TLS globalmente.
5. **UX:** no modo corrigido, o aviso repetitivo some e vira uma orientação
   discreta.

**Testar cada defesa isolada** (o laboratório permite isso de propósito):

- **Só o escape:** template corrigido + `LAB_MODE=vulneravel` → sem alerta,
  mesmo com cookie ainda legível.
- **Só a CSP:** template ainda com `|safe` + `LAB_MODE=corrigido` → o script
  cru **não executa** porque a CSP bloqueia (veja o console). Não confunda com
  a correção pelo escape.
- **Só o HttpOnly:** `LAB_MODE=corrigido`, login novo → `document.cookie` não
  mostra o cookie (mesmo que um script ainda executasse).

**Antes do reteste, faça uma verificação de saúde do coletor** (abra
`http://127.0.0.1:9000/health` ou veja a linha `[saude]` no terminal). Assim,
um terminal **vazio** no reteste significa **"a defesa funcionou"**, e não
"o coletor caiu".

### O que as defesas NÃO fazem (limites honestos)

- **HttpOnly** impede **ler** o cookie por JavaScript; **não** impede o XSS de
  executar nem todas as ações em nome do usuário.
- Ativar **HttpOnly/CSP não invalida** tokens já capturados antes: a resposta a
  uma sessão comprometida inclui **revogar** as sessões (logout / `reset.py`).
- **SameSite** não corrige XSS (o script roda na própria origem). **Secure** é
  sobre transporte (HTTPS), não sobre leitura no navegador.
- **Consultas parametrizadas** previnem **SQL injection**, não XSS.

---

## 9. Reset (para ensaiar de novo)

```bash
python reset.py
```

Recria **apenas** `instance/mural.db` (contas, publicações e comentários de
semente) e, ao recriar, **invalida todas as sessões antigas**. Não apaga nada
fora do projeto. Depois do reset, **faça login novamente**.

---

## 10. Solução de problemas

- **Porta ocupada (5000 ou 9000):** feche processos antigos do portal/coletor
  (outro terminal, ou reinicie a máquina). No macOS, o AirPlay pode usar a
  5000 — desligue "Receptor AirPlay" em Ajustes, ou mude a porta no código.
- **Host errado / "Host não esperado":** acesse **`http://localhost:5000`**
  (portal) e **`http://127.0.0.1:9000`** (coletor). O portal recusa outros
  hosts de propósito.
- **A captura não aparece:** confirme que o portal está em **modo vulnerável**,
  que você acessou por **`localhost`** (não `127.0.0.1`) e que o **coletor está
  no ar** (linha `[saude]` após abrir `/health`). Veja o console do navegador.
- **Cookie expirado / token não vale:** a sessão expira em 8h, e **logout** ou
  **reset** revogam. Faça **login de novo** e recapture.
- **Perfis/cookies compartilhados:** use **dois navegadores ou dois perfis**
  distintos para vítima e atacante; senão os cookies se misturam e a
  reutilização "parece" já estar logada.
- **CORS:** o payload usa `mode:'no-cors'` de propósito; **não** ative CORS com
  credenciais no coletor. Se você trocar para ler a resposta, aí sim esbarra em
  CORS — não é necessário para a demo.
- **CSP bloqueando algo no modo corrigido:** é esperado para scripts inline.
  Nossos scripts legítimos estão em arquivos próprios (`static/portal.js`), que
  a CSP permite. Não adicione `unsafe-inline`.
- **HttpOnly "não mudou":** você precisa **reemitir** o cookie — faça **login
  de novo** depois de entrar no modo corrigido.
- **Certificado (perfil HTTPS):** o `ssl_context="adhoc"` usa certificado
  self-signed; o navegador avisa. Aceite **só para este localhost**. Não
  desative a validação TLS global.
- **SQLite "database is locked" no DBeaver:** o DBeaver pode segurar uma
  transação. Faça **commit/rollback** na conexão do DBeaver (ou feche a
  conexão) antes de rodar o portal/`reset.py`. Evite manter uma transação
  aberta durante a demonstração.

---

## 11. Estrutura dos arquivos

```
seminario-owasp-xss-lab/
├── README.md                     # este arquivo
├── ROTEIRO.md                    # roteiro de 20 min para 3 apresentadores
├── requirements.txt
├── run_portal.py                 # inicia o portal (porta 5000, loopback)
├── run_collector.py              # inicia o coletor (porta 9000, loopback)
├── reset.py                      # recria o banco e invalida sessões
├── consultas_dbeaver.sql         # consultas SQL prontas
├── instance/
│   └── mural.db                  # SQLite local (criado no 1º início; ignorado pelo Git)
├── portal/
│   ├── app.py                    # rotas, emissão do cookie, CSP, validação de host
│   ├── config.py                 # modo do laboratório e postura de segurança
│   ├── auth.py                   # sessão opaca (token aleatório, só hash no banco)
│   ├── db.py                     # SQLite, consultas parametrizadas
│   ├── seed.py                   # dados fictícios
│   ├── schema.sql                # esquema (4 tabelas)
│   ├── templates/                # login, cadastro, mural, publicacao (|safe), conta, base
│   └── static/                   # portal.css, portal.js
├── collector/
│   ├── collector.py              # coletor separado (sem acesso ao banco do portal)
│   ├── templates/painel.html     # página do atacante (tudo escapado)
│   └── static/                   # painel.css, painel.js (botão copiar token)
├── payloads/
│   ├── 1_prova_alert.txt         # <script>alert(1)</script>
│   ├── 2_captura_sessao.txt      # payload de captura (só campus_session)
│   └── README.md
├── patches/
│   ├── remediation.diff          # diff aplicável do escape (|safe -> escapado)
│   ├── README.md                 # os 5 pontos de correção, com trechos de código
│   └── secure/publicacao.html    # cópia corrigida de apoio
└── tests/
    └── verificacao_navegador.py  # verificação em navegador real (Playwright)
```

---

## 12. Resultados reais das verificações

A verificação de navegador (`tests/verificacao_navegador.py`, Chromium via
Playwright) foi executada e passou **18/18** nesta implementação (ver
`ROTEIRO.md` e a mensagem de entrega). Ela cobre: alerta e persistência;
captura enviando só `campus_session` com o token igual ao cookie real da
vítima; coletor sem captura por mera visita; reutilização lendo a conta e o
recado privado da vítima; token inválido e revogado negados; isolamento de
host do cookie; escape parando alerta e captura sem apagar comentários;
HttpOnly escondendo o cookie de `document.cookie`; e CSP bloqueando script
inline com violação no console.

Para rodar você mesmo (com as portas 5000/9000 livres):

```bash
pip install playwright && python -m playwright install chromium
python -m tests.verificacao_navegador
```

---

## 13. Referências oficiais (verificadas em setembro/2026)

- OWASP Top 10:2025 — **A05:2025 Injection**, que **inclui XSS** (era
  **A03:2021 Injection** na edição de 2021):
  <https://owasp.org/Top10/2025/A05_2025-Injection/>
- OWASP — Cross Site Scripting Prevention Cheat Sheet:
  <https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html>
- OWASP — Content Security Policy Cheat Sheet:
  <https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html>
- Flask — Security Considerations:
  <https://flask.palletsprojects.com/en/stable/security/>
- Jinja — autoescaping e filtro `safe`:
  <https://jinja.palletsprojects.com/en/stable/templates/#working-with-automatic-escaping>
