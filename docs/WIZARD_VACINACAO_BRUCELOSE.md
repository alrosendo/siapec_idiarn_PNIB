# Wizard: Vacinação brucelose com vínculo de IDs (PNIB / PNCEBT)

Fluxo do portal do **veterinário credenciado** (e, quando parametrizado, agente vacinador sob RT). É o principal **gatilho da Etapa 3 do PNIB**: não se declara vacina de brucelose sem animal identificado.

Encadeia com o wizard [Identificar agora](./WIZARD_IDENTIFICAR_AGORA.md) quando houver cabeça sem ID no lote elegível.

---

## Contexto legal (operacional)

| Tema | Comportamento no sistema |
|------|---------------------------|
| PNCEBT | vacinação de fêmeas em faixa etária elegível (parametrizável; tipicamente 3–8 meses — confirmar norma vigente no admin) |
| PNIB Etapa 3 | manejo sanitário = identificação individual obrigatória + envio à Base Central |
| SIAPEC-like | receituário → declaração → relatório mensal; fiscal só na exceção |

---

## Mapa do fluxo completo

```text
Veterinário
├── 1. Receituário (compra de vacina)
├── 2. Declarar vacinação (wizard)
│     ├── Passo 1 — Contexto (propriedade / data / vacina)
│     ├── Passo 2 — Elegíveis e quantidades
│     ├── Passo 3 — Vincular IDs          ← obrigatório PNIB
│     │     └── [Identificar agora] se faltar ID
│     ├── Passo 4 — Dados da aplicação
│     └── Passo 5 — Revisão e envio
├── 3. Consulta / 2ª via / cancelamento (com regra)
└── 4. Relatório mensal (consolida declarações)
```

Telas de apoio: agentes vacinadores, estoque de vacina do RT, resultados de exame (fluxo separado).

---

## Pré-requisitos (antes do wizard)

| Requisito | Se faltar |
|-----------|-----------|
| Vet credenciado ativo no município/UF | bloqueia |
| Produtor/propriedade cadastrados | bloqueia |
| Exploração bovinos/búfalos | bloqueia |
| Receituário com saldo de doses | bloqueia ou avisa (param) |
| Propriedade sem interdição de brucelose incompatível | bloqueia |
| Agente vacinador cadastrado (se não for o próprio RT) | bloqueia passo 4 |

---

## Tela 0 — Receituário (antecedente)

| Campo | Tipo | Obrig. |
|-------|------|--------|
| RT / CRMV | readonly | — |
| Propriedade / produtor | busca | sim |
| Quantidade de doses | number | sim |
| Laboratório / partida (se já conhecida) | select/texto | condicional |
| Revenda | select | sim |
| Data receita | date | sim |
| Validade receita | date | sim |

Estados: `emitido` → `utilizado parcial` → `esgotado` → `cancelado`.  
A declaração de vacinação **debita** doses do receituário.

---

## Passo 1 — Contexto da declaração

| Campo | Tipo | Obrig. | Validação |
|-------|------|--------|-----------|
| Propriedade | select/busca | sim | na área do RT |
| Exploração | select | sim | bovino/búfalo |
| Data da vacinação | date | sim | ≤ hoje; dentro da validade da vacina |
| Receituário | select | sim | com saldo ≥ 1 |
| Vacina (produto) | select | sim | homologada brucelose |
| Partida / lote industrial | texto | sim | |
| Validade do produto | date | sim | ≥ data vacinação |
| Responsável técnico | readonly | — | logado |
| Agente vacinador | select | sim | cadastrado sob o RT |
| Campanha / reforço | select | não | se houver campanha estadual |

**Banner PNIB**

```text
Etapa 3 — Toda fêmea vacinada contra brucelose deve estar identificada
individualmente e sincronizada com a Base Central.
```

Botões: `Cancelar` · `Próximo`

---

## Passo 2 — Elegíveis e quantidades

Objetivo: definir **quantas** e **quais células de saldo** entram no lote vacinal (visão SIAPEC), antes de individualizar.

### 2.1 Resumo automático da exploração

