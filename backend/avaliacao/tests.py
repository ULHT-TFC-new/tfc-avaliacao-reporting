"""A avaliação avalia a entrega (Reunião 8, 18/11)."""
from django.db import DatabaseError, transaction
from django.test import TestCase
from django.utils import timezone

from avaliacao.models import Avaliacao, ModeloAvaliacao
from configuracao.models import AnoLetivo, Docente, Utilizador
from propostas.models import Proposta
from tfc.models import TFC, Entrega


class AvaliacaoPorEntregaTests(TestCase):
    def setUp(self):
        ano = AnoLetivo.objects.create(designacao="2099/00", data_referencia_elegibilidade=timezone.now().date())
        u = Utilizador.objects.create(username="d", email="d@x.pt", nome="Docente")
        self.jurado = Docente.objects.create(utilizador=u)
        p = Proposta.objects.create(ano_letivo=ano, codigo="T1", titulo="T", descricao="-", modalidade="INDIVIDUAL",
                                    estado="ATRIBUIDA", tipo_proponente="DOCENTE", proponente=u)
        self.tfc = TFC.objects.create(proposta=p, ano_letivo=ano, orientador=self.jurado)
        momentos = ModeloAvaliacao.objects.get(ano_letivo__designacao="2026/27").momentos.order_by("ordem")
        self.ai1, self.ai2 = momentos[0], momentos[1]

    def test_o_mesmo_docente_avalia_o_tfc_em_momentos_diferentes(self):
        for m in (self.ai1, self.ai2):
            Avaliacao.objects.create(entrega=Entrega.objects.create(tfc=self.tfc, momento=m), jurado=self.jurado)
        self.assertEqual(Avaliacao.objects.filter(entrega__tfc=self.tfc, jurado=self.jurado).count(), 2)

    def test_uma_avaliacao_por_jurado_em_cada_entrega(self):
        e = Entrega.objects.create(tfc=self.tfc, momento=self.ai1)
        Avaliacao.objects.create(entrega=e, jurado=self.jurado)
        with self.assertRaises(DatabaseError), transaction.atomic():
            Avaliacao.objects.create(entrega=e, jurado=self.jurado)
