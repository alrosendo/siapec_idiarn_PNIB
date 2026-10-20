# Wizard: Identificar agora (PNIB)

Fluxo reutilizável aberto a partir de nascimento, GTA (passo 3), vacinação brucelose, menu `Identificação (PNIB)` ou tela de saldo (`sem ID`).

Estilo operacional: rápido como SIAPEC; grava animal individual + evento imutável + fila de sync com a Base Central.

---

## Entrada e contexto

| Parâmetro de abertura | Origem | Efeito |
|----------------------|--------|--------|
| `propriedade_id` | tela pai | pré-preenchido, readonly |
| `exploracao_id` | tela pai | pré-preenchido, readonly |
| `sexo` / `faixa` | saldo ou GTA | filtra estoque e valida cota |
| `quantidade_sugerida` | GTA / nascimento / vacina | teto do lote |
| `modo` | `aplicacao` \| `perda` \| `substituicao` \| `estoque` | define passos |
| `retorno` | callback da tela pai | devolve lista de IDs aplicados |

**Perfis que podem abrir**

| Perfil | Aplicar | Perda/substituição | Solicitar estoque |
|--------|---------|--------------------|-------------------|
| Produtor | sim (se habilitado) | sim (declara) | sim |
| Veterinário credenciado | sim | sim (no ato sanitário) | não (só consulta) |
| Fiscal / OESA | sim | homologa / aplica | distribui |
| Admin | configura parâmetros | — | — |

**Bloqueios na abertura**

- propriedade interditada
- exploração sem espécie bovino/búfalo
- produtor sem habilitação PNIB (parametrizável)
- estoque zerado **e** modo = aplicação (oferece ir para solicitação)

---

## Mapa do wizard

```text
Identificar agora
├── Passo A — Contexto e objetivo
├── Passo B — Estoque de identificadores     (ou solicitar)
├── Passo C — Aplicação no animal / lote
├── Passo D — Revisão e confirmação
└── Pós-gravação — retorno à tela pai + sync

Atalhos laterais (mesmo domínio, telas irmãs)
├── Solicitar identificadores
├── Declarar perda
└── Substituir identificador
```

---

## Passo A — Contexto e objetivo

| Campo | Tipo | Obrig. | Notas |
|-------|------|--------|-------|
| Propriedade | readonly | — | |
| Exploração | readonly | — | |
| Objetivo | select | sim | `Identificar saldo sem ID` · `Identificar nascidos` · `Completar GTA` · `Habilitar vacinação` · `Avulso` |
| Quantidade planejada | number | sim | ≤ saldo sem ID na faixa (se filtrado) ou livre se avulso |
| Sexo (filtro) | select | condicional | obrig. se veio do saldo/GTA |
| Faixa etária (filtro) | select | condicional | idem |
| Data da aplicação | date | sim | default hoje; ≤ hoje |
| Local | select | sim | propriedade / curral / evento |
| Evento (se local = evento) | select | sim | |

**Resumo lateral**

```text
Saldo sem ID (filtro): 32
Estoque disponível: 80
Planejado: 23
Após gravar → sem ID: 9
```

Botões: `Cancelar` · `Próximo`

---

## Passo B — Estoque de identificadores

### B.1 Seleção de faixa de IDs

| Campo | Tipo | Obrig. | Validação |
|-------|------|--------|-----------|
| Origem do estoque | select | sim | lote distribuído ao produtor / ao escritório / ao vet |
| Lote / remessa | select | sim | só lotes com saldo > 0 |
| Faixa inicial | texto/número | sim | pertence ao lote |
| Faixa final | texto/número | condicional | se modo faixa; senão usa lista |
| Modo de consumo | radio | sim | `Faixa sequencial` · `Seleção manual` · `Leitor RFID/código` |

**Lista de disponíveis (após escolher lote)**

| Coluna | Conteúdo |
|--------|----------|
| ID oficial | código a gravar no animal |
| Brinco visual | se houver |
| Tipo dispositivo | convencional / eletrônico (param MAPA) |
| Status estoque | disponível / reservado / aplicado / perdido |
| Ação | reservar para este wizard |

**Regras**

1. Só entram IDs `disponivel` (ou `reservado` por este usuário/sessão).
2. `quantidade selecionada` deve ser = `quantidade planejada` do passo A (ou ≤, com aviso).
3. Reserva otimista por TTL (ex.: 30 min) para evitar dois produtores pegarem o mesmo ID.
4. Se estoque insuficiente → CTA `Solicitar identificadores` (tela irmã).

### B.2 Tela irmã — Solicitar identificadores

| Campo | Tipo | Obrig. |
|-------|------|--------|
| Propriedade / exploração | select | sim |
| Quantidade solicitada | number | sim |
| Tipo dispositivo | select | sim |
| Justificativa | texto | se qtd > cota |
| Escritório de retirada | select | sim |

Workflow: `solicitado` → `em análise OESA` → `aprovado` → `entregue` (gera linhas no estoque do produtor).

Botões passo B: `Voltar` · `Próximo` (com N IDs reservados)

---

## Passo C — Aplicação no animal / lote

Três submodos (mesmo passo, UI diferente):

### C.1 Faixa sequencial (mais fluido — estilo SIAPEC)

Para cada cabeça do lote, o sistema associa o próximo ID da reserva a um “slot” animal.

| Campo por linha | Tipo | Obrig. | Default |
|-----------------|------|--------|---------|
| ID oficial | readonly | — | da reserva |
| Sexo | select | sim | filtro do passo A |
| Data nascimento | date | sim | estimado pela faixa (editável) |
| Faixa | readonly/calc | — | pela data |
| Categoria | select | não | cria/recria/etc. |
| Nome / manejo interno | texto | não | controle do produtor |
| Mãe (ID) | busca | não | se conhecida |
| Observação | texto | não | |

