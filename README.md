# SIAPEC × IDIARN × PNIB

Sistema de defesa agropecuária para o **IDIARN** (RN), com UX no estilo **SIAPEC** (saldo, GTA, autonomia do produtor) e motor de regras do **PNIB** (identificação individual + sync Base Central).

## Decisão de repositório

- **Agora:** pasta local neste computador — `/home/aloisio/projetos/siapec_idiarn_PNIB`
- **GitHub:** só quando quiser backup/compartilhamento (podemos criar depois com `gh`)

## Stack (MVP)

| Camada | Tecnologia |
|--------|------------|
| API | FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod) |
| Front | Vue 3 + Vite + Vue Router |
| Docs | `docs/` (wizards PNIB) |

## Subir local (dev rápido)

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (outro terminal)
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000/docs  
- App: http://localhost:5173  

## Módulos do MVP

1. Cadastros: produtor, propriedade, vínculos, veterinário RT  
2. Saldo híbrido (agregado + com/sem ID)  
3. Nascimento / morte (índice de parição e mortalidade)  
4. Fila OESA para mortalidade acima do índice  
5. Wizard Identificar agora  
6. Emissão de GTA (com passo de IDs)  
7. Vacinação brucelose com vínculo de IDs  

Ver `docs/` para especificação de telas.

## Telas do front

| Rota | Função |
|------|--------|
| `/` | Início |
| `/cadastros` | Produtores, propriedades, vínculos, RTs |
| `/exploracao` | Saldo + nascimento + morte + histórico |
| `/identificar` | Aplicar IDs do estoque |
| `/transito` | Emitir GTA |
| `/vacina` | Brucelose com IDs |
| `/oesa` | Homologar/estornar mortalidade |

### Vínculos na propriedade

Tipos: proprietário, arrendatário, parceiro, comodato, posseiro, administrador, outro.  
Inclusão e exclusão (inativação) na tela **Cadastros → Propriedades e vínculos**.
