Aqui estÃ¡ o relatÃ³rio consolidado de Gate 1 â€” todo o conteÃºdo solicitado, extraÃ­do literalmente dos 4 documentos canÃ´nicos.

---

# Gate 1 â€” ExtraÃ§Ã£o Literal dos Documentos CanÃ´nicos (Wave 3 v4.0 / Componente 11)

## Â§1. RequisitosProvasDigitais_v4_0.docx

### Â§1.1 SeÃ§Ã£o 5 inteira â€” Matriz de TransiÃ§Ãµes do Fluxo (fonte canÃ´nica da entrega)

**CabeÃ§alho da SeÃ§Ã£o 5 (literal):**

> O mecanismo de transiÃ§Ã£o Ã© Ãºnico e invariÃ¡vel para todas as etapas: o ator responsÃ¡vel identifica a prova (escaneando o QR Code pela cÃ¢mera ou digitando manualmente o cÃ³digo da etiqueta), assina digitalmente e confirma a aÃ§Ã£o. Somente apÃ³s a confirmaÃ§Ã£o o status Ã© atualizado.
>
> O sistema possui quatro rotas, escolhidas manualmente pelo Administrador 3Studio no momento da criaÃ§Ã£o da prova. A rota Ã© imutÃ¡vel apÃ³s a criaÃ§Ã£o. As tabelas a seguir descrevem cada rota separadamente, em sequÃªncia de transiÃ§Ãµes vÃ¡lidas.

#### Â§1.1.1 SeÃ§Ã£o 5.1 â€” InventÃ¡rio Geral de Estados (literal)

> O sistema possui 14 estados distintos (incluindo "Cancelada" como estado transversal). A tabela abaixo lista cada estado e as rotas em que aparece. Os atores autorizados estÃ£o definidos nas seÃ§Ãµes 5.2 a 5.6.

| # | Estado | Rotas em que aparece |
|---|---|---|
| 01 | Criada | Todas as rotas (estado inicial) |
| 02 | Encaminhada para LaminaÃ§Ã£o | Lam. Matriz, Lam. Filial |
| 03 | Com Motorista (ida laminaÃ§Ã£o) | Lam. Matriz, Lam. Filial |
| 04 | LaminaÃ§Ã£o ConcluÃ­da | Lam. Matriz, Lam. Filial |
| 05 | Com Motorista (volta laminaÃ§Ã£o) | Lam. Matriz |
| 06 | De volta Ã  3Studio (pÃ³s-laminaÃ§Ã£o) | Lam. Matriz |
| 07 | Retirada pelo Vendedor | Matriz, Lam. Matriz |
| 08 | Encaminhada para o Vendedor | Filial, Lam. Filial |
| 09 | Aprovada pelo Vendedor | Todas as rotas |
| 10 | Reprovada pelo Vendedor | Todas as rotas |
| 11 | De volta Ã  3Studio | Matriz, Lam. Matriz |
| 12 | Com Motorista (entrega final) | Matriz, Lam. Matriz |
| 13 | Recebida pela Clicheria (terminal) | Todas as rotas |
| 14 | Cancelada (transversal) | Todas â€” disponÃ­vel em qualquer estado ativo |

#### Â§1.1.2 SeÃ§Ã£o 5.2 â€” Rota Matriz (literal)

> Vendedor estÃ¡ na Matriz e a prova nÃ£o requer laminaÃ§Ã£o. A prova sai da 3Studio, vai para o vendedor (na Matriz), retorna Ã  3Studio apÃ³s aprovaÃ§Ã£o e Ã© entregue Ã  Clicheria pelo Motorista.

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (inÃ­cio) | 3Studio | Preenchimento do formulÃ¡rio de criaÃ§Ã£o. Rota "Matriz" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | Vendedor | Identificar prova â†’ Assinar â†’ Confirmar. | Retirada pelo Vendedor |
| Retirada pelo Vendedor | Vendedor | Identificar prova â†’ Selecionar "Aprovar" â†’ Assinar â†’ Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | 3Studio | Identificar prova â†’ Assinar â†’ Confirmar recebimento. | De volta Ã  3Studio |
| De volta Ã  3Studio | Motorista | Identificar prova â†’ Assinar â†’ Confirmar entrega final. | Com Motorista (entrega final) |
| Com Motorista (entrega final) | Clicheria | Identificar prova â†’ Assinar â†’ Confirmar recebimento. | Recebida pela Clicheria (ConcluÃ­da) |

**Contagem de transiÃ§Ãµes vÃ¡lidas (sem reprovaÃ§Ã£o): 6 (incluindo a criaÃ§Ã£o inicial).**

#### Â§1.1.3 SeÃ§Ã£o 5.3 â€” Rota Lam. Matriz (literal)

> Vendedor estÃ¡ na Matriz e a prova requer laminaÃ§Ã£o. A prova sai da 3Studio para a Clicheria via Motorista (ida laminaÃ§Ã£o), Ã© laminada, retorna Ã  3Studio via Motorista (volta laminaÃ§Ã£o), Ã© retirada pelo Vendedor (na Matriz), aprovada, retorna Ã  3Studio e Ã© entregue final Ã  Clicheria via Motorista.

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (inÃ­cio) | 3Studio | Preenchimento do formulÃ¡rio de criaÃ§Ã£o. Rota "Lam. Matriz" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | 3Studio | Identificar prova â†’ Assinar â†’ Confirmar encaminhamento para laminaÃ§Ã£o. | Encaminhada para LaminaÃ§Ã£o |
| Encaminhada para LaminaÃ§Ã£o | Motorista | Identificar prova â†’ Assinar â†’ Confirmar travessia (ida laminaÃ§Ã£o). | Com Motorista (ida laminaÃ§Ã£o) |
| Com Motorista (ida laminaÃ§Ã£o) | Clicheria | Identificar prova â†’ Assinar â†’ Confirmar conclusÃ£o da laminaÃ§Ã£o. | LaminaÃ§Ã£o ConcluÃ­da |
| LaminaÃ§Ã£o ConcluÃ­da | Motorista | Identificar prova â†’ Assinar â†’ Confirmar travessia (volta laminaÃ§Ã£o). | Com Motorista (volta laminaÃ§Ã£o) |
| Com Motorista (volta laminaÃ§Ã£o) | 3Studio | Identificar prova â†’ Assinar â†’ Confirmar recebimento da prova laminada. | De volta Ã  3Studio (pÃ³s-laminaÃ§Ã£o) |
| De volta Ã  3Studio (pÃ³s-laminaÃ§Ã£o) | Vendedor | Identificar prova â†’ Assinar â†’ Confirmar. | Retirada pelo Vendedor |
| Retirada pelo Vendedor | Vendedor | Identificar prova â†’ Selecionar "Aprovar" â†’ Assinar â†’ Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | 3Studio | Identificar prova â†’ Assinar â†’ Confirmar recebimento. | De volta Ã  3Studio |
| De volta Ã  3Studio | Motorista | Identificar prova â†’ Assinar â†’ Confirmar entrega final. | Com Motorista (entrega final) |
| Com Motorista (entrega final) | Clicheria | Identificar prova â†’ Assinar â†’ Confirmar recebimento. | Recebida pela Clicheria (ConcluÃ­da) |

**Contagem de transiÃ§Ãµes vÃ¡lidas (sem reprovaÃ§Ã£o): 11 (incluindo a criaÃ§Ã£o inicial).** â† CritÃ©rio de aceitaÃ§Ã£o do Componente 11 v4.0 menciona "11 transiÃ§Ãµes".

