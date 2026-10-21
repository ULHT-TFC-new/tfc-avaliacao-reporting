# Registo do Projeto — DEISI2257

Este ficheiro reúne o planeamento do projeto, o registo das atividades desenvolvidas e as notas das reuniões.

---

## 1. Planeamento do projeto

Planeamento até à 1ª entrega intercalar. Será revisto após cada reunião com o orientador e após cada entrega.

| Período | Tarefa | Estado |
|---|---|---|
| 30/09 – 04/10 | Criar o repositório e coordenar com os grupos do DEISI2256 e DEISI2258 (estrutura dos repositórios, base de dados, backend) | Em curso |
| 02/10 – 18/10 | Elaborar a lista de processos da plataforma (macro-processos e processos), seguindo o método de ERT, e revê-la com o orientador | Concluído |
| 05/10 – 20/10 | Finalizar o inquérito com os outros grupos e validá-lo com o orientador | Concluído |
| 20/10 – 06/11 | Divulgar o inquérito e recolher respostas | Em curso (preparação da publicação) |
| 09/11 – 15/11 | Análise exploratória dos resultados | Por iniciar |
| 09/11 – 22/11 | Levantamento de requisitos, use cases, user stories e modelo de dados | Por iniciar |
| 16/11 – 29/11 | Arquitetura, mockups e configuração do ambiente (contentores Docker) | Por iniciar |
| 23/11 – 06/12 | Redação do relatório da 1ª entrega e gravação do vídeo (máx. 2 min) | Por iniciar |
| **06/12** | **Envio do relatório ao orientador (1 semana de antecedência)** | — |
| **13/12** | **1ª entrega intercalar** | — |

### Marcos do ano letivo

| Data | Marco |
|---|---|
| 13/12/2026 | 1ª entrega intercalar |
| 04/04/2027 | 2ª entrega intercalar (desenvolvimento praticamente concluído) |
| 04/06/2027 | Entrega final (1ª época) |
| 07/06 – 19/06/2027 | Defesas |

---

## 2. Registo de atividades

| Data | Atividade | Observações |
|---|---|---|
| 28/09/2026 | Análise da plataforma atual e primeiro rascunho das perguntas do inquérito | Perguntas organizadas por blocos, associados a cada um dos três TFC |
| 30/09/2026 | Reunião com o orientador | Ver Reunião 1 |
| 30/09/2026 | Criação do repositório na organização ULHT-TFC-new | Registo do projeto |
| 02/10/2026 | Pedido do orientador para elaborar a lista de processos da plataforma | Por email, seguindo o método de ERT |
| 03/10/2026 | Elaboração da lista inicial de processos da plataforma | Macro-processos e processos (nível mezzo) |
| 03/10/2026 | Criação do inquérito em Microsoft Forms | Três perfis, com ramificação; respostas anónimas e limitadas a contas da Lusófona |
| 05/10/2026 | Envio do inquérito ao orientador para validação | Link de colaboração e documento com a estrutura do inquérito |
| 06/10/2026 | Comparação e correção da lista de processos elaborada pelo colega | Adotada como lista comum; corrigidas referências ao regulamento |
| 07/10/2026 | Reunião entre os grupos sobre o inquérito | Ver Reunião 2 |
| 14/10/2026 | Feedback do orientador, por email, sobre o percurso de aluno do inquérito | Percurso aprovado; apagadas as respostas de teste e desativada temporariamente a opção "uma resposta por pessoa" para o orientador testar os outros perfis |
| 14/10/2026 | Reunião com o orientador | Ver Reunião 3 (sem a participação de Tomás Cruz) |
| 14/10/2026 | Sugestões do orientador, por email, para os restantes perfis do inquérito | Pergunta sobre o calendário do TFC, alinhamento das perguntas com as escalas, linha temporal de prazos, tabela de avaliação por equipamento |
| 16/10/2026 | Aplicação das alterações ao inquérito e envio ao orientador | — |
| 18/10/2026 | Correção da lista de processos depois da revisão do orientador | Acrescentado o processo de configuração do modelo de avaliação (P-01.3) e corrigidas regras de candidatura, seleção e desistência |
| 20/10/2026 | Aprovação do inquérito pelo orientador para publicação | Pedido de uma nota introdutória para cada audiência; no relatório, anexar o inquérito com nota prévia sobre o uso de IA |
| 20/10/2026 | Preparação da publicação do inquérito | Notas de divulgação para alunos a iniciar o TFC, alunos que já o realizaram e docentes |

