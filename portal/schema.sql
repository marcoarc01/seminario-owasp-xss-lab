-- =====================================================================
-- Mural do Campus — esquema do banco (SQLite)
-- Arquivo físico documentado: instance/mural.db  (abra no DBeaver)
--
-- Quatro tabelas com nomes claros: usuarios, publicacoes, comentarios,
-- sessoes. Toda a aplicação usa consultas parametrizadas (placeholders "?"),
-- tanto na versão vulnerável quanto na corrigida. O laboratório é de XSS,
-- portanto NÃO introduzimos SQL injection em lugar nenhum.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- usuarios: contas fictícias de demonstração.
-- A senha é guardada apenas como hash (werkzeug / scrypt), nunca em texto.
-- "recado_privado" é o dado fictício e sensível que a vítima vê em
-- "Minha conta" e que o atacante consegue ler ao reutilizar a sessão.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario        TEXT    NOT NULL UNIQUE,
    senha_hash     TEXT    NOT NULL,
    nome           TEXT    NOT NULL,
    matricula      TEXT    NOT NULL,
    curso          TEXT    NOT NULL,
    recado_privado TEXT    NOT NULL
);

-- ---------------------------------------------------------------------
-- publicacoes: o mural compartilhado entre as contas.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publicacoes (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo   TEXT    NOT NULL,
    corpo    TEXT    NOT NULL,
    autor    TEXT    NOT NULL,
    criado_em TEXT   NOT NULL
);

-- ---------------------------------------------------------------------
-- comentarios: guardamos o texto ORIGINAL, sem modificação.
-- Se alguém publicar <script>...</script>, o script fica salvo aqui
-- exatamente como foi enviado, para inspeção no DBeaver.
-- A vulnerabilidade NÃO está no banco: está em como o template renderiza
-- este texto. O escape correto acontece na exibição, não no armazenamento.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comentarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    publicacao_id INTEGER NOT NULL,
    autor        TEXT    NOT NULL,
    conteudo     TEXT    NOT NULL,   -- texto original, preservado
    criado_em    TEXT    NOT NULL,
    FOREIGN KEY (publicacao_id) REFERENCES publicacoes(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- sessoes: sessão OPACA. O cookie campus_session carrega um token
-- aleatório imprevisível. Aqui guardamos apenas o HASH desse token
-- (sha-256), nunca o token em si e nunca a senha. Assim, ler esta tabela
-- no DBeaver NÃO entrega a sessão da vítima — o cookie continua sendo a
-- única forma de provar posse do token.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash  TEXT    NOT NULL UNIQUE,  -- sha256(token), não o token
    usuario_id  INTEGER NOT NULL,
    criado_em   TEXT    NOT NULL,
    expira_em   TEXT    NOT NULL,
    revogada    INTEGER NOT NULL DEFAULT 0,  -- 0 = válida, 1 = revogada
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comentarios_pub ON comentarios(publicacao_id);
CREATE INDEX IF NOT EXISTS idx_sessoes_hash    ON sessoes(token_hash);
