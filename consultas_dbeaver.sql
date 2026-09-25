-- =====================================================================
-- Consultas prontas para o DBeaver — Mural do Campus
-- Banco: instance/mural.db  (SQLite)
-- Abra o arquivo no DBeaver: New Database Connection -> SQLite -> Path.
-- =====================================================================

-- 1) Ver o esquema (todas as tabelas e como foram criadas)
SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name;

-- 2) Contas fictícias, inclusive as criadas no cadastro
--    (repare: só há hash de senha, nunca a senha em texto)
SELECT id, usuario, nome, matricula, curso, senha_hash FROM usuarios;

-- 3) Publicações do mural
SELECT id, titulo, autor, criado_em FROM publicacoes ORDER BY id;

-- 4) TODOS os comentários, com o texto ORIGINAL preservado.
--    É aqui que o <script> aparece salvo exatamente como foi enviado.
SELECT id, publicacao_id, autor, conteudo, criado_em
FROM comentarios
ORDER BY id;

-- 5) Localizar comentários que contêm um <script> (o payload do XSS)
SELECT id, publicacao_id, autor, conteudo
FROM comentarios
WHERE conteudo LIKE '%<script%'
ORDER BY id;

-- 6) Comentários de uma publicação específica (ex.: publicação 1)
SELECT id, autor, conteudo, criado_em
FROM comentarios
WHERE publicacao_id = 1
ORDER BY id;

-- 7) Sessões: repare que guardamos apenas o HASH do token, nunca o token.
--    Ou seja, o banco NÃO entrega a sessão da vítima — o cookie é a única
--    prova de posse do token. (revogada: 0 = válida, 1 = revogada)
SELECT id, usuario_id, token_hash, criado_em, expira_em, revogada
FROM sessoes
ORDER BY id DESC;

-- 8) Sessões válidas agora (não revogadas e não expiradas)
SELECT s.id, u.usuario, s.criado_em, s.expira_em
FROM sessoes s
JOIN usuarios u ON u.id = s.usuario_id
WHERE s.revogada = 0
  AND s.expira_em > strftime('%Y-%m-%d %H:%M:%S', 'now')
ORDER BY s.id DESC;

-- Observação: NÃO use o banco como atalho para "pegar a sessão da vítima".
-- O objetivo do laboratório é mostrar a captura pelo XSS no navegador. A
-- tabela sessoes existe para explicar o modelo (hash do token, expiração,
-- revogação), não para contornar a demonstração.
