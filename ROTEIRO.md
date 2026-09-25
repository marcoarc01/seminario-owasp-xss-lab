# ROTEIRO — Mural do Campus (20 minutos, 3 integrantes)

> **Nota de duração.** O PDF original do trabalho previa **40 minutos**. Esta
> versão foi planejada para **20 minutos**, preservando os requisitos técnicos
> (comentários sem higienização, fadiga de alerta, XSS persistente com captura
> via `document.cookie`, recepção visível no terminal, remediação com escape,
> CSP e proteção de cookies, e consultas parametrizadas). A adaptação de tempo
> foi feita por nós; este documento **não** afirma aprovação do professor —
> registra apenas a diferença de duração para transparência.

**Divisão:** Integrante 1 — Contexto/UX (5 min) · Integrante 2 — Demonstração
(8 min) · Integrante 3 — Correção/Reteste/Conclusão (7 min).

**Preparação (antes de começar, com a tela já no projetor):**

- Terminal 1: `python run_collector.py` (deixe visível).
- Terminal 2: `python run_portal.py` (modo vulnerável).
- Navegador **A (vítima)**: logado como `aluno`.
- Navegador/perfil **B (atacante)**: logado como `atacante`.
- DBeaver aberto em `instance/mural.db`, com `consultas_dbeaver.sql` carregado.
- Rode `python reset.py` uma vez para começar limpo (e faça login de novo).
- Abra `http://127.0.0.1:9000/health` uma vez para provar que o coletor está no ar.

---

## Parte 1 — Integrante 1 — Contexto e UX (5 min)

**Objetivo:** situar o problema e mostrar a aplicação.

**Fala de apoio:**

> "Nosso tema é **XSS persistente**: quando um site guarda um comentário e
> depois o exibe **sem tratar**, o navegador de quem abre a página pode acabar
> **executando** aquele conteúdo como código. Montamos um mural de campus
> local, só no nosso computador, com contas fictícias, para mostrar isso e
> depois corrigir."

**O que mostrar (2–3 min):**

1. Abra `http://localhost:5000` no navegador da **vítima**. Faça o login.
2. Mostre o **mural vazio** e crie ao vivo duas páginas: **"Teste do alerta"**
   e **"Teste da captura"**. Abra a primeira e publique um comentário normal.
3. Mostre **"Minha conta"**: nome, matrícula, curso e o **recado privado**.
   *"Guardem esse recado privado: é o dado sensível que vamos ver 'vazar'."*

**UX / fadiga de alerta (1–2 min):**

4. Aponte o **aviso repetitivo** ("Entendi") que reaparece ao entrar no mural e
   ao abrir publicações. *"Esse aviso repetido cansa o usuário — é a **fadiga de
   alerta**. As pessoas clicam em 'Entendi' no automático."*
5. **Ponto técnico importante:** *"A fadiga de alerta **não** é necessária para
   o ataque funcionar. Ela é só comportamento de interface. A causa técnica do
   XSS é o comentário ser **interpretado como código** — é isso que vamos ver."*

**Resultado esperado:** plateia entende o cenário, a conta da vítima e que o
aviso repetitivo é UX, não a causa do XSS.

---

## Parte 2 — Integrante 2 — Demonstração (8 min)

**Objetivo:** provar o XSS, mostrar o dado salvo, capturar a sessão e reutilizá-la.

### 2A. Prova inicial (≈2 min)

1. Vítima → página **"Teste do alerta"** → comentário
   `<script>alert(1)</script>` → **Publicar**.
2. **Resultado esperado:** aparece **`alert(1)`**. *"O comentário virou código."*
3. **DBeaver:** rode a consulta 5 (`WHERE conteudo LIKE '%<script%'`).
   *"O texto está salvo **igual** ao digitado — o problema não é o banco, é a
   exibição."*
4. Abra a **mesma** publicação no navegador **atacante** → alerta dispara.
   **Atualize** → dispara de novo. *"É **persistente**: veio do banco."*

### 2B. Captura da sessão (≈3 min)

5. Na página **"Teste da captura"**, cole o payload de
   captura (`payloads/2_captura_sessao.txt`) → **Publicar**.
   *"Esse script lê **só** o cookie `campus_session` e manda para o nosso
   coletor local. Nada de senha, nada de outros cookies."*
6. Faça a **vítima** abrir essa publicação.
7. **Resultado esperado:** no **Terminal 1** aparece o bloco **`[CAPTURA]`** com
   horário, origem e o **token**. *"Essa é a evidência principal: o token da
   sessão chegou ao atacante."*
8. (Opcional) Abra `http://127.0.0.1:9000` e mostre a captura com **Copiar token**.

### 2C. Reutilização da sessão (≈3 min)

9. No navegador **atacante**, abra **"Minha conta"** → mostra o **Beto (atacante)**.
10. **DevTools** na aba do **PORTAL** (`http://localhost:5000`): **Application →
    Cookies → `http://localhost:5000`**. Substitua o cookie:
    - **Name** `campus_session` · **Value** *(token copiado)* · **Domain**
      `localhost` · **Path** `/`.
