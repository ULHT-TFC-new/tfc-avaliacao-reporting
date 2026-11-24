# Backend — Plataforma de gestão de TFC

Backend da plataforma, em Python com Django e Django REST Framework, sobre uma base de dados PostgreSQL. Cobre toda a plataforma (propostas, candidaturas, entregas, avaliações e reporting); o frontend é desenvolvido no DEISI2256.

O modelo de dados está descrito em `docs/03_modelo_de_dados.md`. Cada classe desse documento corresponde a um modelo do Django e a uma tabela da base de dados.

## Arquitetura

| Contentor | Tecnologia | Porta | Função |
|---|---|---|---|
| `db` | PostgreSQL 16 | 5432 | Base de dados partilhada pelos três TFC |
| `backend` | Python 3.13, Django 5.2, Django REST Framework | 8000 | Lógica de negócio e API REST |
| frontend (DEISI2256) | a definir | 3000 ou 5173 | Chama a API do backend |

Os ficheiros submetidos (relatórios) ficam no volume `ficheiros` e não na base de dados.

## Organização do código

Uma app do Django por área do modelo de dados:

| App | Área | Classes |
|---|---|---|
| `configuracao` | Configuração e utilizadores (MP-01) | AnoLetivo, Fase, Curso, GrupoCursos, UnidadeCurricular, Utilizador, Aluno, AlunoUC, InscricaoTFC, Docente, EntidadeExterna |
| `propostas` | Propostas (MP-02) | Proposta, PropostaUC, Tecnologia, PropostaAluno, AnexoProposta |
| `candidaturas` | Candidaturas e atribuição (MP-03) | Grupo, Candidatura, Selecao |
| `tfc` | TFC, acompanhamento e entregas (MP-03 a MP-05) | TFC, TFCAluno, Pedido, Atividade, Entrega, VerificacaoAutomatica |
| `avaliacao` | Avaliação e resultados (MP-06 a MP-08) | ModeloAvaliacao, MomentoAvaliacao, Criterio, MembroJuri, Defesa, Avaliacao, ClassificacaoCriterio, Seminario, Presenca, NotaMomento, ResultadoFinal |
| `comum` | Transversais | Notificacao, Historico |

## Regras na base de dados

As regras que garantem a consistência dos dados estão no PostgreSQL e são criadas pelas migrações:

| Regra | Onde |
|---|---|
| Restrições (candidatura repetida, prioridades únicas, um TFC ativo por aluno, um grupo individual por aluno, um candidato selecionado por TFC, uma avaliação por entrega e jurado, limites de notas e pesos) | `models.py` de cada app (`constraints`) |
| R4 — um aluno só está num grupo de dois ativo por ano; o grupo individual fica ativo ao ser criado | `candidaturas/migrations/0008_regras_por_grupo.py` |
| R8 — renumerar a lista do grupo quando uma candidatura sai, e pô-la no fim se voltar | `candidaturas/migrations/0008_regras_por_grupo.py` |
| R9 — validar uma candidatura nova (fase, grupo, proposta, modalidade, candidatura repetida, limite, créditos) | `candidaturas/migrations/0008_regras_por_grupo.py` |
| P-03.3 — o grupo de dois fica ativo quando o colega confirma a primeira candidatura | `candidaturas/migrations/0008_regras_por_grupo.py` |
| P-03.4 — mudar a prioridade (`mover_candidatura`) | `candidaturas/migrations/0008_regras_por_grupo.py` |
| P-03.7 — selecionar o candidato (`selecionar_candidato`) | `candidaturas/migrations/0008_regras_por_grupo.py` |
| R7 e P-03.9 — confirmar a seleção (`confirmar_selecao`) e atribuir o TFC (`atribuir_tfc`), que desencadeia as restantes operações | `tfc/migrations/0003_atribuir_e_confirmar.py` |
| R14 (parcial) — histórico das mudanças de estado das candidaturas | `candidaturas/migrations/0008_regras_por_grupo.py` |

As alterações da reunião de 18/11 estão nas migrações `candidaturas/0005` a `0008`, `tfc/0003` e `avaliacao/0004` a `0006`: todas as candidaturas pertencem a um grupo (a individual é um grupo só com o aluno), a seleção passa a ter confirmação pela coordenação e a avaliação passa a avaliar a entrega. As migrações convertem os dados que já existam na base de dados.

Ainda por implementar: R10 (fecho no prazo), R11 (discrepância entre jurados), R12 (pesos), R13 (cálculo das notas), R15 (fecho do ano letivo), o resto do histórico e as vistas de reporting.

## Arrancar com Docker

Requisitos: Docker e Docker Compose.

```bash
cp .env.example .env      # alterar as passwords
docker compose up --build
```

O backend aplica as migrações ao arrancar: cria as tabelas, as regras da base de dados, o ano letivo 2026/27 (com as fases do regulamento), os cursos LEI, LIG e LCD e o modelo de avaliação de 2026/27.

Para usar o painel de administração e ver dados de exemplo:

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py carregar_demo
```

O `carregar_demo` cria um ano letivo "DEMO" com a fase de candidaturas aberta, docentes, alunos, grupos, propostas e candidaturas (incluindo uma candidatura em grupo à espera da confirmação do colega). No DEMO01, a orientadora seleciona um candidato e a coordenação confirma, o que atribui o TFC; no DEMO04, há um candidato selecionado à espera da confirmação. Pode ser corrido várias vezes.

## Endpoints

| Endpoint | Resposta |
|---|---|
| `GET /api/estado/` | Confirma que o backend responde e a versão do PostgreSQL |
| `GET /api/cursos/` | Cursos ativos |
| `GET /api/propostas/` | Propostas disponíveis, com o número de candidaturas. Filtros: `?curso=LEI`, `?tecnologia=python`, `?orientador=ana`, `?pesquisa=reporting` |
| `/admin/` | Painel de administração do Django, com todas as tabelas |

Exemplo de chamada a partir do frontend:

```js
const resposta = await fetch("http://localhost:8000/api/propostas/?curso=LEI");
const propostas = await resposta.json();
```

Os endereços do frontend autorizados a chamar a API estão em `CORS_ALLOWED_ORIGINS`, no `.env`.

## Correr sem Docker

Com um PostgreSQL local e as variáveis do `.env` definidas no terminal:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Testes

```bash
python manage.py test
```

Os testes verificam as regras da base de dados: grupos (individual, confirmação pelo colega, um grupo de dois ativo por aluno), lista de candidaturas (posição de uma candidatura nova, renumeração, regresso à lista, mudança de prioridade), validações (créditos do aluno e do colega, limite, modalidade, candidatura repetida, fase fechada), seleção e confirmação com as operações desencadeadas pela atribuição, e avaliação por entrega.
