"""Testes das regras da lista de candidaturas, dos grupos, da seleção e da atribuição (PostgreSQL)."""
from datetime import timedelta

from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from configuracao.models import Aluno, AnoLetivo, Curso, Docente, Fase, InscricaoTFC, Utilizador
from propostas.models import Proposta
from tfc.models import TFC, TFCAluno

from .models import Candidatura, Grupo, Selecao


def erro_bd():
    """Erros levantados pelos triggers (RAISE EXCEPTION) e pelas restrições chegam ao Django como DatabaseError."""
    return DatabaseError


class Base(TestCase):
    def setUp(self):
        agora = timezone.now()
        self.ano = AnoLetivo.objects.create(designacao="2099/00", data_referencia_elegibilidade=agora.date())
        Fase.objects.create(ano_letivo=self.ano, tipo="CANDIDATURAS",
                            data_inicio=agora - timedelta(days=1), data_fim=agora + timedelta(days=1))
        self.curso = Curso.objects.get(codigo="LEI")
        u = Utilizador.objects.create(username="docente", email="d@x.pt", nome="Docente")
        self.docente = Docente.objects.create(utilizador=u)
        self.alunos = [self.criar_aluno(i) for i in range(1, 5)]
        self.propostas = [self.criar_proposta(i) for i in range(1, 6)]

    def criar_aluno(self, i, ects=120):
        u = Utilizador.objects.create(username=f"a{i}", email=f"a{i}@x.pt", nome=f"Aluno {i}")
        a = Aluno.objects.create(utilizador=u, numero=f"2200{i}", curso=self.curso)
        InscricaoTFC.objects.create(aluno=a, ano_letivo=self.ano, ects=ects)
        return a

    def criar_proposta(self, i, modalidade="INDIVIDUAL_OU_GRUPO"):
        return Proposta.objects.create(ano_letivo=self.ano, codigo=f"T{i}", titulo=f"TFC {i}", descricao="-",
                                       modalidade=modalidade, estado="DISPONIVEL", tipo_proponente="DOCENTE",
                                       proponente=self.docente.utilizador, orientador_sugerido=self.docente)

    def grupo(self, submissor, colega=None):
        g = Grupo.objects.create(ano_letivo=self.ano, submissor=submissor, colega=colega)
        g.refresh_from_db()
        return g

    def individual(self, aluno):
        return Grupo.objects.filter(ano_letivo=self.ano, submissor=aluno, colega__isnull=True).first() \
            or self.grupo(aluno)

    def candidatar(self, grupo, proposta):
        c = Candidatura.objects.create(ano_letivo=self.ano, grupo=grupo, proposta=proposta)
        c.refresh_from_db()
        return c

    def lista(self, grupo):
        return list(Candidatura.objects.filter(grupo=grupo, estado__in=["ATIVA", "PENDENTE_CONFIRMACAO"])
                    .order_by("prioridade").values_list("proposta__codigo", "prioridade"))

    def estado(self, c):
        c.refresh_from_db()
        return c.estado

    def sql(self, funcao, *args):
        with connection.cursor() as cur:
            cur.execute(f"SELECT {funcao}({', '.join(['%s'] * len(args))})", list(args))
            return cur.fetchone()[0]


class GruposTests(Base):
    def test_grupo_individual_fica_ativo(self):
        self.assertEqual(self.grupo(self.alunos[0]).estado, "ATIVO")

    def test_um_so_grupo_individual_por_aluno(self):
        self.grupo(self.alunos[0])
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.grupo(self.alunos[0])

    def test_grupo_de_dois_fica_ativo_quando_o_colega_confirma(self):
        g = self.grupo(self.alunos[0], self.alunos[1])
        self.assertEqual(g.estado, "PENDENTE")
        c = self.candidatar(g, self.propostas[0])
        self.assertEqual((c.estado, c.prioridade), ("PENDENTE_CONFIRMACAO", 1))
        c.estado = "ATIVA"
        c.save()
        g.refresh_from_db()
        self.assertEqual((g.estado, g.aceite_colega), ("ATIVO", True))

    def test_colega_recusa_e_a_lista_sobe(self):
        g = self.grupo(self.alunos[0], self.alunos[1])
        cs = [self.candidatar(g, p) for p in self.propostas[:3]]
        cs[0].estado, cs[0].motivo_fim = "ENCERRADA", "RECUSADA_PELO_COLEGA"
        cs[0].save()
        self.assertEqual(self.lista(g), [("T2", 1), ("T3", 2)])

    def test_aluno_so_esta_num_grupo_de_dois_ativo(self):
        g1 = self.grupo(self.alunos[0], self.alunos[1])
        c = self.candidatar(g1, self.propostas[0])
        c.estado = "ATIVA"
        c.save()
        g2 = self.grupo(self.alunos[2], self.alunos[1])  # o aluno 2 já está num grupo ativo
        c2 = self.candidatar(g2, self.propostas[1])
        c2.estado = "ATIVA"
        with self.assertRaises(erro_bd()), transaction.atomic():
            c2.save()


