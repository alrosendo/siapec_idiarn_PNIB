# IDIARN × PNIB — especificação de telas

Sistema de defesa agropecuária com UX no estilo **SIAPEC** (saldo, GTA, autonomia do produtor) e motor de regras **PNIB** (identificação individual + sync Base Central).

Código do MVP: pasta local `/home/aloisio/projetos/siapec_idiarn_PNIB` (ainda sem GitHub).

## Documentos

| Doc | Conteúdo |
|-----|----------|
| [WIZARD_IDENTIFICAR_AGORA.md](./WIZARD_IDENTIFICAR_AGORA.md) | Estoque, aplicação, perda e substituição de identificadores |
| [WIZARD_VACINACAO_BRUCELOSE.md](./WIZARD_VACINACAO_BRUCELOSE.md) | Declaração PNCEBT com vínculo obrigatório de IDs (Etapa 3) |

## Encadeamento

```text
Saldo / GTA / Nascimento / Vacina
        │
        ▼
 Identificar agora ──► Animal + ID + sync
        │
        ▼
 Vacinação brucelose (100% IDs) ──► evento sanitário + sync
        │
        ▼
 GTA (lista IDs quando a regra exigir)
```

## Telas já prototipadas no frontend

- Início / propriedades seed
- Exploração (saldo híbrido + lista de animais)
- Identificação (aplicar IDs do estoque)
- Trânsito (emitir GTA)
- Sanidade (vacinação brucelose com IDs)