| Coluna | Conteúdo |
|--------|----------|
| Sexo | F (machos normalmente fora — param) |
| Faixa etária | só faixas elegíveis PNCEBT |
| Saldo | total na célula |
| Já vacinadas (janela) | count com evento recente |
| Com ID / Sem ID | do saldo híbrido |
| Elegíveis estimados | saldo − já vacinadas − bloqueios |

### 2.2 Campos de entrada

| Campo | Tipo | Obrig. |
|-------|------|--------|
| Grade: doses a aplicar por faixa | number | sim |
| Incluir só não vacinadas na janela | toggle | default on |
| Observação de manejo | texto | não |

**Validações**

- soma doses > 0  
- soma doses ≤ saldo elegível  
- soma doses ≤ saldo do receituário  
- se `sem ID` na célula > 0 e PNIB Etapa 3: pode avançar, mas passo 3 exigirá identificação  

**Lateral**

```text
Doses no receituário: 40
Doses deste lote: 18
Fêmeas elegíveis: 22 (14 com ID · 8 sem ID)
```

---

## Passo 3 — Vincular identificadores (núcleo PNIB)

Meta: `count(animais vinculados) = doses do passo 2`.

### Layout

```text
Lote vacinal: 18 doses
Vinculadas: 10          Faltam: 8

[ Selecionar do rebanho ]  [ Ler RFID ]  [ Importar planilha ]  [ Identificar agora ]

Lista vinculada
ID          Sexo  Nasc.       Faixa   Última brucelose   Sync
BR-…        F     2025-11-02  0-12    —                  OK
…
```

### Modos de vínculo

| Modo | Comportamento |
|------|----------------|
| Selecionar do rebanho | multi-select em fêmeas elegíveis **com ID** na exploração |
| Ler RFID | mesma UX do wizard identificar; só aceita IDs já aplicados |
| Importar planilha | colunas `id_oficial` (+ opcional brinco); valida linha a linha |
| Identificar agora | abre wizard; ao retornar, IDs novos já vêm marcados no lote |

### Validações por animal

| Regra | Severidade |
|-------|------------|
| Sexo elegível (param: tipicamente F) | erro |
| Idade/faixa dentro da janela PNCEBT | erro (ou aviso + justificativa OESA) |
| Já vacinada na janela de reforço indevido | erro |
| Status ≠ ativo | erro |
| Exploração atual ≠ origem | erro |
| Sync MAPA = erro bloqueante | erro (param) |
| Sync pendente | aviso (permite gravar local + reenviar) |
| Animal já na lista | erro duplicata |
| Quantidade vinculada ≠ doses | erro ao avançar |

### Botão Identificar agora (8 sem ID)

Abre [WIZARD_IDENTIFICAR_AGORA.md](./WIZARD_IDENTIFICAR_AGORA.md) com:

```text
objetivo = habilitar_vacinacao
sexo = F
faixa = (faixas do passo 2 com sem_ID)
quantidade_sugerida = faltantes
retorno = anexar ids ao lote vacinal
```

Não permite concluir o passo 3 enquanto `faltam > 0`.

Botões: `Voltar` · `Próximo` (só com 100% vinculado)

---

## Passo 4 — Dados da aplicação

| Campo | Tipo | Obrig. | Notas |
|-------|------|--------|-------|
| Via de aplicação | select | sim | conforme bula/param |
| Dose (ml) | number | sim | default do produto |
| Local anatômico | select | não | |
| Temperatura armazenamento | number | não | boa prática |
| Hora início / fim | time | não | |
| Reações adversas no lote | toggle+texto | se sim | gera ocorrência |
| Anexos (fotos, ata) | upload | não | |
| Declaração do RT | checkbox | sim | texto legal curto |

Se agente vacinador ≠ RT: checkbox extra “sob supervisão do RT logado”.

---

## Passo 5 — Revisão e envio

Espelho readonly:

1. Propriedade, exploração, data, RT, agente  
2. Vacina, partida, validade, receituário  
3. Tabela de animais (ID, nascimento, faixa)  
4. Doses debitadas  
5. Destino sync: Base Estadual + Base Central PNIB  

