"""R8 (complemento): uma candidatura que volta à lista (por exemplo, reativada pela coordenação ou
depois de uma desatribuição, P-03.13) fica na última posição, se o limite de candidaturas o permitir.
"""
from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION candidatura_regressa_a_lista() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_max int;
    v_n int;
BEGIN
    SELECT max_candidaturas INTO v_max FROM configuracao_anoletivo WHERE id = NEW.ano_letivo_id;
    SELECT count(*) INTO v_n FROM candidaturas_candidatura
     WHERE id <> NEW.id
       AND estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA')
       AND CASE WHEN NEW.grupo_id IS NULL
                THEN grupo_id IS NULL AND aluno_id = NEW.aluno_id AND ano_letivo_id = NEW.ano_letivo_id
                ELSE grupo_id = NEW.grupo_id END;
    IF v_n >= v_max THEN
        RAISE EXCEPTION 'Atingiu o limite de % candidaturas. Retire uma candidatura de outro TFC.', v_max;
    END IF;
    NEW.prioridade := v_n + 1;  -- última posição da lista
    NEW.motivo_fim := '';
    RETURN NEW;
END $$;

CREATE TRIGGER candidatura_regressa_a_lista
BEFORE UPDATE OF estado ON candidaturas_candidatura
FOR EACH ROW
WHEN (OLD.estado NOT IN ('PENDENTE_CONFIRMACAO', 'ATIVA') AND NEW.estado IN ('PENDENTE_CONFIRMACAO', 'ATIVA'))
EXECUTE FUNCTION candidatura_regressa_a_lista();
"""

REVERSE = r"""
DROP TRIGGER IF EXISTS candidatura_regressa_a_lista ON candidaturas_candidatura;
DROP FUNCTION IF EXISTS candidatura_regressa_a_lista();
"""


class Migration(migrations.Migration):
    dependencies = [("candidaturas", "0003_regras_lista")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