class ListaDeCandidaturasTests(Base):
    def test_candidatura_fica_na_ultima_posicao(self):
        g = self.individual(self.alunos[0])
        for p in self.propostas[:3]:
            self.candidatar(g, p)
        self.assertEqual(self.lista(g), [("T1", 1), ("T2", 2), ("T3", 3)])

    def test_cancelar_sobe_as_seguintes(self):
        g = self.individual(self.alunos[0])
        cs = [self.candidatar(g, p) for p in self.propostas[:4]]
        cs[1].estado = "CANCELADA"
        cs[1].save()
        cs[1].refresh_from_db()
        self.assertIsNone(cs[1].prioridade)
        self.assertEqual(self.lista(g), [("T1", 1), ("T3", 2), ("T4", 3)])

    def test_candidatura_reativada_volta_para_o_fim(self):
        g = self.individual(self.alunos[0])
        cs = [self.candidatar(g, p) for p in self.propostas[:3]]
        cs[0].estado = "CANCELADA"
        cs[0].save()
        c = Candidatura.objects.get(id=cs[0].id)
        c.estado = "ATIVA"
        c.save()
        self.assertEqual(self.lista(g), [("T2", 1), ("T3", 2), ("T1", 3)])

    def test_mudar_prioridade(self):
        g = self.individual(self.alunos[0])
        cs = [self.candidatar(g, p) for p in self.propostas[:4]]
        self.sql("mover_candidatura", cs[3].id, 1)
        self.assertEqual(self.lista(g), [("T4", 1), ("T1", 2), ("T2", 3), ("T3", 4)])

    def test_sem_creditos_fica_recusada(self):
        sem = self.criar_aluno(9, ects=60)
        c = self.candidatar(self.individual(sem), self.propostas[0])
        self.assertEqual((c.estado, c.motivo_fim, c.prioridade), ("RECUSADA", "SEM_CREDITOS", None))

    def test_colega_sem_creditos_recusa_a_candidatura_do_grupo(self):
        sem = self.criar_aluno(9, ects=60)
        c = self.candidatar(self.grupo(self.alunos[0], sem), self.propostas[0])
        self.assertEqual((c.estado, c.motivo_fim), ("RECUSADA", "SEM_CREDITOS"))

    def test_limite_de_candidaturas(self):
        self.ano.min_candidaturas, self.ano.max_candidaturas = 1, 2
        self.ano.save()
        g = self.individual(self.alunos[0])
        self.candidatar(g, self.propostas[0])
        self.candidatar(g, self.propostas[1])
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.candidatar(g, self.propostas[2])

    def test_tfc_de_grupo_nao_aceita_individual(self):
        p = self.criar_proposta(10, modalidade="GRUPO")
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.candidatar(self.individual(self.alunos[0]), p)

    def test_tfc_individual_nao_aceita_grupo(self):
        p = self.criar_proposta(10, modalidade="INDIVIDUAL")
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.candidatar(self.grupo(self.alunos[0], self.alunos[1]), p)

    def test_candidatura_repetida(self):
        g = self.individual(self.alunos[0])
        self.candidatar(g, self.propostas[0])
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.candidatar(g, self.propostas[0])

    def test_candidatura_repetida_noutro_grupo(self):
        self.candidatar(self.individual(self.alunos[0]), self.propostas[0])
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.candidatar(self.grupo(self.alunos[0], self.alunos[1]), self.propostas[0])

    def test_fase_fechada(self):
        Fase.objects.filter(ano_letivo=self.ano).update(data_fim=timezone.now() - timedelta(hours=1),
                                                        data_inicio=timezone.now() - timedelta(days=2))
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.candidatar(self.individual(self.alunos[0]), self.propostas[0])