11. Recarregue **"Minha conta"**.
12. **Resultado esperado:** aparece a **identidade e o recado privado da
    VÍTIMA** — sem a senha dela. *"O atacante entrou como a vítima **dentro da
    própria aplicação**, reusando a sessão roubada."*

> **Cuidado (dizer baixo para a equipe):** **não** deslogar a vítima entre a
> captura e a reutilização — o logout revoga a sessão e o token para de valer.

**Resultado esperado da Parte 2:** alerta + persistência, token no terminal,
e o atacante lendo o recado privado da vítima.

---

## Parte 3 — Integrante 3 — Correção, reteste e conclusão (7 min)

**Objetivo:** corrigir ao vivo e provar que o ataque não funciona mais.

### 3A. Correção principal — escape (≈2 min)

1. Abra `portal/templates/publicacao.html`. Mostre a linha comentada que
   **marca a vulnerabilidade**. Troque:
   `{{ comentario.conteudo | safe }}` → `{{ comentario.conteudo }}`. Salve.
2. Recarregue a publicação do alerta.
   **Resultado esperado:** o `<script>` aparece como **texto**, **sem** alerta.
   O comentário **continua** no banco. *"Não apagamos nada, não usamos regex —
   só passamos a tratar o comentário como **texto**."*

### 3B. Cookie HttpOnly + CSP (≈2–3 min)

3. Pare o portal e suba no **modo corrigido**
   (`LAB_MODE=corrigido python run_portal.py`). **Faça login de novo**
   (o cookie precisa ser reemitido).
4. **DevTools → Cookies:** `campus_session` agora tem **`HttpOnly ✓`**. No
   console, `document.cookie` **não** mostra o cookie.
   *"Agora o JavaScript não consegue **ler** o cookie."*
5. **CSP isolada (opcional, se der tempo):** com o template ainda `|safe` e o
   modo corrigido, um `<script>` injetado **não executa** — a **CSP** bloqueia,
   e o **console** mostra "Refused to execute inline script". *"A CSP é uma
   **camada extra**: mesmo se o escape falhasse, ela barraria o script inline."*

### 3C. Reteste e limites (≈2 min)

6. **Verificação de saúde do coletor** antes: mostre a linha `[saude]` (ou abra
   `/health`). *"Se agora o terminal ficar **vazio**, é porque a defesa
   funcionou — não porque o coletor caiu."*
7. Refaça a captura no modo corrigido: **nenhum** bloco `[CAPTURA]` novo.
8. **Limites honestos (falar):**
   - *"HttpOnly impede **ler** o cookie, mas não impede o XSS de rodar nem
     todas as ações em nome do usuário."*
   - *"Ligar HttpOnly/CSP **não** invalida um token já roubado — por isso a
     resposta a uma sessão comprometida inclui **revogar** as sessões."*
   - *"Consultas parametrizadas (que usamos em todo o código) previnem **SQL
     injection**, não XSS — são problemas diferentes."*

**Conclusão (30 s):** *"A causa raiz do Stored XSS é **misturar dados com
código** na saída. A correção certa é **escapar** no contexto certo; CSP e
cookie protegido são **camadas** adicionais. Referências: OWASP Top 10:2025
A05 Injection (inclui XSS) e o Cheat Sheet de XSS da OWASP."*

---

## Ensaio (checklist rápido)

- [ ] Cada integrante rodou a sua parte **do início ao fim** pelo menos uma vez.
- [ ] `reset.py` + login novo antes de apresentar.
- [ ] Payloads já copiados para um bloco de notas (para colar rápido).
- [ ] Coletor visível e testado com `/health`.
- [ ] Dois navegadores/perfis realmente separados (cookies não se misturam).
- [ ] DBeaver conectado e **sem transação aberta** (evita travar o SQLite).
- [ ] Zoom do navegador e do terminal aumentado para o projetor.

## Plano de recuperação (se algo falhar ao vivo)

- **O alerta não dispara:** confirme **modo vulnerável**, acesso por
  **`localhost`**, e que o template está com `|safe`. Se editou por engano,
  restaure com `patch -p1 -R < patches/remediation.diff` ou copie de volta.
- **A captura não chega:** verifique o coletor (`/health`), o console do
  navegador, e se acessou por `localhost` (não `127.0.0.1`).
- **Cookie/token não vale:** alguém deslogou a vítima ou a sessão expirou —
  `reset.py`, login novo e recapture.
- **Travou de vez:** tenha o **modo corrigido pronto** e mostre a **parte da
  defesa** com o reteste — a apresentação continua fazendo sentido.
- **Porta ocupada:** feche o processo antigo (Terminal) ou reinicie; no macOS,
  desligue o Receptor AirPlay (usa a 5000).