**AtenÃ§Ã£o (ambiguidade nomeada na tabela)**: o estado destino `De volta Ã  3Studio (pÃ³s-laminaÃ§Ã£o)` (estado #06 do inventÃ¡rio) e o estado destino `De volta Ã  3Studio` (estado #11 do inventÃ¡rio) coexistem nesta rota. Estados distintos com nomes muito prÃ³ximos â€” Motorista pÃ³s-laminaÃ§Ã£o produz o estado *pÃ³s-laminaÃ§Ã£o*; 3Studio recebendo pÃ³s-aprovaÃ§Ã£o do vendedor produz o estado *De volta Ã  3Studio* sem qualificador.

#### Â§1.1.4 SeÃ§Ã£o 5.4 â€” Rota Filial (literal)

> Vendedor estÃ¡ na Filial e a prova nÃ£o requer laminaÃ§Ã£o. A prova Ã© encaminhada diretamente da 3Studio ao Vendedor (na Filial); apÃ³s aprovaÃ§Ã£o, vai diretamente Ã  Clicheria (tambÃ©m na Filial), sem participaÃ§Ã£o do Motorista.

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (inÃ­cio) | 3Studio | Preenchimento do formulÃ¡rio de criaÃ§Ã£o. Rota "Filial" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | Vendedor | Identificar prova â†’ Assinar â†’ Confirmar encaminhamento para o vendedor. | Encaminhada para o Vendedor |
| Encaminhada para o Vendedor | Vendedor | Identificar prova â†’ Selecionar "Aprovar" â†’ Assinar â†’ Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | Clicheria | Identificar prova â†’ Assinar â†’ Confirmar recebimento. | Recebida pela Clicheria (ConcluÃ­da) |

**Contagem de transiÃ§Ãµes vÃ¡lidas (sem reprovaÃ§Ã£o): 4 (incluindo a criaÃ§Ã£o inicial).**

**AtenÃ§Ã£o (ambiguidade de ator na transiÃ§Ã£o "Criada â†’ Encaminhada para o Vendedor")**: o texto da matriz nomeia **Vendedor** como ator desta transiÃ§Ã£o. A descriÃ§Ã£o da rota (parÃ¡grafo introdutÃ³rio) diz que "A prova Ã© encaminhada diretamente da 3Studio ao Vendedor". Esta Ã© uma divergÃªncia aparente na seÃ§Ã£o: o mecanismo "Identificar prova â†’ Assinar â†’ Confirmar encaminhamento para o vendedor" sugere que quem faz o "encaminhamento para o vendedor" deve ser 3Studio (espelho da rota Lam. Filial linha 2, onde 3Studio faz "encaminhamento p/ laminaÃ§Ã£o"). JÃ¡ o UML drawio (pÃ¡gina 06.3) coloca essa atividade na coluna 3Studio (ver Â§4 e Â§5 abaixo). **RecomendaÃ§Ã£o para Gate 2: levar ao Mario para decisÃ£o explÃ­cita â€” Ã© Vendedor ou 3Studio?**

#### Â§1.1.5 SeÃ§Ã£o 5.5 â€” Rota Lam. Filial (literal)

> Vendedor estÃ¡ na Filial e a prova requer laminaÃ§Ã£o. A prova sai da 3Studio (Matriz) para a Clicheria (Filial) via Motorista, Ã© laminada, Ã© encaminhada ao Vendedor (na Filial), aprovada e retorna Ã  Clicheria (tambÃ©m na Filial). NÃ£o hÃ¡ Motorista no retorno, pois Vendedor e Clicheria estÃ£o ambos na Filial.

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| (inÃ­cio) | 3Studio | Preenchimento do formulÃ¡rio de criaÃ§Ã£o. Rota "Lam. Filial" selecionada. Etiqueta gerada automaticamente. | Criada |
| Criada | 3Studio | Identificar prova â†’ Assinar â†’ Confirmar encaminhamento para laminaÃ§Ã£o. | Encaminhada para LaminaÃ§Ã£o |
| Encaminhada para LaminaÃ§Ã£o | Motorista | Identificar prova â†’ Assinar â†’ Confirmar travessia (ida laminaÃ§Ã£o). | Com Motorista (ida laminaÃ§Ã£o) |
| Com Motorista (ida laminaÃ§Ã£o) | Clicheria | Identificar prova â†’ Assinar â†’ Confirmar conclusÃ£o da laminaÃ§Ã£o. | LaminaÃ§Ã£o ConcluÃ­da |
| LaminaÃ§Ã£o ConcluÃ­da | Vendedor | Identificar prova â†’ Assinar â†’ Confirmar. | Encaminhada para o Vendedor |
| Encaminhada para o Vendedor | Vendedor | Identificar prova â†’ Selecionar "Aprovar" â†’ Assinar â†’ Confirmar. | Aprovada pelo Vendedor |
| Aprovada pelo Vendedor | Clicheria | Identificar prova â†’ Assinar â†’ Confirmar recebimento. | Recebida pela Clicheria (ConcluÃ­da) |

**Contagem de transiÃ§Ãµes vÃ¡lidas (sem reprovaÃ§Ã£o): 7 (incluindo a criaÃ§Ã£o inicial).** â† CritÃ©rio de aceitaÃ§Ã£o do Componente 11 v4.0 menciona "7 transiÃ§Ãµes".

#### Â§1.1.6 SeÃ§Ã£o 5.6 â€” ReprovaÃ§Ã£o e Cancelamento (Transversais) (literal)

> As transiÃ§Ãµes abaixo aplicam-se a todas as quatro rotas. A reprovaÃ§Ã£o sÃ³ pode ocorrer nos estados em que o vendedor toma posse da prova; o cancelamento pode ocorrer em qualquer estado ativo (nÃ£o-terminal).

| Estado Atual | Ator | Mecanismo | Estado Destino |
|---|---|---|---|
| Retirada pelo Vendedor (Matriz, Lam. Matriz) | Vendedor | Identificar prova â†’ Selecionar "Reprovar" â†’ Informar motivo â†’ Assinar â†’ Confirmar. | Reprovada pelo Vendedor |
| Encaminhada para o Vendedor (Filial, Lam. Filial) | Vendedor | Identificar prova â†’ Selecionar "Reprovar" â†’ Informar motivo â†’ Assinar â†’ Confirmar. | Reprovada pelo Vendedor |
| Reprovada pelo Vendedor | 3Studio | AÃ§Ã£o administrativa: "Reiniciar Ciclo". Rota da prova Ã© preservada. HistÃ³rico do ciclo anterior Ã© preservado integralmente. | Criada (novo ciclo) |
| Qualquer estado ativo (â‰  Cancelada, â‰  Recebida pela Clicheria) | 3Studio | AÃ§Ã£o administrativa: "Cancelar Prova". Motivo obrigatÃ³rio. | Cancelada |

---

### Â§1.2 RF-007 a RF-012 (literais)

| ID | DescriÃ§Ã£o | Prioridade |
|---|---|---|
| **RF-007** | O sistema deve registrar automaticamente o usuÃ¡rio responsÃ¡vel, a data/hora e o novo status a cada movimentaÃ§Ã£o da prova. O QR Code (ou seu cÃ³digo textual digitado) Ã© o identificador de autenticidade da aÃ§Ã£o. A transiÃ§Ã£o ocorre somente apÃ³s a assinatura digital e a confirmaÃ§Ã£o explÃ­cita do usuÃ¡rio. | Must |
| **RF-008** | [v4.0 ALTERADO] Ao identificar uma prova nos estados "Retirada pelo Vendedor" (rotas Matriz, Lam. Matriz) ou "Encaminhada para o Vendedor" (rotas Filial, Lam. Filial), o sistema deve apresentar ao vendedor duas opÃ§Ãµes: Aprovar ou Reprovar. Na reprovaÃ§Ã£o, o vendedor deve informar obrigatoriamente o motivo, assinar digitalmente e confirmar. O status da prova Ã© alterado para "Reprovada pelo Vendedor". | Must |
| **RF-009** | [v4.0 ALTERADO] ApÃ³s a reprovaÃ§Ã£o, a prova retorna Ã  3Studio com status "Reprovada pelo Vendedor". O perfil 3Studio pode entÃ£o reiniciar o ciclo da prova, retornando-a ao status "Criada", preservando integralmente o histÃ³rico de movimentaÃ§Ãµes anteriores no log de auditoria. Ao reiniciar o ciclo, a rota previamente escolhida Ã© mantida; a 3Studio pode, alternativamente, cancelar a prova e criar uma nova com rota diferente. | Must |
| **RF-010** | [v4.0 ALTERADO] Ao aprovar uma prova, o sistema deve fazer a transiÃ§Ã£o de status conforme a rota previamente escolhida no momento da criaÃ§Ã£o, seguindo a Matriz de TransiÃ§Ãµes (SeÃ§Ã£o 5). A rota Ã© imutÃ¡vel apÃ³s a criaÃ§Ã£o da prova. | Must |
| **RF-011** | O sistema deve permitir o cancelamento de uma prova digital em qualquer estado ativo (exceto "Cancelada" e "Recebida pela Clicheria"), registrando obrigatoriamente o motivo, o usuÃ¡rio responsÃ¡vel e a data/hora do cancelamento. | Must |
| **RF-012** | [v4.0 ALTERADO] O sistema deve exibir uma timeline visual para cada prova, indicando claramente: os estÃ¡gios percorridos, a rota seguida (Matriz, Lam. Matriz, Filial ou Lam. Filial), a etapa de laminaÃ§Ã£o quando aplicÃ¡vel, eventuais reprovaÃ§Ãµes com motivo, o responsÃ¡vel e o timestamp de cada etapa. A timeline deve renderizar de forma adaptada ao nÃºmero de etapas da rota. | Must |

---

### Â§1.3 Regras de NegÃ³cio RN-001 a RN-007 e RN-012 (literais)

| ID | Regra de NegÃ³cio |
|---|---|
| **RN-001** | [v4.0 ALTERADO] Toda prova digital deve possuir um QR Code Ãºnico e nÃ£o reutilizÃ¡vel, gerado automaticamente pelo sistema no momento da criaÃ§Ã£o. O cÃ³digo alfanumÃ©rico do QR Ã© tambÃ©m impresso em formato textual na etiqueta para escaneamento manual de fallback. |
| **RN-002** | [v4.0 ALTERADO] A transiÃ§Ã£o de status da prova sÃ³ pode seguir os caminhos definidos na SeÃ§Ã£o 5 (Matriz de TransiÃ§Ãµes) para a rota especificamente escolhida na criaÃ§Ã£o. NÃ£o Ã© permitido pular etapas dentro de uma rota, nem alternar entre rotas apÃ³s a criaÃ§Ã£o. |
| **RN-003** | Toda movimentaÃ§Ã£o de status exige assinatura digital do usuÃ¡rio responsÃ¡vel, registrando nome, setor, data e hora. |
| **RN-004** | [v4.0 ALTERADO] Apenas o usuÃ¡rio do setor autorizado para a prÃ³xima etapa pode realizar a transiÃ§Ã£o de status. O mapeamento completo de atores por transiÃ§Ã£o estÃ¡ definido na SeÃ§Ã£o 5; o controle de acesso por pÃ¡gina estÃ¡ definido na SeÃ§Ã£o 6. |
| **RN-005** | Provas canceladas nÃ£o podem ter seu status reativado. Um novo registro deve ser criado caso necessÃ¡rio. O histÃ³rico do registro cancelado Ã© preservado. |
| **RN-006** | [v4.0 ALTERADO] Provas reprovadas podem ter seu ciclo reiniciado exclusivamente pelo perfil 3Studio. O reinÃ­cio retorna o status a "Criada", preserva a rota original e mantÃ©m integralmente o histÃ³rico de movimentaÃ§Ãµes do ciclo anterior no log de auditoria. |
| **RN-007** | [v4.0 ALTERADO] A rota de encaminhamento (Matriz, Lam. Matriz, Filial ou Lam. Filial) Ã© escolhida manualmente pelo Administrador 3Studio no momento da criaÃ§Ã£o da prova, entre as quatro opÃ§Ãµes disponÃ­veis. A escolha Ã© livre e nÃ£o Ã© restringida pela localizaÃ§Ã£o cadastral do vendedor. A rota Ã© imutÃ¡vel apÃ³s a criaÃ§Ã£o. |
| **RN-012** | [v4.0 NOVO] As animaÃ§Ãµes do sistema devem respeitar a configuraÃ§Ã£o de acessibilidade do sistema operacional "reduzir movimento" (prefers-reduced-motion). Quando ativada, animaÃ§Ãµes decorativas devem ser substituÃ­das por transiÃ§Ãµes instantÃ¢neas ou minimalistas. |

---

### Â§1.4 User Stories US-002 a US-007 (literais)

| ID | HistÃ³ria de UsuÃ¡rio | CritÃ©rios de AceitaÃ§Ã£o |
|---|---|---|
| **US-002** [v4.0 ALTERADO] | Como vendedor, eu quero escanear o QR Code da prova pela cÃ¢mera integrada (ou digitar manualmente o cÃ³digo da etiqueta) para que o sistema me identifique automaticamente e me direcione Ã  tela de assinatura digital. | 1. A cÃ¢mera abre diretamente no sistema, sem app externo. / 2. HÃ¡ um campo de digitaÃ§Ã£o manual do cÃ³digo como fallback. / 3. O sistema identifica o vendedor logado automaticamente. / 4. ApÃ³s a identificaÃ§Ã£o, a tela de assinatura digital Ã© exibida apenas se o perfil estiver autorizado para a prÃ³xima transiÃ§Ã£o. / 5. ApÃ³s assinar e confirmar, o status muda para o prÃ³ximo estado conforme a rota da prova. |
| **US-003** [v4.0 ALTERADO] | Como vendedor, eu quero aprovar uma prova digital para que ela siga no fluxo de encaminhamento conforme a rota previamente escolhida. | 1. O vendedor sÃ³ consegue aprovar provas em "Retirada pelo Vendedor" (Matriz, Lam. Matriz) ou "Encaminhada para o Vendedor" (Filial, Lam. Filial). / 2. O sistema apresenta as opÃ§Ãµes Aprovar e Reprovar. / 3. Ao selecionar Aprovar, a assinatura Ã© registrada com data/hora. / 4. O sistema executa a transiÃ§Ã£o conforme a rota da prova (SeÃ§Ã£o 5). / 5. Status muda para "Aprovada pelo Vendedor". |
| **US-004** | Como vendedor, eu quero reprovar uma prova digital informando o motivo para que a 3Studio saiba que precisa corrigir e reiniciar o processo. | 1. O vendedor sÃ³ consegue reprovar provas em "Retirada pelo Vendedor" ou "Encaminhada para o Vendedor". / 2. O campo de motivo da reprovaÃ§Ã£o Ã© obrigatÃ³rio. / 3. A assinatura Ã© registrada com data/hora. / 4. O status muda para "Reprovada pelo Vendedor". |
| **US-005** [v4.0 NOVO] | Como Administrador 3Studio, eu quero encaminhar uma prova de rota laminada para a etapa de laminaÃ§Ã£o, registrando o inÃ­cio da travessia atÃ© a clicheria. | 1. AÃ§Ã£o disponÃ­vel apenas para provas em status "Criada" nas rotas Lam. Matriz e Lam. Filial. / 2. ApÃ³s escanear, assinar e confirmar, o status muda para "Encaminhada para LaminaÃ§Ã£o". / 3. A prÃ³xima transiÃ§Ã£o vÃ¡lida Ã© apenas pelo Motorista. |
| **US-006** [v4.0 NOVO] | Como motorista, eu quero confirmar o transporte da prova em cada uma das travessias entre Matriz e Filial para que cada perna do trajeto fique rastreada. | 1. O motorista assina nas trÃªs travessias possÃ­veis: ida laminaÃ§Ã£o, volta laminaÃ§Ã£o e entrega final. / 2. Cada travessia transita a prova para o estado "Com Motorista" correspondente ao contexto. / 3. As travessias disponÃ­veis dependem da rota da prova (ver Matriz de TransiÃ§Ãµes, SeÃ§Ã£o 5). |
| **US-007** [v4.0 NOVO] | Como usuÃ¡rio da clicheria, eu quero confirmar o tÃ©rmino da laminaÃ§Ã£o para liberar a prova para a prÃ³xima etapa do fluxo. | 1. AÃ§Ã£o disponÃ­vel para provas em estado "Com Motorista (ida laminaÃ§Ã£o)". / 2. ApÃ³s escanear, assinar e confirmar, o status muda para "LaminaÃ§Ã£o ConcluÃ­da". / 3. A prÃ³xima transiÃ§Ã£o depende da rota: Lam. Matriz exige Motorista (volta laminaÃ§Ã£o); Lam. Filial exige Vendedor (Encaminhada para o Vendedor). |

---

### Â§1.5 SeÃ§Ã£o 6 â€” Matriz de Acesso (linhas referentes a transiÃ§Ãµes de status)

**CabeÃ§alho da SeÃ§Ã£o 6 (literal):**

> Esta matriz Ã© a fonte Ãºnica de verdade para o controle de acesso a pÃ¡ginas e funcionalidades. Ã‰ implementada em duas camadas independentes: middleware do App Router (Next.js) e Row Level Security do PostgreSQL. Tentativas de acesso a pÃ¡ginas nÃ£o autorizadas sÃ£o redirecionadas para a pÃ¡gina inicial do perfil, com toast informativo.
>
> Legenda: â— = Acesso completo. â— = Acesso parcial (escopo restrito; ver coluna "ObservaÃ§Ãµes"). â—‹ = Sem acesso.

**Linhas relevantes a transiÃ§Ãµes/movimentaÃ§Ã£o de status (literal):**

| PÃ¡gina / Funcionalidade | 3Studio | Vendedor | Motorista | Clicheria | ObservaÃ§Ãµes |
|---|---|---|---|---|---|
| Escanear QR Code | â— | â— | â— | â— | Acesso universal. A validaÃ§Ã£o de transiÃ§Ã£o vÃ¡lida Ã© feita apÃ³s a identificaÃ§Ã£o da prova. |
| VisualizaÃ§Ã£o de Prova (detalhe) | â— | â— | â— | â— | Mesmo escopo da listagem. Acesso direto via URL Ã© bloqueado se a prova nÃ£o estiver no escopo do usuÃ¡rio. |
| Timeline da Prova | â— | â— | â— | â— | Componente embutido na pÃ¡gina de detalhe. Mesmas regras. |
| Listagem de Provas | â— | â— | â— | â— | 3Studio e Clicheria veem todas. Vendedor vÃª apenas provas em que Ã© o vendedor responsÃ¡vel. Motorista vÃª apenas provas em estados "Em TrÃ¢nsito" (qualquer um dos trÃªs contextos "Com Motorista"). |
| Reiniciar Ciclo (ReprovaÃ§Ã£o) | â— | â—‹ | â—‹ | â—‹ | AÃ§Ã£o dentro da pÃ¡gina de detalhe. Exclusiva 3Studio. |
| Cancelar Prova | â— | â—‹ | â—‹ | â—‹ | AÃ§Ã£o dentro da pÃ¡gina de detalhe. Exclusiva 3Studio. |

---

### Â§1.6 RNF-001 e contexto adjacente (literal)

| ID | Categoria | DescriÃ§Ã£o |
|---|---|---|
| **RNF-001** | Performance | O sistema deve carregar o dashboard e a listagem de provas em no mÃ¡ximo 3 segundos, considerando atÃ© 30 usuÃ¡rios simultÃ¢neos. |

**Nota importante:** o RNF de "transiÃ§Ã£o em < 1 segundo" **NÃƒO existe** na v4.0 â€” o requisito mais prÃ³ximo Ã© o **RNF-002** (Performance):

> **RNF-002** [v4.0 ALTERADO] A leitura do QR Code pela cÃ¢mera integrada (ou a confirmaÃ§Ã£o por digitaÃ§Ã£o manual) e a exibiÃ§Ã£o da tela de assinatura devem ocorrer em no mÃ¡ximo **2 segundos** apÃ³s a captura/confirmaÃ§Ã£o.

E o **RNF-009** (Usabilidade):

> **RNF-009** [v4.0 ALTERADO] O fluxo de identificar a prova (escanear ou digitar), assinar digitalmente e confirmar a movimentaÃ§Ã£o deve ser concluÃ­do em no mÃ¡ximo **3 toques/cliques**, contando a partir do estado "prova identificada".

---

## Â§2. BACKLOG_RastreioProvasDigitais_v4_0.docx

### Â§2.1 Componente 11 v4.0 completo (literal)

**Bloco â€” 11 (v4.0) Â· MÃ¡quina de Estados Ampliada â€” 14 Estados, 4 Rotas, Roteamento Manual [AtualizaÃ§Ã£o v4.0]**

| Campo | ConteÃºdo |
|---|---|
| **Prioridade** | Must Have |
| **Depende de** | 10 (v4.0), 19, 05 (v4.0) |
| **Justificativa** | ReformulaÃ§Ã£o central do componente 11 da v3.0. A mÃ¡quina de estados sai de aproximadamente 9 estados para 14, ganhando os estados de laminaÃ§Ã£o e os trÃªs contextos distintos de "Com Motorista". O roteamento sai de automÃ¡tico (baseado na localizaÃ§Ã£o do vendedor) para manual (escolhido pelo admin na criaÃ§Ã£o). A Matriz de TransiÃ§Ãµes da v4.0 (Requisitos v4.0, SeÃ§Ã£o 5) Ã© a especificaÃ§Ã£o canÃ´nica. |
| **Escopo** | â€¢ ImplementaÃ§Ã£o dos 14 estados em enum Pydantic v2 e em PostgreSQL (CREATE TYPE). / â€¢ ImplementaÃ§Ã£o das transiÃ§Ãµes vÃ¡lidas como uma tabela transition_rules indexada por (rota, estado_atual): retorna a lista de (estado_destino, perfil_autorizado). / â€¢ Camada de domÃ­nio que valida cada transiÃ§Ã£o contra a tabela de regras antes de persistir. / â€¢ Suporte explÃ­cito aos trÃªs contextos de "Com Motorista": ida laminaÃ§Ã£o, volta laminaÃ§Ã£o, entrega final â€” cada um Ã© um estado distinto. / â€¢ EliminaÃ§Ã£o completa do roteamento por localizaÃ§Ã£o do vendedor â€” a rota Ã© sempre lida da coluna prova.rota. / â€¢ Log de auditoria imutÃ¡vel de cada transiÃ§Ã£o (carregado pelo Componente 18 da v3.0). / â€¢ Suporte ao fluxo de aprovaÃ§Ã£o/reprovaÃ§Ã£o em ambos os pontos de partida do vendedor: "Retirada pelo Vendedor" (Matriz, Lam. Matriz) e "Encaminhada para o Vendedor" (Filial, Lam. Filial). |
| **CritÃ©rios de AceitaÃ§Ã£o** | â€¢ Toda transiÃ§Ã£o definida na Matriz de TransiÃ§Ãµes (Requisitos v4.0, SeÃ§Ãµes 5.2 a 5.6) Ã© executÃ¡vel; toda transiÃ§Ã£o nÃ£o definida Ã© rejeitada com erro 422. / â€¢ Tentativa de transiÃ§Ã£o por perfil nÃ£o autorizado retorna 403, mesmo que a rota e o estado atual permitam tecnicamente a transiÃ§Ã£o. / â€¢ Provas em rota Lam. Matriz percorrem corretamente as 11 transiÃ§Ãµes especificadas; provas em Lam. Filial percorrem corretamente as 7 transiÃ§Ãµes. / â€¢ Tentativa de mudar a rota apÃ³s criaÃ§Ã£o retorna erro. / â€¢ Cobertura mÃ­nima de 95% nos testes unitÃ¡rios da camada de mÃ¡quina de estados, cobrindo todos os pares (rota, transiÃ§Ã£o). |
| **Notas TÃ©cnicas** | â€¢ A tabela transition_rules deve viver em /domain/state_machine/rules.py como estrutura imutÃ¡vel, nÃ£o em banco de dados â€” o objetivo Ã© tornar a especificaÃ§Ã£o revisÃ¡vel por code review e versionada por git. / â€¢ Migration Alembic deve usar ALTER TYPE para adicionar os novos valores ao enum existente, preservando os dados da v3.0. A Wave 7 cobre o backfill da rota nas provas existentes. |

---

### Â§2.2 Componente 12 v4.0 completo (literal â€” contrato preparatÃ³rio)

**Bloco â€” 12 (v4.0) Â· Timeline Visual com Suporte a 4 Rotas e Etapa de LaminaÃ§Ã£o [AtualizaÃ§Ã£o v4.0]**

| Campo | ConteÃºdo |
|---|---|
| **Prioridade** | Must Have |
| **Depende de** | 11 (v4.0) |
| **Justificativa** | AtualizaÃ§Ã£o do componente 12 da v3.0. A timeline precisa renderizar de forma adaptativa o nÃºmero de etapas de cada rota. A rota Lam. Matriz tem 11 transiÃ§Ãµes; a Filial tem apenas 4. O componente tambÃ©m ganha animaÃ§Ã£o progressiva de revelaÃ§Ã£o dos estÃ¡gios. |
| **Escopo** | â€¢ Componente `<ProofTimeline rota={rota} historico={historico} estado_atual={estado} />` que aceita as 4 rotas. / â€¢ RenderizaÃ§Ã£o adaptativa: cada rota tem layout prÃ³prio com nÃºmero especÃ­fico de etapas. / â€¢ IndicaÃ§Ã£o visual da rota atual (badge no topo). / â€¢ Destaque animado para a etapa atual (Framer Motion). / â€¢ Etapas de motorista exibem qual contexto (ida laminaÃ§Ã£o, volta laminaÃ§Ã£o, entrega final). / â€¢ ReprovaÃ§Ãµes exibem motivo em destaque. / â€¢ Suporte a mÃºltiplos ciclos (provas reiniciadas apÃ³s reprovaÃ§Ã£o). |
| **CritÃ©rios de AceitaÃ§Ã£o** | â€¢ Timeline renderiza corretamente para as 4 rotas. / â€¢ Em rota laminada, as etapas de laminaÃ§Ã£o aparecem com indicaÃ§Ã£o visual diferenciada das demais. / â€¢ Provas com mÃºltiplos ciclos exibem cada ciclo com separador claro. / â€¢ AnimaÃ§Ã£o de revelaÃ§Ã£o respeita prefers-reduced-motion (RN-012, RNF-010). |

---

### Â§2.3 Definition of Done â€” Global (SeÃ§Ã£o 2, literal)

> Todo componente do backlog deve atender aos critÃ©rios abaixo antes de ser marcado como concluÃ­do. Esses critÃ©rios complementam, e nÃ£o substituem, os critÃ©rios de aceitaÃ§Ã£o especÃ­ficos de cada componente.

1. CÃ³digo revisado por ao menos um outro membro da equipe (code review aprovado).
2. Testes unitÃ¡rios implementados para a lÃ³gica de negÃ³cio â€” cobertura mÃ­nima de 80% nas camadas de domÃ­nio e serviÃ§o do backend.
3. Testes de integraÃ§Ã£o passando no ambiente de staging.
4. Migrations de banco de dados aplicadas, versionadas e documentadas.
5. Funcionalidade validada contra os critÃ©rios de aceitaÃ§Ã£o das histÃ³rias de usuÃ¡rio vinculadas (ver Documento de Requisitos v4.0, SeÃ§Ã£o 4).
6. Funcionalidade validada contra a Matriz de Acesso por Perfil (Documento de Requisitos v4.0, SeÃ§Ã£o 6) â€” testes manuais de tentativa de acesso nÃ£o autorizado em cada perfil aplicÃ¡vel.
7. Sem erros no console do browser ou logs de erro crÃ­tico no backend.
8. DocumentaÃ§Ã£o interna (comentÃ¡rios de cÃ³digo, README do mÃ³dulo) atualizada.
9. PolÃ­ticas de RLS relacionadas ao componente verificadas e versionadas em /migrations/rls/.
10. AnimaÃ§Ãµes novas validadas com prefers-reduced-motion ativado (degradaÃ§Ã£o para transiÃ§Ã£o instantÃ¢nea).

---

## Â§3. DAT_RastreioProvasDigitais_v3_0.docx

### Â§3.1 SeÃ§Ã£o 2 â€” SeparaÃ§Ã£o de Responsabilidades â€” Alembic vs Supabase (literal)

> O projeto utiliza dois mecanismos de gerenciamento de schema. A tabela abaixo define o que cada um controla. Misturar as responsabilidades â€” por exemplo, criar tabelas de domÃ­nio via painel do Supabase ou tentar versionar as tabelas de Auth via Alembic â€” resulta em estados inconsistentes difÃ­ceis de reproduzir.

| Responsabilidade | Gerenciado por | Mecanismo |
|---|---|---|
| Tabelas de domÃ­nio (provas, movimentaÃ§Ãµes, usuÃ¡rios da aplicaÃ§Ã£o, audit_log, system_settings) | Alembic | Migrations versionadas em /migrations/. Executadas via `alembic upgrade head` no deploy. |
| Tabelas de autenticaÃ§Ã£o (auth.users, auth.sessions) | Supabase Dashboard | Gerenciadas internamente pelo Supabase Auth. NÃ£o tocar via Alembic. |
| PolÃ­ticas de Row Level Security (RLS) | Scripts SQL versionados | Mantidos em /migrations/rls/. Reaplicados manualmente apÃ³s recriaÃ§Ã£o de tabela. Nunca criar RLS exclusivamente via painel do Supabase sem versionamento. |
| Ãndices de performance | Alembic | IncluÃ­dos nas migrations versionadas junto Ã s tabelas correspondentes. |
| Seeds de dados iniciais (perfis, configuraÃ§Ãµes padrÃ£o) | Alembic | Migration de seed executada uma Ãºnica vez no primeiro deploy do ambiente. |
| Enums de domÃ­nio (rota_enum, status_prova_enum) | Alembic | Criados via CREATE TYPE em migrations. AlteraÃ§Ãµes usam ALTER TYPE ... ADD VALUE. PostgreSQL nÃ£o suporta remover valores de enum em transaÃ§Ã£o â€” mudanÃ§as destrutivas exigem migration manual coordenada. |

> Regra crÃ­tica: toda polÃ­tica de RLS deve existir como arquivo .sql em /migrations/rls/ antes de ser aplicada ao banco. ApÃ³s qualquer DROP TABLE ou recriaÃ§Ã£o de tabela via Alembic, as polÃ­ticas de RLS daquele schema devem ser reaplicadas manualmente a partir dos arquivos versionados.

---

### Â§3.2 SeÃ§Ã£o 3 â€” EstratÃ©gia de Testes (literal)

> A estratÃ©gia segue trÃªs camadas complementares, cobrindo desde a lÃ³gica de negÃ³cio isolada atÃ© fluxos de usuÃ¡rio completos no browser. A cobertura mÃ­nima de 80% aplica-se Ã  lÃ³gica de negÃ³cio do backend â€” mÃ¡quina de estados, RBAC e regras de cÃ¡lculo de atraso. **Para a camada de mÃ¡quina de estados especificamente, exige-se cobertura mÃ­nima de 95% pela criticidade do componente (ver SeÃ§Ã£o 4).**

| Camada | Foco e CenÃ¡rios CrÃ­ticos | Ferramentas | Meta de Cobertura |
|---|---|---|---|
| **Camada 1 â€” UnitÃ¡rios** | â€¢ MÃ¡quina de estados: cada par (rota, transiÃ§Ã£o) Ã© testado, incluindo tentativas de salto de etapa entre rotas. / â€¢ RBAC: cada cÃ©lula da Matriz de Acesso (Requisitos v4.0, SeÃ§Ã£o 6) Ã© coberta â€” permissÃ£o concedida e permissÃ£o negada. / â€¢ RN-008: lÃ³gica de cÃ¡lculo de provas atrasadas em horas Ãºteis. / â€¢ ValidaÃ§Ã£o de campos com Pydantic v2, incluindo a imutabilidade da coluna rota. | pytest â‰¥ 8.0 / pytest-asyncio â‰¥ 0.23 | â‰¥ 80% nas camadas de domÃ­nio e serviÃ§o; **â‰¥ 95% na mÃ¡quina de estados.** |
| **Camada 2 â€” IntegraÃ§Ã£o** | â€¢ Endpoints FastAPI com banco PostgreSQL real (ambiente isolado de teste). / â€¢ Ciclo completo das 4 rotas: criaÃ§Ã£o â†’ travessias do motorista (quando aplicÃ¡vel) â†’ laminaÃ§Ã£o (quando aplicÃ¡vel) â†’ aprovaÃ§Ã£o â†’ encerramento. / â€¢ RejeiÃ§Ã£o de transiÃ§Ãµes invÃ¡lidas e tentativas de salto entre rotas. / â€¢ RLS impedindo acesso entre perfis diferentes â€” query direta retorna 0 registros. / â€¢ EquivalÃªncia entre middleware do App Router e RLS â€” toda pÃ¡gina bloqueada pelo middleware tambÃ©m tem leitura bloqueada pela RLS. | pytest + httpx (AsyncClient) / PostgreSQL isolado | 100% dos endpoints crÃ­ticos. |
| **Camada 3 â€” E2E** | â€¢ Fluxo completo: login â†’ escanear (ou digitar cÃ³digo manual) â†’ assinar â†’ confirmar transiÃ§Ã£o. / â€¢ Dashboard atualizando em tempo real apÃ³s transiÃ§Ã£o. / â€¢ Fluxo de cancelamento com motivo. / â€¢ RestriÃ§Ã£o de aÃ§Ãµes por perfil no browser â€” tentativa de acesso direto via URL. / â€¢ AnimaÃ§Ãµes com prefers-reduced-motion ativado â€” transiÃ§Ãµes degradam para instantÃ¢neas. | Playwright â‰¥ 1.40 / (cÃ¢mera mockada via API de permissÃµes) | CenÃ¡rios crÃ­ticos cobertos manualmente antes de cada deploy em staging. |

> **Nota sobre cÃ¢mera em E2E:** o Playwright suporta injeÃ§Ã£o de media streams via API de permissÃµes do browser, permitindo simular a leitura de QR Code em ambiente headless sem cÃ¢mera fÃ­sica. O QR Code de teste deve ser prÃ©-gerado como fixture estÃ¡tica nos testes. O caminho alternativo de digitaÃ§Ã£o manual do cÃ³digo deve ser igualmente coberto, sem dependÃªncia de mock de cÃ¢mera.

---

### Â§3.3 SeÃ§Ã£o 4 â€” Camada de MÃ¡quina de Estados (literal completo)

> A mÃ¡quina de estados Ã© o coraÃ§Ã£o do domÃ­nio. Na v4.0 do produto, sai de aproximadamente 9 estados para 14, e ganha quatro rotas distintas (Matriz, Lam. Matriz, Filial e Lam. Filial). Esta seÃ§Ã£o define o mÃ³dulo arquitetural responsÃ¡vel por essa lÃ³gica.

**Â§4.1 LocalizaÃ§Ã£o no RepositÃ³rio**

> O mÃ³dulo vive em `/domain/state_machine/` e contÃ©m trÃªs arquivos principais:
> - **rules.py** â€” tabela imutÃ¡vel de transiÃ§Ãµes vÃ¡lidas, indexada por (rota, estado_atual). Versionada em git, revisada por code review.
> - **machine.py** â€” funÃ§Ã£o pura `transition(prova, ator, acao)` que consulta rules.py, valida e retorna o prÃ³ximo estado ou levanta `TransitionNotAllowed`.
> - **enums.py** â€” enums Pydantic v2 sincronizados com os enums PostgreSQL: Rota, EstadoProva, AcaoUsuario.

**Â§4.2 PrincÃ­pio de InvariÃ¢ncia**

> As regras de transiÃ§Ã£o NÃƒO vivem no banco de dados. Vivem em cÃ³digo versionado. Justificativa:
> - RevisÃ£o por code review Ã© mais robusta do que mudanÃ§a de dado em produÃ§Ã£o.
> - Bug em transiÃ§Ã£o Ã© detectado pelos testes unitÃ¡rios (â‰¥ 95% de cobertura) antes do deploy.
> - Rollback de transiÃ§Ã£o quebrada = rollback de commit, nÃ£o migraÃ§Ã£o de dados.
> - A tabela transitions_rules em formato Python Ã© diretamente serializÃ¡vel como documentaÃ§Ã£o (SeÃ§Ã£o 5 do documento de Requisitos).

**Â§4.3 Estrutura da Tabela de Regras (snippet de referÃªncia canÃ´nico)**

```python
# /domain/state_machine/rules.py
from enum import Enum
from typing import Mapping
from .enums import Rota, EstadoProva, Setor

# Cada chave (rota, estado_atual) mapeia para uma lista de transiÃ§Ãµes vÃ¡lidas.
# Cada transiÃ§Ã£o = (acao_usuario, perfil_autorizado, estado_destino).

TRANSITION_RULES: Mapping[tuple[Rota, EstadoProva], list[Transition]] = {
    # ---- ROTA MATRIZ ----
    (Rota.MATRIZ, EstadoProva.CRIADA): [
        Transition(Acao.IDENTIFICAR_E_ASSINAR, Setor.VENDEDOR, EstadoProva.RETIRADA_VENDEDOR),
    ],
    (Rota.MATRIZ, EstadoProva.RETIRADA_VENDEDOR): [
        Transition(Acao.APROVAR, Setor.VENDEDOR, EstadoProva.APROVADA_VENDEDOR),
        Transition(Acao.REPROVAR, Setor.VENDEDOR, EstadoProva.REPROVADA_VENDEDOR),
    ],
    (Rota.MATRIZ, EstadoProva.APROVADA_VENDEDOR): [
        Transition(Acao.IDENTIFICAR_E_ASSINAR, Setor.STUDIO, EstadoProva.DE_VOLTA_STUDIO),
    ],
    (Rota.MATRIZ, EstadoProva.DE_VOLTA_STUDIO): [
        Transition(Acao.IDENTIFICAR_E_ASSINAR, Setor.MOTORISTA, EstadoProva.COM_MOTORISTA_ENTREGA_FINAL),
    ],
    (Rota.MATRIZ, EstadoProva.COM_MOTORISTA_ENTREGA_FINAL): [
        Transition(Acao.IDENTIFICAR_E_ASSINAR, Setor.CLICHERIA, EstadoProva.RECEBIDA_CLICHERIA),
    ],
    # ---- (demais rotas seguem o mesmo padrÃ£o) ----
}
```

> TransiÃ§Ãµes nÃ£o presentes na tabela sÃ£o automaticamente rejeitadas. NÃ£o existe wildcard nem fallback â€” toda transiÃ§Ã£o vÃ¡lida Ã© explÃ­cita.

**Â§4.4 Estados Globais Independentes de Rota**

> Dois fluxos atravessam todas as rotas e sÃ£o tratados separadamente:
> - **ReprovaÃ§Ã£o:** de qualquer estado em que o vendedor possa atuar, a transiÃ§Ã£o REPROVAR (com motivo obrigatÃ³rio) leva a REPROVADA_VENDEDOR. A partir de REPROVADA_VENDEDOR, apenas o 3Studio pode acionar REINICIAR_CICLO, que retorna a CRIADA preservando a rota original.
> - **Cancelamento:** de qualquer estado ativo (â‰  CANCELADA, â‰  RECEBIDA_CLICHERIA), o 3Studio pode acionar CANCELAR (motivo obrigatÃ³rio). O estado terminal CANCELADA nÃ£o tem transiÃ§Ãµes de saÃ­da.

**Â§4.5 SincronizaÃ§Ã£o entre Python e PostgreSQL (fluxo obrigatÃ³rio de mudanÃ§a)**

> Os enums Python e os tipos PostgreSQL precisam estar sincronizados. A v3.0 do DAT estabelece o seguinte fluxo de mudanÃ§a:
> 1. Editar `/domain/state_machine/enums.py` adicionando o novo valor.
> 2. Criar migration Alembic com `ALTER TYPE rota_enum ADD VALUE 'novo_valor'`.
> 3. Editar `/domain/state_machine/rules.py` adicionando as transiÃ§Ãµes do novo valor.
> 4. Cobrir as novas transiÃ§Ãµes com testes unitÃ¡rios (cobertura â‰¥ 95% mantida).
> 5. Atualizar o Documento de Requisitos (SeÃ§Ã£o 5) e o Documento de Arquitetura TÃ©cnica.
>
> Pull requests que tocam apenas um lado da sincronizaÃ§Ã£o (Python ou banco) devem ser bloqueados por checklist obrigatÃ³rio no template de PR.

---

### Â§3.4 SeÃ§Ã£o 7 â€” RBAC â€” Defesa em Profundidade (literal completo)

> A Matriz de Acesso (Documento de Requisitos v4.0, SeÃ§Ã£o 6) Ã© a fonte Ãºnica de verdade para o controle de acesso. Esta seÃ§Ã£o define como ela Ã© implementada em duas camadas independentes.

**Â§7.1 Camada Superior â€” Middleware do App Router**

> Implementado em `/middleware.ts` na raiz do projeto Next.js. Intercepta toda requisiÃ§Ã£o autenticada e valida:
> - (a) O usuÃ¡rio estÃ¡ autenticado (JWT do Supabase vÃ¡lido).
> - (b) O perfil do usuÃ¡rio estÃ¡ autorizado para a pÃ¡gina solicitada conforme `/lib/access-matrix.ts`.
> - (c) Quando o acesso for parcial (â— na matriz), o middleware injeta um header com o escopo aplicÃ¡vel (ex.: `x-scope: vendedor=<user_id>`) que serÃ¡ lido pelos handlers.
>
> Em caso de acesso negado, o middleware retorna 302 redirect para a pÃ¡gina inicial do perfil + cookie efÃªmero com mensagem para o toast.

**Â§7.2 Camada Inferior â€” Row Level Security do PostgreSQL**

> Mesmo que o middleware seja burlado (bug, ataque, mudanÃ§a de UI sem atualizaÃ§Ã£o do middleware), as queries SQL nÃ£o podem retornar dados fora do escopo do usuÃ¡rio.
>
> Toda tabela de domÃ­nio sensÃ­vel tem polÃ­ticas RLS versionadas em `/migrations/rls/`. Exemplos:

```sql
-- /migrations/rls/provas_select.sql
-- Vendedor: vÃª apenas as provas em que Ã© o vendedor responsÃ¡vel
CREATE POLICY provas_select_vendedor ON provas
  FOR SELECT
  TO authenticated
  USING (
    (auth.jwt() ->> 'setor') = 'vendedor'
    AND vendedor_id = (auth.jwt() ->> 'user_id')::uuid
  );

-- Motorista: vÃª apenas as provas em estados "Com Motorista (*)"
CREATE POLICY provas_select_motorista ON provas
  FOR SELECT
  TO authenticated
  USING (
    (auth.jwt() ->> 'setor') = 'motorista'
    AND status IN (
      'com_motorista_ida_laminacao',
      'com_motorista_volta_laminacao',
      'com_motorista_entrega_final'
    )
  );
```

**Â§7.3 EquivalÃªncia entre Camadas**

> Toda alteraÃ§Ã£o na Matriz de Acesso exige PR Ãºnico cobrindo as duas camadas (access-matrix.ts E migrations RLS). Testes automatizados validam a equivalÃªncia: para cada (perfil, pÃ¡gina) marcado como â—/â—, o perfil consegue ler dados; para cada â—‹, o perfil recebe 0 registros via RLS.

---

## Â§4. UML_RastreioProvasDigitais_v4_0.drawio â€” Diagramas de Atividades 06.1 a 06.4

**ObservaÃ§Ã£o metodolÃ³gica:** as 4 abas (06.1â€“06.4) **nÃ£o usam shapes drawio "swimlane"** propriamente ditos. Em vez disso, usam retÃ¢ngulos com label do ator ("3Studio", "Vendedor", "Motorista", "Clicheria") posicionados como cabeÃ§alhos de coluna, e cada nÃ³ de atividade fica visualmente colocado abaixo do cabeÃ§alho correspondente. O parser nÃ£o detecta swimlane por relaÃ§Ã£o parent/child â€” entÃ£o listo as aÃ§Ãµes em ordem de fluxo (seguindo as edges) e atribuo o ator por correlaÃ§Ã£o com a Matriz textual (SeÃ§Ã£o 5).

---

### Â§4.1 Aba 06.1 Â· Atividades Â· Rota Matriz

**CabeÃ§alhos de coluna (atores presentes na aba):** 3Studio Â· Vendedor Â· Motorista Â· Clicheria  *(cada um aparece em 2 retÃ¢ngulos â€” topo e base â€” emoldurando a coluna)*

**SequÃªncia de nÃ³s conectados (em ordem topolÃ³gica do fluxo, a partir do inÃ­cio):**

| # | NÃ³ (label) | Tipo UML | Ator (inferido da Matriz Â§1.1.2) |
|---|---|---|---|
| 1 | (Initial Node â—) | marker | â€” |
| 2 | `Criar prova (rota = Matriz)` | action | 3Studio |
| 3 | `â†’ Criada` | state | (estado destino) |
| 4 | `Identificar prova â†’ assinar â†’ confirmar` | action | Vendedor |
| 5 | `â†’ Retirada pelo Vendedor` | state | (estado destino) |
| 6 | `Aprovar?` | **decision (rhombus)** | Vendedor |
| 7a (rama Aprovar) | `Selecionar "Aprovar" â†’ assinar â†’ confirmar` | action | Vendedor |
| 8a | `â†’ Aprovada pelo Vendedor` | state | (estado destino) |
| 9a | `Identificar prova â†’ assinar â†’ confirmar` | action | 3Studio |
| 10a | `â†’ De volta Ã  3Studio` | state | (estado destino) |
| 11a | `Identificar prova â†’ assinar â†’ confirmar` | action | Motorista |
| 12a | `â†’ Com Motorista (entrega final)` | state | (estado destino) |
| 13a | `Identificar prova â†’ assinar â†’ confirmar` | action | Clicheria |
| 14a | `â†’ Recebida pela Clicheria` | state | (terminal) |
| 15a | (Activity Final â—Ž) | marker | â€” |
| 7b (rama Reprovar) | `Selecionar "Reprovar" â†’ motivo â†’ assinar â†’ confirmar` | action | Vendedor |
| 8b | `â†’ Reprovada pelo Vendedor` | state | (estado destino) |
| 9b | `Reiniciar Ciclo (aÃ§Ã£o administrativa)` | action | 3Studio |
| 10b | `â†’ Criada (novo ciclo)` | state | (volta ao nÃ³ 2) |

**Edges (transiÃ§Ãµes UML literais):**

| De | â†’ Para | Label da edge |
|---|---|---|
| (initial â—) | Criar prova (rota = Matriz) | â€” |
| Criar prova (rota = Matriz) | Identificar prova â†’ assinar â†’ confirmar [Vendedor] | â€” |
| Identificar prova [Vendedor] | Aprovar? | â€” |
| Aprovar? | Selecionar "Aprovar" â†’ assinar â†’ confirmar | **[Aprovar]** |
| Aprovar? | Selecionar "Reprovar" â†’ motivo â†’ assinar â†’ confirmar | **[Reprovar]** |
| Selecionar "Aprovar" | Identificar prova â†’ assinar â†’ confirmar [3Studio] | â€” |
| Identificar prova [3Studio] | Identificar prova â†’ assinar â†’ confirmar [Motorista] | â€” |
| Identificar prova [Motorista] | Identificar prova â†’ assinar â†’ confirmar [Clicheria] | â€” |
| Identificar prova [Clicheria] | (final â—Ž) | â€” |
| Selecionar "Reprovar" | Reiniciar Ciclo (aÃ§Ã£o administrativa) | â€” |
| Reiniciar Ciclo | Criar prova (rota = Matriz) | **novo ciclo** |

**Contexto do Motorista nesta aba:** **um Ãºnico contexto** â€” `Com Motorista (entrega final)`. NÃ£o hÃ¡ ida/volta laminaÃ§Ã£o aqui (rota sem laminaÃ§Ã£o).

---

### Â§4.2 Aba 06.2 Â· Atividades Â· Rota Lam. Matriz

**CabeÃ§alhos de coluna (atores presentes):** 3Studio Â· Motorista Â· Clicheria Â· Vendedor

**SequÃªncia de nÃ³s conectados (ordem topolÃ³gica):**

| # | NÃ³ (label) | Tipo UML | Ator (inferido) |
|---|---|---|---|
| 1 | (Initial Node â—) | marker | â€” |
| 2 | `Criar prova (rota = Lam. Matriz)` | action | 3Studio |
| 3 | `â†’ Criada` | state | (estado destino) |
| 4 | `Identificar prova â†’ assinar â†’ confirmar encaminhamento p/ laminaÃ§Ã£o` | action | **3Studio** |
| 5 | `â†’ Encaminhada para LaminaÃ§Ã£o` | state | (estado destino) |
| 6 | `Identificar prova â†’ assinar â†’ confirmar travessia (ida laminaÃ§Ã£o)` | action | **Motorista** |
| 7 | `â†’ Com Motorista (ida laminaÃ§Ã£o)` | state | (estado destino) |
| 8 | `Identificar prova â†’ assinar â†’ confirmar conclusÃ£o da laminaÃ§Ã£o` | action | **Clicheria** |
| 9 | `â†’ LaminaÃ§Ã£o ConcluÃ­da` | state | (estado destino) |
| 10 | `Identificar prova â†’ assinar â†’ confirmar travessia (volta laminaÃ§Ã£o)` | action | **Motorista** |
| 11 | `â†’ Com Motorista (volta laminaÃ§Ã£o)` | state | (estado destino) |
| 12 | `Identificar prova â†’ assinar â†’ confirmar recebimento da prova laminada` | action | **3Studio** |
| 13 | `â†’ De volta Ã  3Studio (pÃ³s-laminaÃ§Ã£o)` | state | (estado destino) |
| 14 | `Identificar prova â†’ assinar â†’ confirmar` | action | Vendedor |
| 15 | `â†’ Retirada pelo Vendedor` | state | (estado destino) |
| 16 | `Aprovar?` | **decision** | Vendedor |
| 17a | `Selecionar "Aprovar" â†’ assinar â†’ confirmar` | action | Vendedor |
| 18a | `â†’ Aprovada pelo Vendedor` | state | (estado destino) |
| 19a | `Identificar prova â†’ assinar â†’ confirmar` | action | 3Studio |
| 20a | `â†’ De volta Ã  3Studio` | state | (estado destino) |
| 21a | `Identificar prova â†’ assinar â†’ confirmar entrega final` | action | **Motorista** |
| 22a | `â†’ Com Motorista (entrega final)` | state | (estado destino) |
| 23a | `Identificar prova â†’ assinar â†’ confirmar` | action | Clicheria |
| 24a | `â†’ Recebida pela Clicheria` | state | (terminal) |
| 25a | (Activity Final â—Ž) | marker | â€” |
| 17b | `Selecionar "Reprovar" â†’ motivo â†’ assinar â†’ confirmar` | action | Vendedor |
| 18b | `â†’ Reprovada pelo Vendedor` | state | (estado destino) |
| 19b | `Reiniciar Ciclo (aÃ§Ã£o administrativa)` | action | 3Studio |
| 20b | `â†’ Criada (novo ciclo)` | state | (volta ao nÃ³ 2) |

**Edges (transiÃ§Ãµes UML literais, fluxo principal):** (initial) â†’ Criar prova â†’ Identificar [3Studio/encaminhamento p/ laminaÃ§Ã£o] â†’ Identificar [Motorista/ida laminaÃ§Ã£o] â†’ Identificar [Clicheria/conclusÃ£o] â†’ Identificar [Motorista/volta laminaÃ§Ã£o] â†’ Identificar [3Studio/recebimento laminada] â†’ Identificar [Vendedor] â†’ Aprovar? â†’ [Aprovar] Selecionar "Aprovar" â†’ Identificar [3Studio] â†’ Identificar [Motorista/entrega final] â†’ Identificar [Clicheria] â†’ (final). Rama de reprovaÃ§Ã£o: Aprovar? â†’ [Reprovar] Selecionar "Reprovar" â†’ Reiniciar Ciclo â†’ Criar prova (com edge label **"novo ciclo"**).

**Contexto do Motorista nesta aba:** **trÃªs contextos distintos** explicitamente diferenciados pelas labels â€” `(ida laminaÃ§Ã£o)`, `(volta laminaÃ§Ã£o)` e `(entrega final)`. Cada contexto Ã© um nÃ³ de aÃ§Ã£o separado.

---

### Â§4.3 Aba 06.3 Â· Atividades Â· Rota Filial

**CabeÃ§alhos de coluna (atores presentes):** 3Studio Â· Vendedor Â· Clicheria *(sem Motorista â€” rota sem laminaÃ§Ã£o e Vendedor jÃ¡ na Filial)*

**SequÃªncia de nÃ³s conectados (ordem topolÃ³gica):**

| # | NÃ³ (label) | Tipo UML | Ator (inferido) |
|---|---|---|---|
| 1 | (Initial Node â—) | marker | â€” |
| 2 | `Criar prova (rota = Filial)` | action | 3Studio |
| 3 | `â†’ Criada` | state | (estado destino) |
| 4 | `Identificar prova â†’ assinar â†’ confirmar encaminhamento p/ vendedor` | action | **3Studio (pela posiÃ§Ã£o no diagrama, ver Â§5)** |
| 5 | `â†’ Encaminhada para o Vendedor` | state | (estado destino) |
| 6 | `Aprovar?` | **decision** | Vendedor |
| 7a | `Selecionar "Aprovar" â†’ assinar â†’ confirmar` | action | Vendedor |
| 8a | `â†’ Aprovada pelo Vendedor` | state | (estado destino) |
| 9a | `Identificar prova â†’ assinar â†’ confirmar` | action | Clicheria |
| 10a | `â†’ Recebida pela Clicheria` | state | (terminal) |
| 11a | (Activity Final â—Ž) | marker | â€” |
| 7b | `Selecionar "Reprovar" â†’ motivo â†’ assinar â†’ confirmar` | action | Vendedor |
| 8b | `â†’ Reprovada pelo Vendedor` | state | (estado destino) |
| 9b | `Reiniciar Ciclo (aÃ§Ã£o administrativa)` | action | 3Studio |
| 10b | `â†’ Criada (novo ciclo)` | state | (volta ao nÃ³ 2) |

**Edges (transiÃ§Ãµes UML literais):** (initial) â†’ Criar prova â†’ Identificar [encaminhamento p/ vendedor] â†’ Aprovar? â†’ [Aprovar] Selecionar "Aprovar" â†’ Identificar [Clicheria] â†’ (final). Rama de reprovaÃ§Ã£o: Aprovar? â†’ [Reprovar] Selecionar "Reprovar" â†’ Reiniciar Ciclo â†’ Criar prova (edge **"novo ciclo"**).

**Contexto do Motorista nesta aba:** **inexistente** â€” Motorista nÃ£o aparece. Coerente com a descriÃ§Ã£o da rota Filial na SeÃ§Ã£o 5.4 do Requisitos ("sem participaÃ§Ã£o do Motorista").

---

### Â§4.4 Aba 06.4 Â· Atividades Â· Rota Lam. Filial

**CabeÃ§alhos de coluna (atores presentes):** 3Studio Â· Motorista Â· Clicheria Â· Vendedor

**SequÃªncia de nÃ³s conectados (ordem topolÃ³gica):**

| # | NÃ³ (label) | Tipo UML | Ator (inferido) |
|---|---|---|---|
| 1 | (Initial Node â—) | marker | â€” |
| 2 | `Criar prova (rota = Lam. Filial)` | action | 3Studio |
| 3 | `â†’ Criada` | state | (estado destino) |
| 4 | `Identificar prova â†’ assinar â†’ confirmar encaminhamento p/ laminaÃ§Ã£o` | action | **3Studio** |
| 5 | `â†’ Encaminhada para LaminaÃ§Ã£o` | state | (estado destino) |
| 6 | `Identificar prova â†’ assinar â†’ confirmar travessia (ida laminaÃ§Ã£o)` | action | **Motorista** |
| 7 | `â†’ Com Motorista (ida laminaÃ§Ã£o)` | state | (estado destino) |
| 8 | `Identificar prova â†’ assinar â†’ confirmar conclusÃ£o da laminaÃ§Ã£o` | action | **Clicheria** |
| 9 | `â†’ LaminaÃ§Ã£o ConcluÃ­da` | state | (estado destino) |
| 10 | `Identificar prova â†’ assinar â†’ confirmar` | action | Vendedor |
| 11 | `â†’ Encaminhada para o Vendedor` | state | (estado destino) |
| 12 | `Aprovar?` | **decision** | Vendedor |
| 13a | `Selecionar "Aprovar" â†’ assinar â†’ confirmar` | action | Vendedor |
| 14a | `â†’ Aprovada pelo Vendedor` | state | (estado destino) |
| 15a | `Identificar prova â†’ assinar â†’ confirmar` | action | Clicheria |
| 16a | `â†’ Recebida pela Clicheria` | state | (terminal) |
| 17a | (Activity Final â—Ž) | marker | â€” |
| 13b | `Selecionar "Reprovar" â†’ motivo â†’ assinar â†’ confirmar` | action | Vendedor |
| 14b | `â†’ Reprovada pelo Vendedor` | state | (estado destino) |
| 15b | `Reiniciar Ciclo (aÃ§Ã£o administrativa)` | action | 3Studio |
| 16b | `â†’ Criada (novo ciclo)` | state | (volta ao nÃ³ 2) |

**Edges (transiÃ§Ãµes UML literais, fluxo principal):** (initial) â†’ Criar prova â†’ Identificar [3Studio/encaminhamento p/ laminaÃ§Ã£o] â†’ Identificar [Motorista/ida laminaÃ§Ã£o] â†’ Identificar [Clicheria/conclusÃ£o] â†’ Identificar [Vendedor] â†’ Aprovar? â†’ [Aprovar] Selecionar "Aprovar" â†’ Identificar [Clicheria] â†’ (final). Rama de reprovaÃ§Ã£o: Aprovar? â†’ [Reprovar] Selecionar "Reprovar" â†’ Reiniciar Ciclo â†’ Criar prova (edge **"novo ciclo"**).

**Contexto do Motorista nesta aba:** **um Ãºnico contexto** â€” `(ida laminaÃ§Ã£o)`. NÃ£o hÃ¡ volta laminaÃ§Ã£o nem entrega final pelo Motorista nesta rota (coerente com a descriÃ§Ã£o da rota Lam. Filial na SeÃ§Ã£o 5.5 â€” "NÃ£o hÃ¡ Motorista no retorno, pois Vendedor e Clicheria estÃ£o ambos na Filial").

---

## Â§5. CoerÃªncia Cruzada â€” Matriz Textual (Requisitos Â§5) Ã— UML drawio

Confronto rota a rota entre o texto da SeÃ§Ã£o 5 do Requisitos e os nÃ³s/edges das abas 06.x do drawio.

### Â§5.1 Rota Matriz (texto Â§5.2 vs UML 06.1)

**Resultado: COERENTE.** As 5 transiÃ§Ãµes nÃ£o-iniciais da matriz textual (Criadaâ†’Retirada, Retiradaâ†’Aprovada, Aprovadaâ†’De volta, De voltaâ†’Com Motorista entrega final, Com Motorista entrega finalâ†’Recebida) batem byte-a-byte com o caminho principal do UML. Atores idÃªnticos: Vendedor, Vendedor, 3Studio, Motorista, Clicheria. ReprovaÃ§Ã£o representada no UML como rama [Reprovar] do decision "Aprovar?" levando a "Reprovada pelo Vendedor" â†’ "Reiniciar Ciclo" â†’ "Criada (novo ciclo)", coerente com Â§5.6.

### Â§5.2 Rota Lam. Matriz (texto Â§5.3 vs UML 06.2)

**Resultado: COERENTE.** As 10 transiÃ§Ãµes nÃ£o-iniciais da matriz textual batem com o caminho principal do UML, incluindo os **trÃªs contextos distintos do Motorista** (ida laminaÃ§Ã£o, volta laminaÃ§Ã£o, entrega final), todos presentes como nÃ³s separados. Atores idÃªnticos. ReprovaÃ§Ã£o e reinÃ­cio de ciclo presentes e coerentes.

### Â§5.3 Rota Filial (texto Â§5.4 vs UML 06.3)

**Resultado: DIVERGÃŠNCIA APARENTE â€” DECISÃƒO NECESSÃRIA NO GATE 2.**

A matriz textual (Â§5.4, linha 2) diz:

> `Criada` â†’ **Vendedor** â†’ "Identificar prova â†’ Assinar â†’ Confirmar encaminhamento para o vendedor." â†’ `Encaminhada para o Vendedor`

JÃ¡ o UML (06.3) tem essa aÃ§Ã£o **posicionada na coluna 3Studio** (cabeÃ§alho `act_filial_c10003`/`c10004`) â€” o ID `act_filial_c10014` segue a numeraÃ§Ã£o das aÃ§Ãµes que estÃ£o sob aquela coluna. ReforÃ§a essa leitura o fato de o **mecanismo descrito** ser "encaminhamento p/ vendedor" (analogia direta com o "encaminhamento p/ laminaÃ§Ã£o" das rotas laminadas, onde 3Studio Ã© quem **encaminha**).

Ou seja, a matriz textual nomeia "Vendedor" como ator, mas o UML coloca a aÃ§Ã£o na coluna 3Studio. Faz mais sentido semÃ¢ntico ser **3Studio** (espelho de "Lam. Filial: 3Studio faz encaminhamento p/ laminaÃ§Ã£o" e "Lam. Matriz: 3Studio faz encaminhamento p/ laminaÃ§Ã£o").

**ImplicaÃ§Ã£o para a implementaÃ§Ã£o:** o item M-1 da decisÃ£o (Gate 2) precisa ser fechado com Mario:
- **OpÃ§Ã£o A** (seguir o texto da Â§5.4): ator = Vendedor. Mas isto cria um caso atÃ­pico â€” o Vendedor estaria "encaminhando para si mesmo" via assinatura.
- **OpÃ§Ã£o B** (seguir o UML 06.3 + analogia com Lam. Filial): ator = 3Studio. Mais consistente com o padrÃ£o das rotas Lam. *. Cria assimetria entre Rota Matriz (Vendedor faz Criadaâ†’Retirada) e Rota Filial (3Studio faz Criadaâ†’Encaminhada).
- **OpÃ§Ã£o C** (interpretaÃ§Ã£o alternativa): o Vendedor Ã© o ator porque ele Ã© quem assina ao receber a prova (analogia com Matriz onde Vendedor assina ao "retirar"). Nesse caso o nome do estado "Encaminhada para o Vendedor" descreve o resultado da aÃ§Ã£o do Vendedor, nÃ£o a aÃ§Ã£o de um terceiro encaminhando.

A OpÃ§Ã£o C Ã© compatÃ­vel tanto com o texto quanto com a semÃ¢ntica geral do sistema ("ator que assina = ator que executa a transiÃ§Ã£o"), e equivale operacionalmente Ã  OpÃ§Ã£o A.

### Â§5.4 Rota Lam. Filial (texto Â§5.5 vs UML 06.4)

**Resultado: COERENTE.** As 6 transiÃ§Ãµes nÃ£o-iniciais da matriz textual batem com o caminho principal do UML. Atores idÃªnticos: 3Studio (encaminhamento p/ laminaÃ§Ã£o), Motorista (ida laminaÃ§Ã£o), Clicheria (conclusÃ£o), Vendedor (LaminaÃ§Ã£o ConcluÃ­daâ†’Encaminhada para o Vendedor â€” coerente com a Â§5.5 que nomeia Vendedor), Vendedor (aprovaÃ§Ã£o), Clicheria (recebimento final).

**ObservaÃ§Ã£o:** nesta rota, o ator da transiÃ§Ã£o `LaminaÃ§Ã£o ConcluÃ­da â†’ Encaminhada para o Vendedor` Ã© **Vendedor** segundo o Requisitos Â§5.5 â€” e o UML 06.4 coloca essa aÃ§Ã£o na coluna do Vendedor. Mesma semÃ¢ntica que a transiÃ§Ã£o equivalente da rota Filial Â§5.4 (matricidade discutida em Â§5.3 acima): ator que assina ao receber = Vendedor.

### Â§5.5 SumÃ¡rio de coerÃªncia

| Rota | Texto Â§5 â†” UML 06.x | Status |
|---|---|---|
| Matriz | Â§5.2 â†” 06.1 | âœ… COERENTE |
| Lam. Matriz | Â§5.3 â†” 06.2 | âœ… COERENTE (3 contextos de Motorista distintos confirmados) |
| Filial | Â§5.4 â†” 06.3 | âš ï¸ DIVERGÃŠNCIA APARENTE na transiÃ§Ã£o Criadaâ†’Encaminhada (texto: Vendedor; UML: coluna 3Studio). **DecisÃ£o necessÃ¡ria no Gate 2.** |
| Lam. Filial | Â§5.5 â†” 06.4 | âœ… COERENTE |

### Â§5.6 ConfirmaÃ§Ã£o dos 3 contextos do Motorista

Os trÃªs contextos diferenciados do Motorista citados na enumeraÃ§Ã£o inicial sÃ£o **confirmados** pelo drawio:

| Contexto | Rotas em que aparece | Estado destino | Confirmado em UML |
|---|---|---|---|
| **(ida laminaÃ§Ã£o)** | Lam. Matriz, Lam. Filial | Com Motorista (ida laminaÃ§Ã£o) | Aba 06.2 (nÃ³ c10019) + Aba 06.4 (nÃ³ c10019) |
| **(volta laminaÃ§Ã£o)** | Lam. Matriz **apenas** | Com Motorista (volta laminaÃ§Ã£o) | Aba 06.2 (nÃ³ c10023) |
| **(entrega final)** | Matriz, Lam. Matriz | Com Motorista (entrega final) | Aba 06.1 (nÃ³ c10024) + Aba 06.2 (nÃ³ c10034) |

Cada contexto tem **rÃ³tulo de aÃ§Ã£o distinto** no UML ("travessia (ida laminaÃ§Ã£o)" / "travessia (volta laminaÃ§Ã£o)" / "entrega final"), confirmando o requisito do escopo do Componente 11 v4.0 ("trÃªs contextos distintos de 'Com Motorista': ida laminaÃ§Ã£o, volta laminaÃ§Ã£o, entrega final â€” cada um Ã© um estado distinto").

---

## Resumo executivo para uso no Gate 2

1. **A Matriz canÃ´nica estÃ¡ na SeÃ§Ã£o 5 do Requisitos v4.0**, decomposta em 4 sub-tabelas (5.2â€“5.5) + transversais (5.6). Total de transiÃ§Ãµes vÃ¡lidas (excluindo a criaÃ§Ã£o inicial e excluindo reprovaÃ§Ã£o/cancelamento transversais): **5 (Matriz) + 10 (Lam. Matriz) + 3 (Filial) + 6 (Lam. Filial) = 24 transiÃ§Ãµes rota-especÃ­ficas**. CritÃ©rios de aceitaÃ§Ã£o do Componente 11 mencionam "11 transiÃ§Ãµes Lam. Matriz" e "7 transiÃ§Ãµes Lam. Filial" â€” esses nÃºmeros incluem a criaÃ§Ã£o como transiÃ§Ã£o contada (Lam. Matriz: 10+1=11; Lam. Filial: 6+1=7).
2. **InventÃ¡rio de 14 estados** (incluindo Cancelada transversal) estÃ¡ literalmente listado em Â§1.1.1 acima. Nomes canÃ´nicos a usar em `StatusProvaEnum`.
3. **PrincÃ­pio de invariÃ¢ncia (DAT Â§4.2)** + **fluxo obrigatÃ³rio de mudanÃ§a em 5 passos (DAT Â§4.5)** Ã© mandatÃ³rio â€” espelha exatamente o que o CLAUDE.md jÃ¡ documenta na seÃ§Ã£o "Como adicionar valor ao enum `rota_enum`" e "Como adicionar valor a `StatusProvaEnum`".
4. **Cobertura â‰¥95% na mÃ¡quina de estados** Ã© dito 3x: DAT Â§3 (Camada 1), DAT Â§4.2 (justificativa de invariÃ¢ncia), Backlog Â§5 Componente 11 (CritÃ©rio de AceitaÃ§Ã£o). Ã‰ um deliverable testÃ¡vel.
5. **DivergÃªncia Ãºnica detectada** (Gate 2 deve resolver): ator da transiÃ§Ã£o `Criada â†’ Encaminhada para o Vendedor` na **Rota Filial** â€” texto Â§5.4 diz "Vendedor"; UML 06.3 posiciona a aÃ§Ã£o na coluna 3Studio. RecomendaÃ§Ã£o tÃ©cnica: aderir ao texto (ator = Vendedor) com nota explicativa, pois o texto Ã© a fonte canÃ´nica declarada explicitamente em "A Matriz de TransiÃ§Ãµes da v4.0 (Requisitos v4.0, SeÃ§Ã£o 5) Ã© a especificaÃ§Ã£o canÃ´nica" (Backlog C11 Justificativa).
6. **RNF "< 1 segundo" para transiÃ§Ã£o NÃƒO EXISTE na v4.0.** Os RNFs anÃ¡logos sÃ£o RNF-002 (â‰¤ 2 s para captura â†’ tela de assinatura) e RNF-009 (â‰¤ 3 cliques para concluir a transiÃ§Ã£o apÃ³s identificaÃ§Ã£o).
7. **RBAC dual layer (DAT Â§7)** jÃ¡ estÃ¡ implementado na Wave 1 v4.0 (Componente 05) â€” Componente 11 sÃ³ precisa usar `access_required("transicoes.executar")` ou similar (a chave exata vem da `shared/access-matrix.json` atual, ou do que for criado para C11).