class SelecaoEAtribuicaoTests(Base):
    def test_selecionar_e_confirmar_desencadeia_a_atribuicao(self):
        g1, g2 = self.individual(self.alunos[0]), self.individual(self.alunos[1])
        c_a1 = [self.candidatar(g1, p) for p in self.propostas[:3]]   # aluno 1: T1, T2, T3
        c_a2 = [self.candidatar(g2, p) for p in self.propostas[1:4]]  # aluno 2: T2, T3, T4

        selecao = self.sql("selecionar_candidato", c_a1[1].id, self.docente.utilizador_id)  # T2 → aluno 1
        self.assertFalse(TFC.objects.exists())  # ainda não confirmada
        tfc_id = self.sql("confirmar_selecao", selecao, self.docente.id, None, None)

        tfc = TFC.objects.get(id=tfc_id)
        self.assertEqual((tfc.estado, tfc.proposta.estado), ("EM_CURSO", "ATRIBUIDA"))
        self.assertTrue(Selecao.objects.get(id=selecao).confirmada)
        self.assertTrue(TFCAluno.objects.filter(tfc=tfc, aluno=self.alunos[0], ativo=True).exists())
        estados = {c.proposta.codigo: (c.estado, c.motivo_fim) for c in Candidatura.objects.filter(grupo=g1)}
        self.assertEqual(estados, {"T1": ("ENCERRADA", "ALUNO_CONTEMPLADO"), "T2": ("CONTEMPLADA", ""),
                                   "T3": ("ENCERRADA", "ALUNO_CONTEMPLADO")})
        self.assertEqual(Candidatura.objects.get(id=c_a2[0].id).motivo_fim, "TFC_ATRIBUIDO_A_OUTRO")
        self.assertEqual(self.lista(g2), [("T3", 1), ("T4", 2)])

    def test_mudar_o_candidato_selecionado(self):
        c1 = self.candidatar(self.individual(self.alunos[0]), self.propostas[0])
        c2 = self.candidatar(self.individual(self.alunos[1]), self.propostas[0])
        self.sql("selecionar_candidato", c1.id, self.docente.utilizador_id)
        self.sql("selecionar_candidato", c2.id, self.docente.utilizador_id)
        self.assertEqual(list(Selecao.objects.filter(selecionada=True).values_list("candidatura_id", flat=True)),
                         [c2.id])

    def test_atribuir_grupo_cria_os_dois_alunos_no_tfc(self):
        g = self.grupo(self.alunos[0], self.alunos[1])
        outra = self.candidatar(self.individual(self.alunos[1]), self.propostas[1])
        c = self.candidatar(g, self.propostas[0])
        c.estado = "ATIVA"
        c.save()
        tfc_id = self.sql("atribuir_tfc", c.id, self.docente.id)
        self.assertEqual(set(TFCAluno.objects.filter(tfc_id=tfc_id).values_list("aluno_id", flat=True)),
                         {self.alunos[0].id, self.alunos[1].id})
        self.assertEqual(self.estado(outra), "ENCERRADA")  # a candidatura individual do colega é encerrada

    def test_nao_confirma_sem_selecao(self):
        c = self.candidatar(self.individual(self.alunos[0]), self.propostas[0])
        s = self.sql("selecionar_candidato", c.id, self.docente.utilizador_id)
        Selecao.objects.filter(id=s).update(selecionada=False)
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.sql("confirmar_selecao", s, self.docente.id, None, None)

    def test_nao_atribui_proposta_ja_atribuida(self):
        c1 = self.candidatar(self.individual(self.alunos[0]), self.propostas[0])
        c2 = self.candidatar(self.individual(self.alunos[1]), self.propostas[1])
        self.sql("atribuir_tfc", c1.id, self.docente.id)
        Candidatura.objects.filter(id=c2.id).update(proposta=self.propostas[0])
        with self.assertRaises(erro_bd()), transaction.atomic():
            self.sql("atribuir_tfc", c2.id, self.docente.id)