Botões: `Voltar` · `Confirmar declaração`

### Pós-confirmação (transação)

1. Cria cabeçalho `VacinacaoBrucelose` (`status=confirmada`).  
2. Cria N eventos imutáveis `VACINA_BRUCELOSE` ligados a cada `animal_id`.  
3. Debita receituário.  
4. Atualiza flags sanitárias da propriedade/exploração.  
5. Enfileira sync PNIB (animal + evento) e integração sanitária estadual.  
6. Disponibiliza PDF/comprovante e item no relatório mensal.

**Tela sucesso**

```text
Vacinação registrada · Protocolo VN-2026-000123
18 animais · 18 eventos
Sync PNIB: 15 OK · 3 na fila
[ Imprimir ] [ Nova declaração ] [ Ver propriedade ]
```

---

## Cancelamento e retificação

| Ação | Quem | Regra |
|------|------|-------|
| Cancelar declaração | RT (prazo curto) / OESA | só se sync ainda não consumido **ou** com estorno oficial |
| Retificar partida/data | OESA | gera evento de correção; mantém audit trail |
| Remover 1 animal | OESA | estorna 1 dose no receituário se permitido |

Nunca apagar evento: status `cancelado` + motivo.

---

## Relatório mensal (fechamento SIAPEC-like)

| Campo | Tipo |
|-------|------|
| Mês/ano de referência | select |
| Lista de declarações do RT | readonly |
| Totais por município / produto / partida | agregados |
| Pendências de sync | lista |
| Protocolo de entrega | gerado no envio |

Estados: `rascunho` → `enviado` → `homologado OESA` / `devolvido`.

---

## Filas OESA relacionadas

| Fila | Gatilho |
|------|---------|
| Vacinação fora da faixa etária com justificativa | aviso confirmado pelo RT |
| Reação adversa | toggle no passo 4 |
| Sync PNIB com erro persistente | N retries |
| Uso de doses > índice esperado da propriedade | analítico |
| Declaração sem receituário (exceção) | se param permitir emergência |

---

## Regras PNIB × etapa (resumo)

```text
SE etapa >= 3 OR param_antecipar_brucelose_ids
  ENTÃO passo 3 exige 100% IDs

SE animal elegível sem ID
  ENTÃO oferecer Identificar agora (obrigatório para fechar)

SE vacina gravada
  ENTÃO evento individual + sync Base Central
  ENTÃO animal fica apto a GTA com ID já listável

SE etapa < 3 AND param_piloto = false
  ENTÃO (somente transição) permitir declaração agregada legada
       — NÃO recomendado para IDIARN greenfield; manter desligado
```

Para o desenho IDIARN + PNIB: **nunca** gravar brucelose só por quantidade sem ID.

---

## Integração com GTA e saldo

| Depois da vacina | Efeito |
|------------------|--------|
| Saldo híbrido | `com ID` permanece; evento sanitário na timeline |
| GTA | animais aparecem na busca do passo 3 com badge “Brucelose OK / data” |
| Ficha sanitária | inclui consolidado da declaração |
| Pendências | remove pendência de campanha se houver |

---

## Critérios de aceite (MVP)

- [ ] Não avança passo 3 com `faltam > 0`
- [ ] Identificar agora retorna e completa o lote sem retrabalho
- [ ] Debito correto do receituário (parcial e total)
- [ ] Um evento por animal + protocolo único de cabeçalho
- [ ] Cancelamento preserva auditoria
- [ ] Relatório mensal lista a declaração no mesmo dia
- [ ] Simulação Etapa 3: 8 sem ID → wizard → 18 vacinadas → 18 sync enfileirados

---

## Wireflow condensado

```text
[Receituário]
     → [1 Contexto]
     → [2 Elegíveis / doses]
     → [3 IDs] ──faltou ID──→ [Identificar agora] ──volta──→ [3 IDs]
     → [4 Aplicação]
     → [5 Confirmar]
     → [Sucesso + sync]
     → (fim do mês) [Relatório mensal]
```