---

## 3. Notas das reuniões

### Reunião 1 — 30/09/2026

**Tipo:** Reunião com o orientador
**Participantes:** Prof. Luís Gomes (orientador), Tomás Cruz (DEISI2257) e os alunos dos TFC DEISI2256 e DEISI2258

#### Pontos discutidos

**Inquéritos e dados**
- Antes do levantamento de requisitos, será feito um inquérito aos utilizadores da plataforma atual, dirigido a alunos e docentes.
- Os inquiridos serão divididos por perfil:
  - **Alunos que iniciaram o TFC:** alunos que estão a começar o TFC este ano letivo e que só usaram a plataforma para propostas e inscrições; não conhecem os processos de entrega nem de avaliação.
  - **Alunos que já concluíram o TFC:** alunos que realizaram o TFC em anos anteriores e conhecem as restantes funcionalidades.
  - **Docentes:** orientadores e jurados, que usam a plataforma para propor TFC, acompanhar trabalhos e avaliar entregas.
- A separação de perfis evita distorções estatísticas (falácia do "meio frango"), em que a média de grupos com experiências diferentes não representa nenhum deles.

**Gestão do repositório**
- Cada grupo deve criar o seu repositório, na organização GitHub ULHT-TFC-new.

**Documentação**
- As notas das reuniões, o planeamento do projeto e o registo de atividades ficam neste ficheiro Markdown.
- A análise exploratória fica num ficheiro Markdown à parte.

#### Decisões
- O inquérito terá ramificação por perfil: os alunos que iniciaram o TFC respondem apenas às perguntas sobre navegação, propostas e candidaturas;
  os alunos que já concluíram o TFC respondem a todos os blocos de aluno; os docentes respondem a um bloco próprio sobre acompanhamento e avaliação.
- Criação do repositório do DEISI2257 na organização ULHT-TFC-new.

#### Próximos passos
- [ ] Coordenar com os grupos do DEISI2256 e DEISI2258 a estrutura dos repositórios e a divisão da base de dados e do backend.
- [x] Finalizar o inquérito em conjunto com o outro grupo e validá-lo com o orientador. *(inquérito enviado a 05/10; correções identificadas na Reunião 2)*

---

### Reunião 2 — 07/10/2026

**Tipo:** Reunião entre os grupos (reunião curta)
**Participantes:** Tomás Cruz (DEISI2257) e os alunos dos TFC DEISI2256 e DEISI2258

#### Pontos discutidos

**Inquérito**
- Revisão conjunta do inquérito sobre a plataforma de gestão de TFC.
- Foram identificadas perguntas em falta e correções a fazer antes da divulgação.

#### Decisões
- O inquérito só é divulgado depois de aplicadas as correções e os acrescentos identificados.

#### Próximos passos
- [x] Aplicar ao inquérito as correções e os acrescentos discutidos.
- [x] Testar novamente os três percursos do inquérito (um por perfil).
- [x] Enviar a versão corrigida ao orientador.

---

### Reunião 3 — 14/10/2026

**Tipo:** Reunião com o orientador
**Participantes:** Prof. Luís Gomes (orientador) e os alunos dos TFC DEISI2256 e DEISI2258. Tomás Cruz (DEISI2257) não pôde participar; os pontos abaixo foram obtidos junto dos colegas e pelos emails do orientador.

#### Pontos discutidos

**Lista de processos**
- Revisão da lista de processos da plataforma pelo orientador, com indicação do que alterar e melhorar.

**Inquérito**
- Revisão do inquérito pelo orientador. O percurso de aluno já tinha sido aprovado por email; as sugestões para os restantes perfis foram enviadas por email no mesmo dia.

#### Decisões
- Aplicar à lista de processos as alterações indicadas pelo orientador.
- Aplicar ao inquérito as sugestões do orientador antes da publicação.

#### Próximos passos
- [x] Corrigir a lista de processos (18/10).
- [x] Aplicar as alterações ao inquérito e enviá-lo ao orientador (16/10).
- [ ] Preparar o formulário para publicação (reativar "uma resposta por pessoa", apagar respostas de teste, definir data de fim).
- [ ] Publicar o inquérito com as notas de divulgação para cada audiência.
- [ ] Guardar a informação sobre o uso de IA na elaboração do inquérito, para a nota prévia do anexo do relatório.
