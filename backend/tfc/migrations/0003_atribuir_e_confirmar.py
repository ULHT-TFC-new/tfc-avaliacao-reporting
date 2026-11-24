"""R7: atribuir um TFC numa só operação, agora a partir do grupo da candidatura (Reunião 8, 18/11).

atribuir_tfc desencadeia as restantes operações: a proposta passa a Atribuída, o TFC é criado com os alunos
do grupo, a candidatura passa a Contemplada, as outras candidaturas desses alunos e as dos outros candidatos
a este TFC são encerradas, e as listas afetadas são renumeradas (trigger R8).

confirmar_selecao: a coordenação confirma o candidato selecionado pelo orientador ou pelo proponente, o que
publica a atribuição (chama atribuir_tfc).
"""
from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION atribuir_tfc(p_candidatura bigint, p_orientador bigint, p_coorientador bigint DEFAULT NULL)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
    c candidaturas_candidatura%ROWTYPE;
    g candidaturas_grupo%ROWTYPE;
    v_prop propostas_proposta%ROWTYPE;
    v_alunos bigint[];
    v_tfc bigint;
BEGIN
    SELECT * INTO c FROM candidaturas_candidatura WHERE id = p_candidatura FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Candidatura % não existe.', p_candidatura;
    END IF;
    IF c.estado <> 'ATIVA' THEN
        RAISE EXCEPTION 'Só uma candidatura ativa pode ser contemplada (estado atual: %).', c.estado;
    END IF;
    SELECT * INTO v_prop FROM propostas_proposta WHERE id = c.proposta_id FOR UPDATE;
    IF v_prop.estado NOT IN ('DISPONIVEL', 'PRE_ATRIBUIDA') THEN
        RAISE EXCEPTION 'A proposta não pode ser atribuída (estado atual: %).', v_prop.estado;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM configuracao_docente WHERE id = p_orientador AND ativo) THEN
        RAISE EXCEPTION 'O orientador tem de ser um docente ativo.';
    END IF;

    SELECT * INTO g FROM candidaturas_grupo WHERE id = c.grupo_id;
    v_alunos := array_remove(ARRAY[g.submissor_id, g.colega_id], NULL);
    UPDATE candidaturas_grupo SET estado = 'ATIVO' WHERE id = g.id AND estado <> 'ATIVO';

    -- Proposta e TFC
    UPDATE propostas_proposta SET estado = 'ATRIBUIDA' WHERE id = v_prop.id;
    INSERT INTO tfc_tfc (proposta_id, ano_letivo_id, estado, orientador_id, coorientador_id,
                         repositorio_url, data_atribuicao, epoca_final)
    VALUES (v_prop.id, c.ano_letivo_id, 'EM_CURSO', p_orientador, p_coorientador, '', now(), 1)
    RETURNING id INTO v_tfc;
    INSERT INTO tfc_tfcaluno (tfc_id, aluno_id, ano_letivo_id, candidatura_id, ativo, data_entrada, motivo_saida)
    SELECT v_tfc, a, c.ano_letivo_id, CASE WHEN a = g.submissor_id THEN c.id END, true, current_date, ''
      FROM unnest(v_alunos) a;

    -- Candidaturas (cada mudança de estado dispara a renumeração das listas, R8)
    UPDATE candidaturas_candidatura SET estado = 'CONTEMPLADA', motivo_fim = '', data_estado = now()
     WHERE id = c.id;
    UPDATE candidaturas_candidatura SET estado = 'ENCERRADA', motivo_fim = 'ALUNO_CONTEMPLADO', data_estado = now()
     WHERE id <> c.id AND ano_letivo_id = c.ano_letivo_id
       AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA')
       AND grupo_id IN (SELECT id FROM candidaturas_grupo
                         WHERE submissor_id = ANY (v_alunos) OR colega_id = ANY (v_alunos));
    UPDATE candidaturas_candidatura SET estado = 'ENCERRADA', motivo_fim = 'TFC_ATRIBUIDO_A_OUTRO', data_estado = now()
     WHERE proposta_id = v_prop.id AND id <> c.id
       AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA');

    INSERT INTO comum_historico (entidade, entidade_id, evento, campo, valor_anterior, valor_novo, data, motivo)
    VALUES ('Proposta', v_prop.id, 'atribuir', 'estado', v_prop.estado, 'ATRIBUIDA', now(), '');

    RETURN v_tfc;
END $$;

CREATE OR REPLACE FUNCTION confirmar_selecao(p_selecao bigint, p_orientador bigint,
                                             p_coorientador bigint DEFAULT NULL, p_utilizador bigint DEFAULT NULL)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
    s candidaturas_selecao%ROWTYPE;
    v_tfc bigint;
BEGIN
    SELECT * INTO s FROM candidaturas_selecao WHERE id = p_selecao FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Seleção % não existe.', p_selecao;
    END IF;
    IF NOT s.selecionada THEN
        RAISE EXCEPTION 'Este candidato não está selecionado.';
    END IF;
    IF s.confirmada THEN
        RAISE EXCEPTION 'A seleção já foi confirmada.';
    END IF;
    v_tfc := atribuir_tfc(s.candidatura_id, p_orientador, p_coorientador);
    UPDATE candidaturas_selecao SET confirmada = true, confirmada_por_id = p_utilizador, data_confirmacao = now()
     WHERE id = s.id;
    RETURN v_tfc;
END $$;
"""

REVERSE = r"""
DROP FUNCTION IF EXISTS confirmar_selecao(bigint, bigint, bigint, bigint);
DROP FUNCTION IF EXISTS atribuir_tfc(bigint, bigint, bigint);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tfc", "0002_atribuir_tfc"),
        ("candidaturas", "0008_regras_por_grupo"),
    ]
    operations = [migrations.RunSQL(SQL, REVERSE)]
