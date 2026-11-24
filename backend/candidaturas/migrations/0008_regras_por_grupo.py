"""Regras da lista de candidaturas na base de dados, por grupo (docs/03_modelo_de_dados.md, secção 5.2).

R4: cada aluno só está num grupo de dois ativo por ano; um grupo individual fica ativo ao ser criado.
R8: quando uma candidatura sai da lista, as restantes do grupo sobem; se voltar, fica na última posição.
R9: validação de uma candidatura nova (fase, proposta, modalidade, candidatura repetida, limite e créditos).
P-03.3: quando o colega confirma a primeira candidatura, o grupo fica ativo.
P-03.4: função mover_candidatura para mudar a prioridade.
P-03.7: função selecionar_candidato (o orientador ou o proponente escolhe o candidato).
"""
from django.db import migrations

SQL = r"""
-- R4: grupos
CREATE OR REPLACE FUNCTION grupo_validar() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.colega_id IS NULL THEN
        NEW.estado := 'ATIVO';          -- grupo individual
        NEW.aceite_colega := true;
    END IF;
    IF NEW.colega_id IS NOT NULL AND NEW.estado = 'ATIVO' AND EXISTS (
        SELECT 1 FROM candidaturas_grupo g
         WHERE g.id <> NEW.id AND g.ano_letivo_id = NEW.ano_letivo_id
           AND g.estado = 'ATIVO' AND g.colega_id IS NOT NULL
           AND (g.submissor_id IN (NEW.submissor_id, NEW.colega_id)
                OR g.colega_id IN (NEW.submissor_id, NEW.colega_id))) THEN
        RAISE EXCEPTION 'Um dos alunos já pertence a outro grupo ativo neste ano letivo.';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER grupo_validar
BEFORE INSERT OR UPDATE ON candidaturas_grupo
FOR EACH ROW EXECUTE FUNCTION grupo_validar();

-- Lista de candidaturas do grupo: pendentes e ativas, numeradas de 1 a n
CREATE OR REPLACE FUNCTION renumerar_lista(p_grupo bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    -- 1.º passo: afastar as prioridades, para não violar o índice único durante a renumeração
    UPDATE candidaturas_candidatura SET prioridade = prioridade + 1000
     WHERE grupo_id = p_grupo AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA');
    -- 2.º passo: numerar de 1 a n, mantendo a ordem
    UPDATE candidaturas_candidatura c SET prioridade = l.nova
      FROM (SELECT id, row_number() OVER (ORDER BY prioridade, id) AS nova
              FROM candidaturas_candidatura
             WHERE grupo_id = p_grupo AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA')) l
     WHERE c.id = l.id;
END $$;

-- R9: validar uma candidatura nova
CREATE OR REPLACE FUNCTION candidatura_validar_nova() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_ano configuracao_anoletivo%ROWTYPE;
    v_prop propostas_proposta%ROWTYPE;
    v_grupo candidaturas_grupo%ROWTYPE;
    v_alunos bigint[];
    v_n int;
BEGIN
    SELECT * INTO v_ano FROM configuracao_anoletivo WHERE id = NEW.ano_letivo_id;
    SELECT * INTO v_prop FROM propostas_proposta WHERE id = NEW.proposta_id;
    SELECT * INTO v_grupo FROM candidaturas_grupo WHERE id = NEW.grupo_id;
    v_alunos := array_remove(ARRAY[v_grupo.submissor_id, v_grupo.colega_id], NULL);

    IF v_ano.estado <> 'ABERTO' THEN
        RAISE EXCEPTION 'O ano letivo % está fechado.', v_ano.designacao;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM configuracao_fase
                    WHERE ano_letivo_id = NEW.ano_letivo_id AND tipo = 'CANDIDATURAS'
                      AND now() BETWEEN data_inicio AND data_fim) THEN
        RAISE EXCEPTION 'A fase de candidaturas não está aberta.';
    END IF;
    IF v_grupo.estado IN ('RECUSADO', 'DISSOLVIDO') THEN
        RAISE EXCEPTION 'O grupo não está ativo.';
    END IF;
    IF v_prop.estado = 'PRE_ATRIBUIDA' THEN
        IF NOT EXISTS (SELECT 1 FROM propostas_propostaaluno
                        WHERE proposta_id = NEW.proposta_id AND aluno_id = ANY (v_alunos)) THEN
            RAISE EXCEPTION 'Este TFC está pré-atribuído a outro aluno.';
        END IF;
    ELSIF v_prop.estado <> 'DISPONIVEL' THEN
        RAISE EXCEPTION 'Este TFC não está disponível para candidatura.';
    END IF;
    IF v_grupo.colega_id IS NULL AND v_prop.modalidade = 'GRUPO' THEN
        RAISE EXCEPTION 'Este TFC é para grupos de 2 e não aceita candidaturas individuais.';
    END IF;
    IF v_grupo.colega_id IS NOT NULL AND v_prop.modalidade = 'INDIVIDUAL' THEN
        RAISE EXCEPTION 'Este TFC é individual e não aceita grupos.';
    END IF;

    -- R1: nenhum dos alunos pode ter já uma candidatura a este TFC, neste ou noutro grupo
    IF EXISTS (SELECT 1 FROM candidaturas_candidatura c
                 JOIN candidaturas_grupo g ON g.id = c.grupo_id
                WHERE c.proposta_id = NEW.proposta_id
                  AND c.estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA')
                  AND (g.submissor_id = ANY (v_alunos) OR g.colega_id = ANY (v_alunos))) THEN
        RAISE EXCEPTION 'Já existe uma candidatura a este TFC.';
    END IF;

    SELECT count(*) INTO v_n FROM candidaturas_candidatura
     WHERE grupo_id = NEW.grupo_id AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA');
    IF v_n >= v_ano.max_candidaturas THEN
        RAISE EXCEPTION 'Atingiu o limite de % candidaturas. Retire uma candidatura de outro TFC.', v_ano.max_candidaturas;
    END IF;

    -- Créditos de todos os alunos do grupo
    IF EXISTS (SELECT a FROM unnest(v_alunos) a
                WHERE NOT EXISTS (SELECT 1 FROM configuracao_inscricaotfc i
                                   WHERE i.aluno_id = a AND i.ano_letivo_id = NEW.ano_letivo_id AND i.elegivel)) THEN
        NEW.estado := 'RECUSADA';
        NEW.motivo_fim := 'SEM_CREDITOS';
        NEW.prioridade := NULL;
        RETURN NEW;
    END IF;

    -- Individual: ativa. Em grupo: o colega confirma cada candidatura (P-03.3).
    NEW.estado := CASE WHEN v_grupo.colega_id IS NULL THEN 'ATIVA' ELSE 'PENDENTE_CONFIRMACAO' END;
    NEW.motivo_fim := '';
    NEW.prioridade := v_n + 1;  -- última posição da lista
    RETURN NEW;
END $$;

CREATE TRIGGER candidatura_validar_nova
BEFORE INSERT ON candidaturas_candidatura
FOR EACH ROW EXECUTE FUNCTION candidatura_validar_nova();

-- R8: a candidatura sai da lista → perde a prioridade e a lista é renumerada
CREATE OR REPLACE FUNCTION candidatura_antes_de_sair() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.prioridade := NULL;
    RETURN NEW;
END $$;

CREATE TRIGGER candidatura_antes_de_sair
BEFORE UPDATE OF estado ON candidaturas_candidatura
FOR EACH ROW
WHEN (OLD.estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA') AND NEW.estado NOT IN ('PENDENTE_CONFIRMACAO', 'ATIVA'))
EXECUTE FUNCTION candidatura_antes_de_sair();

CREATE OR REPLACE FUNCTION candidatura_depois_de_sair() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM renumerar_lista(NEW.grupo_id);
    RETURN NULL;
END $$;

CREATE TRIGGER candidatura_depois_de_sair
AFTER UPDATE OF estado ON candidaturas_candidatura
FOR EACH ROW
WHEN (OLD.estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA') AND NEW.estado NOT IN ('PENDENTE_CONFIRMACAO', 'ATIVA'))
EXECUTE FUNCTION candidatura_depois_de_sair();

-- R8 (complemento): uma candidatura que volta à lista fica na última posição
CREATE OR REPLACE FUNCTION candidatura_regressa_a_lista() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_max int;
    v_n int;
BEGIN
    SELECT max_candidaturas INTO v_max FROM configuracao_anoletivo WHERE id = NEW.ano_letivo_id;
    SELECT count(*) INTO v_n FROM candidaturas_candidatura
     WHERE id <> NEW.id AND grupo_id = NEW.grupo_id AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA');
    IF v_n >= v_max THEN
        RAISE EXCEPTION 'Atingiu o limite de % candidaturas. Retire uma candidatura de outro TFC.', v_max;
    END IF;
    NEW.prioridade := v_n + 1;
    NEW.motivo_fim := '';
    RETURN NEW;
END $$;

CREATE TRIGGER candidatura_regressa_a_lista
BEFORE UPDATE OF estado ON candidaturas_candidatura
FOR EACH ROW
WHEN (OLD.estado NOT IN ('PENDENTE_CONFIRMACAO', 'ATIVA') AND NEW.estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA'))
EXECUTE FUNCTION candidatura_regressa_a_lista();

-- P-03.3: o colega confirma a primeira candidatura → o grupo fica ativo (e R4 é verificado)
CREATE OR REPLACE FUNCTION candidatura_confirmada() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE candidaturas_grupo SET estado = 'ATIVO', aceite_colega = true
     WHERE id = NEW.grupo_id AND estado = 'PENDENTE';
    RETURN NULL;
END $$;

CREATE TRIGGER candidatura_confirmada
AFTER UPDATE OF estado ON candidaturas_candidatura
FOR EACH ROW
WHEN (OLD.estado = 'PENDENTE_CONFIRMACAO' AND NEW.estado = 'ATIVA')
EXECUTE FUNCTION candidatura_confirmada();

-- R14 (parcial): histórico das mudanças de estado das candidaturas
CREATE OR REPLACE FUNCTION candidatura_historico() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO comum_historico (entidade, entidade_id, evento, campo, valor_anterior, valor_novo, data, motivo)
    VALUES ('Candidatura', NEW.id, 'mudança de estado', 'estado', OLD.estado, NEW.estado, now(), NEW.motivo_fim);
    RETURN NULL;
END $$;

CREATE TRIGGER candidatura_historico
AFTER UPDATE OF estado ON candidaturas_candidatura
FOR EACH ROW WHEN (OLD.estado IS DISTINCT FROM NEW.estado)
EXECUTE FUNCTION candidatura_historico();

-- P-03.4: mudar a prioridade de uma candidatura (as outras do grupo ajustam-se)
CREATE OR REPLACE FUNCTION mover_candidatura(p_id bigint, p_nova int)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    c candidaturas_candidatura%ROWTYPE;
    v_n int;
BEGIN
    SELECT * INTO c FROM candidaturas_candidatura WHERE id = p_id FOR UPDATE;
    IF c.estado NOT IN ('PENDENTE_CONFIRMACAO', 'ATIVA') THEN
        RAISE EXCEPTION 'A candidatura não está na lista.';
    END IF;
    SELECT count(*) INTO v_n FROM candidaturas_candidatura
     WHERE grupo_id = c.grupo_id AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA');
    p_nova := greatest(1, least(p_nova, v_n));
    IF p_nova = c.prioridade THEN RETURN; END IF;

    UPDATE candidaturas_candidatura SET prioridade = prioridade + 1000
     WHERE grupo_id = c.grupo_id AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA');
    UPDATE candidaturas_candidatura SET prioridade = CASE
            WHEN id = p_id THEN p_nova
            WHEN prioridade - 1000 > c.prioridade AND prioridade - 1000 <= p_nova THEN prioridade - 1001
            WHEN prioridade - 1000 < c.prioridade AND prioridade - 1000 >= p_nova THEN prioridade - 999
            ELSE prioridade - 1000 END
     WHERE grupo_id = c.grupo_id AND prioridade > 1000 AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA');
END $$;

-- P-03.7: o orientador ou o proponente seleciona o candidato de uma proposta (pode mudar até à confirmação)
CREATE OR REPLACE FUNCTION selecionar_candidato(p_candidatura bigint, p_utilizador bigint)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
    c candidaturas_candidatura%ROWTYPE;
    v_id bigint;
BEGIN
    SELECT * INTO c FROM candidaturas_candidatura WHERE id = p_candidatura FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Candidatura % não existe.', p_candidatura;
    END IF;
    IF c.estado <> 'ATIVA' THEN
        RAISE EXCEPTION 'Só uma candidatura ativa pode ser selecionada (estado atual: %).', c.estado;
    END IF;
    IF EXISTS (SELECT 1 FROM candidaturas_selecao WHERE proposta_id = c.proposta_id AND confirmada) THEN
        RAISE EXCEPTION 'A seleção deste TFC já foi confirmada pela coordenação.';
    END IF;
    -- desfaz uma seleção anterior ainda não confirmada
    UPDATE candidaturas_selecao SET selecionada = false
     WHERE proposta_id = c.proposta_id AND selecionada AND candidatura_id <> c.id;
    INSERT INTO candidaturas_selecao (proposta_id, candidatura_id, selecionada, selecionada_por_id, data_selecao,
                                      justificacao_ajuste, confirmada)
    VALUES (c.proposta_id, c.id, true, p_utilizador, now(), '', false)
    ON CONFLICT (candidatura_id) DO UPDATE
       SET selecionada = true, selecionada_por_id = EXCLUDED.selecionada_por_id, data_selecao = now()
    RETURNING id INTO v_id;
    RETURN v_id;
END $$;
"""

REVERSE = r"""
DROP FUNCTION IF EXISTS selecionar_candidato(bigint, bigint);
DROP TRIGGER IF EXISTS candidatura_historico ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_confirmada ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_regressa_a_lista ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_depois_de_sair ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_antes_de_sair ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS candidatura_validar_nova ON candidaturas_candidatura;
DROP TRIGGER IF EXISTS grupo_validar ON candidaturas_grupo;
DROP FUNCTION IF EXISTS mover_candidatura(bigint, int);
DROP FUNCTION IF EXISTS candidatura_historico();
DROP FUNCTION IF EXISTS candidatura_confirmada();
DROP FUNCTION IF EXISTS candidatura_regressa_a_lista();
DROP FUNCTION IF EXISTS candidatura_depois_de_sair();
DROP FUNCTION IF EXISTS candidatura_antes_de_sair();
DROP FUNCTION IF EXISTS candidatura_validar_nova();
DROP FUNCTION IF EXISTS renumerar_lista(bigint);
DROP FUNCTION IF EXISTS grupo_validar();
"""


class Migration(migrations.Migration):
    dependencies = [("candidaturas", "0007_candidatura_por_grupo")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
