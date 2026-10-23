from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.dto import (
    AnimalOut,
    AplicarIdentificacaoIn,
    AplicarIdentificacaoOut,
    DeclaracaoOut,
    ChegadaCreate,
    GTACreate,
    GTAOut,
    HomologarIn,
    MorteCreate,
    NascimentoCreate,
    ProdutorCreate,
    ProdutorOut,
    ProdutorUpdate,
    PropriedadeCreate,
    PropriedadeDetalheOut,
    PropriedadeOut,
    PropriedadeUpdate,
    SaldoResumoOut,
    VacinacaoCreate,
    VacinacaoOut,
    VeterinarioCreate,
    VeterinarioOut,
    VeterinarioUpdate,
    VinculoCreate,
    VinculoOut,
)
from app.services import cadastros, gta_service, identificacao, movimento, saldo, vacinacao

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "pnib_etapa": settings.pnib_etapa,
        "indice_paricao": settings.indice_paricao,
        "indice_mortalidade_mes": settings.indice_mortalidade_mes,
    }


# ---- Cadastros: produtores ----

@router.get("/produtores", response_model=list[ProdutorOut])
def listar_produtores(
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    return cadastros.listar_produtores(db, apenas_ativos=apenas_ativos)


@router.post("/produtores", response_model=ProdutorOut)
def criar_produtor(payload: ProdutorCreate, db: Session = Depends(get_db)):
    try:
        return cadastros.criar_produtor(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.patch("/produtores/{produtor_id}", response_model=ProdutorOut)
def atualizar_produtor(
    produtor_id: int, payload: ProdutorUpdate, db: Session = Depends(get_db)
):
    try:
        return cadastros.atualizar_produtor(db, produtor_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ---- Cadastros: propriedades + vínculos ----

@router.get("/propriedades", response_model=list[PropriedadeOut])
def listar_propriedades(db: Session = Depends(get_db)):
    return cadastros.listar_propriedades(db)


@router.post("/propriedades", response_model=PropriedadeDetalheOut)
def criar_propriedade(payload: PropriedadeCreate, db: Session = Depends(get_db)):
    try:
        return cadastros.criar_propriedade(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/propriedades/{propriedade_id}", response_model=PropriedadeDetalheOut)
def detalhe_propriedade(propriedade_id: int, db: Session = Depends(get_db)):
    try:
        return cadastros.obter_propriedade(db, propriedade_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.patch("/propriedades/{propriedade_id}", response_model=PropriedadeDetalheOut)
def atualizar_propriedade(
    propriedade_id: int, payload: PropriedadeUpdate, db: Session = Depends(get_db)
):
    try:
        return cadastros.atualizar_propriedade(db, propriedade_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/vinculos/tipos", response_model=list[str])
def tipos_vinculo():
    return cadastros.tipos_vinculo()


@router.post("/propriedades/{propriedade_id}/vinculos", response_model=VinculoOut)
def adicionar_vinculo(
    propriedade_id: int, payload: VinculoCreate, db: Session = Depends(get_db)
):
    try:
        return cadastros.adicionar_vinculo(db, propriedade_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete(
    "/propriedades/{propriedade_id}/vinculos/{vinculo_id}",
    response_model=VinculoOut,
)
def remover_vinculo(
    propriedade_id: int, vinculo_id: int, db: Session = Depends(get_db)
):
    try:
        return cadastros.remover_vinculo(db, propriedade_id, vinculo_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ---- Cadastros: veterinários RT ----

@router.get("/veterinarios", response_model=list[VeterinarioOut])
def listar_vets(apenas_ativos: bool = True, db: Session = Depends(get_db)):
    return cadastros.listar_veterinarios(db, apenas_ativos=apenas_ativos)


@router.post("/veterinarios", response_model=VeterinarioOut)
def criar_vet(payload: VeterinarioCreate, db: Session = Depends(get_db)):
    try:
        return cadastros.criar_veterinario(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.patch("/veterinarios/{vet_id}", response_model=VeterinarioOut)
def atualizar_vet(vet_id: int, payload: VeterinarioUpdate, db: Session = Depends(get_db)):
    try:
        return cadastros.atualizar_veterinario(db, vet_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ---- Exploração / operações ----

@router.get("/exploracoes/{exploracao_id}/saldo", response_model=SaldoResumoOut)
def obter_saldo(exploracao_id: int, db: Session = Depends(get_db)):
    try:
        return saldo.resumo_saldo(db, exploracao_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/exploracoes/{exploracao_id}/animais", response_model=list[AnimalOut])
def obter_animais(exploracao_id: int, db: Session = Depends(get_db)):
    return identificacao.listar_animais(db, exploracao_id)


@router.post("/exploracoes/nascimentos", response_model=DeclaracaoOut)
def nascimento(payload: NascimentoCreate, db: Session = Depends(get_db)):
    try:
        decl, _ = movimento.declarar_nascimento(db, payload)
        return decl
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/exploracoes/mortes", response_model=DeclaracaoOut)
def morte(payload: MorteCreate, db: Session = Depends(get_db)):
    try:
        decl, _ = movimento.declarar_morte(db, payload)
        return decl
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/declaracoes", response_model=list[DeclaracaoOut])
def declaracoes(
    exploracao_id: int | None = None,
    status: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return movimento.listar_declaracoes(
        db, exploracao_id=exploracao_id, status=status, tipo=tipo
    )


@router.get("/oesa/fila-mortalidade", response_model=list[DeclaracaoOut])
def fila_mortalidade(db: Session = Depends(get_db)):
    return movimento.listar_declaracoes(db, status="em_analise_oesa", tipo="morte")


@router.post("/oesa/declaracoes/{declaracao_id}/homologar", response_model=DeclaracaoOut)
def homologar(declaracao_id: int, payload: HomologarIn, db: Session = Depends(get_db)):
    try:
        return movimento.homologar_declaracao(db, declaracao_id, payload.aprovar)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/propriedades/{propriedade_id}/estoque-ids")
def estoque_ids(propriedade_id: int, db: Session = Depends(get_db)):
    rows = identificacao.listar_estoque(db, propriedade_id)
    return [
        {
            "id_oficial": r.id_oficial,
            "brinco_visual": r.brinco_visual,
            "status": r.status,
            "lote_remessa": r.lote_remessa,
        }
        for r in rows
    ]


@router.post("/identificacao/aplicar", response_model=AplicarIdentificacaoOut)
def aplicar_ids(payload: AplicarIdentificacaoIn, db: Session = Depends(get_db)):
    try:
        return identificacao.aplicar_identificacao(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/gtas", response_model=GTAOut)
def criar_gta(payload: GTACreate, db: Session = Depends(get_db)):
    try:
        return gta_service.emitir_gta(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/gtas", response_model=list[GTAOut])
def gtas(status: str | None = Query(default=None), db: Session = Depends(get_db)):
    return gta_service.listar_gtas(db, status=status)


@router.post("/gtas/{gta_id}/chegada", response_model=GTAOut)
def confirmar_chegada(gta_id: int, payload: ChegadaCreate, db: Session = Depends(get_db)):
    try:
        return gta_service.confirmar_chegada(db, gta_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/vacinacoes/brucelose", response_model=VacinacaoOut)
def vacinar(payload: VacinacaoCreate, db: Session = Depends(get_db)):
    try:
        return vacinacao.declarar_vacinacao(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
