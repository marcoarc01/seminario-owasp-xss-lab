# Payloads do laboratório (uso local e didático)

Estes exemplos só fazem sentido dentro deste laboratório, em `localhost`.
Eles não têm destino configurável para terceiros, não coletam senhas e não
usam ofuscação. Cole-os no campo **Novo comentário** de uma publicação
enquanto o portal estiver no **modo vulnerável**.

## 1. Prova inicial — `1_prova_alert.txt`

```html
<script>alert(1)</script>
```

Prova que o comentário é interpretado como código: ao abrir a publicação,
o navegador executa `alert(1)`. Use uma publicação **separada** da captura,
para o alerta não atrapalhar a etapa seguinte (o `alert` trava a página até
você clicar em OK).

## 2. Captura da sessão — `2_captura_sessao.txt`

Lê **apenas** `campus_session` de `document.cookie` e envia esse valor ao
coletor fixo em `http://127.0.0.1:9000/collect`, por uma requisição simples
(`mode:'no-cors'`, `credentials:'omit'`). Não lê a resposta, não manda outros
cookies e não usa CORS com credenciais.

Detalhes técnicos que fazem a captura funcionar com as regras reais do navegador:

- **Requisição simples**: `POST` com `Content-Type: application/x-www-form-urlencoded`
  é uma requisição "simples" de CORS — não dispara *preflight* e é enviada mesmo
  sem o coletor devolver cabeçalhos CORS.
- **`mode:'no-cors'`**: não precisamos ler a resposta; só queremos que o pedido
  chegue. Por isso o coletor não libera CORS globalmente.
- **`credentials:'omit'`**: não anexa cookies do coletor. O que chega ao coletor
  é só o valor que o payload leu e mandou de propósito.
- **Isolamento de host**: o portal é servido em `localhost` e o coletor em
  `127.0.0.1`. São hosts diferentes; o navegador **não** manda o cookie do
  portal para o coletor sozinho. Só o payload envia.

> Por que a captura só funciona no modo vulnerável? Porque ela depende de duas
> coisas: (a) o comentário ser interpretado como código (falta de escape) e
> (b) o cookie ser legível por JavaScript (sem `HttpOnly`). No modo corrigido,
> o escape já impede (a); e mesmo que o escape falhasse, a CSP `script-src 'self'`
> bloquearia o `<script>` inline, e o `HttpOnly` esconderia o cookie de
> `document.cookie`.
