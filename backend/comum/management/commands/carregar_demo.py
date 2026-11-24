"""Carrega dados de demonstração num ano letivo próprio ("DEMO"), com a fase de candidaturas aberta.

Uso: python manage.py carregar_demo
Cria docentes, alunos, grupos, propostas e candidaturas. Depois, o orientador seleciona um candidato do DEMO01
e a coordenação confirma (o que atribui o TFC com a função atribuir_tfc), e o orientador do DEMO04 seleciona um
candidato que fica à espera da confirmação da coordenação. Pode ser corrido várias vezes: apaga e recria o ano DEMO.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from candidaturas.models import Candidatura, Grupo, Selecao
from comum.models import Historico
from configuracao.models import Aluno, AnoLetivo, Curso, Docente, Fase, InscricaoTFC, Utilizador
from propostas.models import Proposta, Tecnologia
from tfc.models import TFC, TFCAluno

DOCENTES = ["Ana Martins", "Bruno Costa", "Carla Sousa"]
ALUNOS = [("22001", "Diogo Pereira", "LEI", 150), ("22002", "Eva Santos", "LEI", 132), ("22003", "Filipe Rocha", "LIG", 120),
          ("22004", "Gabriela Lima", "LEI", 96), ("22005", "Hugo Alves", "LIG", 60)]
PROPOSTAS = [
    ("DEMO01", "Plataforma de reporting de avaliações", "INDIVIDUAL_OU_GRUPO", ["Python", "Django", "PostgreSQL"], 0),
    ("DEMO02", "Aplicação móvel de acompanhamento de TFC", "INDIVIDUAL", ["React Native", "TypeScript"], 1),
    ("DEMO03", "Verificação automática de relatórios com GitHub Actions", "GRUPO", ["GitHub Actions", "Python"], 2),
    ("DEMO04", "Painel de indicadores para a coordenação", "INDIVIDUAL_OU_GRUPO", ["React", "Python"], 0),
    ("DEMO05", "Gestão de seminários e presenças", "INDIVIDUAL", ["Django", "PostgreSQL"], 1),
]
# aluno → propostas por ordem de preferência (candidaturas individuais: grupo só com o aluno)
CANDIDATURAS = {"22001": ["DEMO01", "DEMO04", "DEMO05"], "22002": ["DEMO01", "DEMO02", "DEMO04"],
                "22003": ["DEMO04", "DEMO05", "DEMO01"], "22004": ["DEMO02", "DEMO05", "DEMO04"],
                "22005": ["DEMO01", "DEMO02", "DEMO05"]}


class Command(BaseCommand):
    help = "Carrega dados de demonstração (ano letivo DEMO)."

    @transaction.atomic
    def handle(self, *args, **opts):
        agora = timezone.now()
        AnoLetivo.objects.filter(designacao="DEMO").exists() and self._apagar()
        ano = AnoLetivo.objects.create(designacao="DEMO", data_referencia_elegibilidade=agora.date())
        Fase.objects.create(ano_letivo=ano, tipo="CANDIDATURAS", data_inicio=agora - timedelta(days=7),
                            data_fim=agora + timedelta(days=30))

        docentes = []
        for i, nome in enumerate(DOCENTES, 1):
            u, _ = Utilizador.objects.get_or_create(username=f"demo_docente{i}",
                                                    defaults={"email": f"demo_docente{i}@exemplo.pt", "nome": nome})
            docentes.append(Docente.objects.get_or_create(utilizador=u)[0])

        alunos = {}
        for numero, nome, curso, ects in ALUNOS:
            u, _ = Utilizador.objects.get_or_create(username=f"demo_{numero}",
                                                    defaults={"email": f"demo_{numero}@exemplo.pt", "nome": nome})
            a, _ = Aluno.objects.get_or_create(utilizador=u, defaults={"numero": f"D{numero}",
                                                                        "curso": Curso.objects.get(codigo=curso)})
            InscricaoTFC.objects.create(aluno=a, ano_letivo=ano, ects=ects)
            alunos[numero] = a

        propostas = {}
        for codigo, titulo, modalidade, tecnologias, d in PROPOSTAS:
            p = Proposta.objects.create(
                ano_letivo=ano, codigo=codigo, titulo=titulo, descricao=f"Proposta de demonstração ({titulo}).",
                modalidade=modalidade, estado="DISPONIVEL", tipo_proponente="DOCENTE",
                proponente=docentes[d].utilizador, orientador_sugerido=docentes[d], data_publicacao=agora)
            p.cursos.set(Curso.objects.filter(codigo__in=["LEI", "LIG"]))
            p.tecnologias.set([Tecnologia.objects.get_or_create(nome=t)[0] for t in tecnologias])
            propostas[codigo] = p

        grupos = {}
        for numero, codigos in CANDIDATURAS.items():
            grupos[numero] = Grupo.objects.create(ano_letivo=ano, submissor=alunos[numero])
            for codigo in codigos:
                Candidatura.objects.create(ano_letivo=ano, grupo=grupos[numero], proposta=propostas[codigo])

        # Candidatura em grupo: a Eva submete com o Filipe; fica pendente até o Filipe confirmar (P-03.2 e P-03.3)
        par = Grupo.objects.create(ano_letivo=ano, submissor=alunos["22002"], colega=alunos["22003"])
        Candidatura.objects.create(ano_letivo=ano, grupo=par, proposta=propostas["DEMO03"])

        coordenacao, _ = Utilizador.objects.get_or_create(
            username="demo_coordenacao", defaults={"email": "demo_coordenacao@exemplo.pt", "nome": "Coordenação"})
        with connection.cursor() as cur:
            # DEMO01: o orientador seleciona o Diogo e a coordenação confirma, o que atribui o TFC
            c = Candidatura.objects.get(grupo=grupos["22001"], proposta=propostas["DEMO01"])
            cur.execute("SELECT selecionar_candidato(%s, %s)", [c.id, docentes[0].utilizador_id])
            selecao = cur.fetchone()[0]
            cur.execute("SELECT confirmar_selecao(%s, %s, NULL, %s)", [selecao, docentes[0].id, coordenacao.id])
            # DEMO04: a orientadora seleciona o Filipe; fica à espera da confirmação da coordenação
            c = Candidatura.objects.get(grupo=grupos["22003"], proposta=propostas["DEMO04"])
            cur.execute("SELECT selecionar_candidato(%s, %s)", [c.id, docentes[0].utilizador_id])

        self.stdout.write(self.style.SUCCESS("Dados de demonstração carregados no ano letivo DEMO."))
        for g in Grupo.objects.filter(ano_letivo=ano).order_by("id"):
            linhas = Candidatura.objects.filter(grupo=g).order_by("prioridade", "id")
            nomes = g.submissor.utilizador.nome + (f" + {g.colega.utilizador.nome}" if g.colega else "")
            self.stdout.write(f"  {g} {nomes}: " + ", ".join(
                f"{c.proposta.codigo}[{c.prioridade or '-'}:{c.get_estado_display()}]" for c in linhas))

    def _apagar(self):
        ano = AnoLetivo.objects.get(designacao="DEMO")
        ids = list(TFC.objects.filter(ano_letivo=ano).values_list("id", flat=True))
        TFCAluno.objects.filter(tfc_id__in=ids).delete()
        TFC.objects.filter(id__in=ids).delete()
        cand = list(Candidatura.objects.filter(ano_letivo=ano).values_list("id", flat=True))
        Historico.objects.filter(entidade="Candidatura", entidade_id__in=cand).delete()
        Selecao.objects.filter(candidatura_id__in=cand).delete()
        Candidatura.objects.filter(id__in=cand).delete()
        Grupo.objects.filter(ano_letivo=ano).delete()
        Proposta.objects.filter(ano_letivo=ano).delete()
        InscricaoTFC.objects.filter(ano_letivo=ano).delete()
        ano.fases.all().delete()
        ano.delete()