Ações em massa: `Preencher sexo = F` · `Nascer = data fixa` · `Aplicar faixa etária padrão`.

### C.2 Seleção do rebanho sem ID (quando já existe “slot” agregado)

Não cria nascimento novo: apenas **converte** parte do saldo sem ID em animais identificados.

| Campo | Tipo | Obrig. |
|-------|------|--------|
| Célula de saldo (sexo × faixa) | readonly | — |
| Qtd a identificar nesta célula | number | sim |
| Lista ID → (sexo/faixa já da célula) | auto | sim |

Nascimento fica implícito/desconhecido: usa data estimada (início/meio da faixa) marcada como `estimada=true`.

### C.3 Leitor RFID / código

| Campo | Tipo | Obrig. |
|-------|------|--------|
| Campo de leitura | input foco contínuo | sim |
| Feedback bip | UI | — | OK / ID inválido / já aplicado |
| Buffer da sessão | lista | — | IDs lidos nesta sessão |

Ao ler: se ID está na reserva → adiciona linha; se não → erro “fora do estoque reservado”.

### Validações do passo C

| Regra | Mensagem |
|-------|----------|
| ID já aplicado em outro animal | “Identificador em uso” |
| Sexo/faixa foge do filtro da GTA/vacina | “Fora do embarque/lote sanitário” |
| Data nascimento > data aplicação | bloqueio |
| Data nascimento incompatível com faixa do saldo | aviso + confirmação OESA se grave |
| Duplicata na própria lista | bloqueio |
| Qtd linhas ≠ planejada | aviso; pode reduzir planejado |

---

## Passo D — Revisão e confirmação

Espelho readonly:

- propriedade / exploração / data / responsável
- tabela final: ID · sexo · nascimento · faixa · origem do evento
- efeito no saldo: `sem ID −N` · `com ID +N`
- termo: “declaro a aplicação dos identificadores os animais descritos”

Checkbox obrigatório: termo de responsabilidade.  
Botões: `Voltar` · `Confirmar identificação`

### Pós-confirmação

1. Cria/atualiza registros `Animal` (`status=ativo`).
2. Baixa IDs do estoque (`aplicado`).
3. Evento imutável `IDENTIFICACAO_APLICADA`.
4. Recalcula saldo híbrido.
5. Enfileira sync Base Central (um a um ou lote).
6. Retorna à tela pai com `ids[]` (GTA preenche passo 3; vacina preenche lista; nascimento fecha modal).

**Tela sucesso**

```text
23 animais identificados
Sync: 20 OK · 3 pendentes
[ Ver animais ] [ Identificar mais ] [ Voltar ]
```

---

## Tela irmã — Declarar perda

| Campo | Tipo | Obrig. |
|-------|------|--------|
| ID / brinco | busca | sim |
| Tipo | select | sim | perda de brinco · dano · extravio estoque (ainda não aplicado) · furto |
| Data | date | sim |
| Boletim / documento | upload | condicional |
| Solicitar substituto | toggle | não |

Efeitos:

- se ID **aplicado**: animal fica `identificador_pendente` (não some do rebanho); bloqueia GTA até substituição (param).
- se ID **em estoque**: status estoque `perdido`; não conta como animal.

Workflow OESA se tipo = furto ou acima da cota mensal de perdas.

---

## Tela irmã — Substituir identificador

| Campo | Tipo | Obrig. |
|-------|------|--------|
| Animal / ID antigo | busca | sim |
| Motivo | select | sim | perda · dano · leitura falha · erro de aplicação |
| Novo ID (do estoque) | select/leitura | sim |
| Data substituição | date | sim |
| Manter histórico do ID antigo | readonly | — | sempre |

Efeitos:

- ID antigo → `substituido` (histórico preservado na timeline).
- ID novo → `aplicado`.
- Evento `IDENTIFICADOR_SUBSTITUIDO` (id_antigo, id_novo).
- Sync MAPA com operação de substituição (contrato federal).

---

## Estados do identificador (estoque → vida)

```text
disponivel → reservado → aplicado → substituido
                 ↘ perdido (estoque)
aplicado → (perda brinco) → animal.identificador_pendente → aplicado (novo)
```

## Estados de sync

| Status | UI |
|--------|-----|
| `pendente` | badge amarelo |
| `ok` | badge verde |
| `erro` | badge vermelho + reprocessar (OESA) |

---

## Motor de regras (quando o wizard é obrigatório)

```text
SE origem = vacinacao_brucelose AND animal_sem_id
  ENTÃO wizard obrigatório antes de gravar vacina

SE origem = gta AND regra_exigir_ids
  ENTÃO wizard obrigatório até count(ids) atingir meta

SE origem = nascimento AND etapa >= 3 AND param_identificar_nascidos
  ENTÃO sugerir wizard (obrigatório só se param estadual ligar)

SE divergencia_saldo
  ENTÃO permitir só modo conversao_saldo (C.2) via regularização
```

---

## Critérios de aceite (MVP)

- [ ] Reservar N IDs e aplicar em lote sequencial em menos de 2 minutos (23 cabeças mock)
- [ ] Conversão de saldo sem ID → animais sem criar nascimento falso (flag `nascimento_estimado`)
- [ ] Perda + substituição preservam timeline
- [ ] Retorno para GTA e vacina preenche listas automaticamente
- [ ] Estoque insuficiente redireciona para solicitação
- [ ] Sync enfileirado mesmo se Base Central offline (retry)
