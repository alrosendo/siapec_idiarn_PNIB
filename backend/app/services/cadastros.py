from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Produtor, Propriedade, Veterinario, VinculoPropriedade
from app.models.domain import TIPOS_VINCULO
from app.schemas.dto import (
    ProdutorCreate,
    ProdutorOut,
    ProdutorUpdate,
    PropriedadeCreate,
    PropriedadeDetalheOut,
    PropriedadeOut,
    PropriedadeUpdate,
    VeterinarioCreate,
    VeterinarioOut,
    VeterinarioUpdate,
    VinculoCreate,
    VinculoOut,
)


def _produtor_out(p: Produtor) -> ProdutorOut:
    return ProdutorOut(
        id=p.id,
        cpf_cnpj=p.cpf_cnpj,
        nome=p.nome,
        telefone=p.telefone,
        email=p.email,
        ativo=p.ativo,
    )


def _vinculo_out(v: VinculoPropriedade) -> VinculoOut:
    return VinculoOut(
        id=v.id,
        propriedade_id=v.propriedade_id,
        produtor_id=v.produtor_id,
        produtor_nome=v.produtor.nome,
        produtor_cpf_cnpj=v.produtor.cpf_cnpj,
        tipo_vinculo=v.tipo_vinculo,
        ativo=v.ativo,
        data_inicio=v.data_inicio,
        data_fim=v.data_fim,
        observacao=v.observacao,
        criado_em=v.criado_em,
    )


def _propriedade_out(p: Propriedade, com_vinculos: bool = False) -> PropriedadeOut | PropriedadeDetalheOut:
    base = {
        "id": p.id,
        "codigo": p.codigo,
        "nome": p.nome,
        "municipio": p.municipio,
        "uf": p.uf,
        "interditada": p.interditada,
        "produtor_id": p.produtor_id,
        "titular_nome": p.titular.nome if p.titular else None,
        "exploracoes": p.exploracoes or [],
    }
    if not com_vinculos:
        return PropriedadeOut(**base)
    ativos = [_vinculo_out(v) for v in p.vinculos if v.ativo]
    return PropriedadeDetalheOut(**base, vinculos=ativos)


# ---- Produtores ----

def listar_produtores(db: Session, apenas_ativos: bool = True) -> list[ProdutorOut]:
    q = select(Produtor).order_by(Produtor.nome)
    if apenas_ativos:
        q = q.where(Produtor.ativo.is_(True))
    return [_produtor_out(p) for p in db.scalars(q).all()]


def criar_produtor(db: Session, payload: ProdutorCreate) -> ProdutorOut:
    cpf = "".join(c for c in payload.cpf_cnpj if c.isdigit())
    if db.scalar(select(Produtor).where(Produtor.cpf_cnpj == cpf)):
        raise ValueError("CPF/CNPJ já cadastrado")
    p = Produtor(
        cpf_cnpj=cpf,
        nome=payload.nome.strip(),
        telefone=payload.telefone,
        email=payload.email,
        ativo=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _produtor_out(p)


def atualizar_produtor(db: Session, produtor_id: int, payload: ProdutorUpdate) -> ProdutorOut:
    p = db.get(Produtor, produtor_id)
    if not p:
        raise ValueError("Produtor não encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "cpf_cnpj" in data and data["cpf_cnpj"]:
        data["cpf_cnpj"] = "".join(c for c in data["cpf_cnpj"] if c.isdigit())
        outro = db.scalar(
            select(Produtor).where(Produtor.cpf_cnpj == data["cpf_cnpj"], Produtor.id != produtor_id)
        )
        if outro:
            raise ValueError("CPF/CNPJ já cadastrado")
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return _produtor_out(p)


# ---- Propriedades ----

def listar_propriedades(db: Session) -> list[PropriedadeOut]:
    rows = db.scalars(
        select(Propriedade)
        .options(joinedload(Propriedade.exploracoes), joinedload(Propriedade.titular))
        .order_by(Propriedade.nome)
    ).unique().all()
    return [_propriedade_out(p) for p in rows]


def obter_propriedade(db: Session, propriedade_id: int) -> PropriedadeDetalheOut:
    p = db.scalars(
        select(Propriedade)
        .where(Propriedade.id == propriedade_id)
        .options(
            joinedload(Propriedade.exploracoes),
            joinedload(Propriedade.titular),
            joinedload(Propriedade.vinculos).joinedload(VinculoPropriedade.produtor),
        )
    ).unique().first()
    if not p:
        raise ValueError("Propriedade não encontrada")
    return _propriedade_out(p, com_vinculos=True)  # type: ignore[return-value]


def criar_propriedade(db: Session, payload: PropriedadeCreate) -> PropriedadeDetalheOut:
    titular = db.get(Produtor, payload.produtor_id)
    if not titular or not titular.ativo:
        raise ValueError("Titular (produtor) inválido ou inativo")
    if db.scalar(select(Propriedade).where(Propriedade.codigo == payload.codigo)):
        raise ValueError("Código de propriedade já existe")

    prop = Propriedade(
        produtor_id=payload.produtor_id,
        codigo=payload.codigo.strip().upper(),
        nome=payload.nome.strip(),
        municipio=payload.municipio.strip(),
        uf=payload.uf.upper(),
        interditada=False,
    )
    db.add(prop)
    db.flush()
    db.add(
        VinculoPropriedade(
            propriedade_id=prop.id,
            produtor_id=payload.produtor_id,
            tipo_vinculo="proprietario",
            ativo=True,
            data_inicio=date.today(),
            observacao="Titular cadastral inicial",
        )
    )
    db.commit()
    return obter_propriedade(db, prop.id)


def atualizar_propriedade(
    db: Session, propriedade_id: int, payload: PropriedadeUpdate
) -> PropriedadeDetalheOut:
    p = db.get(Propriedade, propriedade_id)
    if not p:
        raise ValueError("Propriedade não encontrada")
    data = payload.model_dump(exclude_unset=True)
    if "codigo" in data and data["codigo"]:
        data["codigo"] = data["codigo"].strip().upper()
        outro = db.scalar(
            select(Propriedade).where(
                Propriedade.codigo == data["codigo"], Propriedade.id != propriedade_id
            )
        )
        if outro:
            raise ValueError("Código já existe")
    if "produtor_id" in data and data["produtor_id"]:
        tit = db.get(Produtor, data["produtor_id"])
        if not tit:
            raise ValueError("Novo titular inválido")
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    return obter_propriedade(db, propriedade_id)


# ---- Vínculos ----

def adicionar_vinculo(db: Session, propriedade_id: int, payload: VinculoCreate) -> VinculoOut:
    if payload.tipo_vinculo not in TIPOS_VINCULO:
        raise ValueError(f"Tipo inválido. Use: {', '.join(TIPOS_VINCULO)}")
    prop = db.get(Propriedade, propriedade_id)
    if not prop:
        raise ValueError("Propriedade não encontrada")
    prod = db.get(Produtor, payload.produtor_id)
    if not prod or not prod.ativo:
        raise ValueError("Produtor inválido ou inativo")

    existe = db.scalar(
        select(VinculoPropriedade).where(
            VinculoPropriedade.propriedade_id == propriedade_id,
            VinculoPropriedade.produtor_id == payload.produtor_id,
            VinculoPropriedade.tipo_vinculo == payload.tipo_vinculo,
            VinculoPropriedade.ativo.is_(True),
        )
    )
    if existe:
        raise ValueError("Já existe vínculo ativo deste tipo para este produtor")

    v = VinculoPropriedade(
        propriedade_id=propriedade_id,
        produtor_id=payload.produtor_id,
        tipo_vinculo=payload.tipo_vinculo,
        ativo=True,
        data_inicio=payload.data_inicio or date.today(),
        observacao=payload.observacao,
    )
    db.add(v)

    # Se for proprietário, atualiza titular cadastral
    if payload.tipo_vinculo == "proprietario":
        prop.produtor_id = payload.produtor_id

    db.commit()
    v = db.scalars(
        select(VinculoPropriedade)
        .where(VinculoPropriedade.id == v.id)
        .options(joinedload(VinculoPropriedade.produtor))
    ).first()
    return _vinculo_out(v)


def remover_vinculo(db: Session, propriedade_id: int, vinculo_id: int) -> VinculoOut:
    v = db.scalar(
        select(VinculoPropriedade)
        .where(
            VinculoPropriedade.id == vinculo_id,
            VinculoPropriedade.propriedade_id == propriedade_id,
        )
        .options(joinedload(VinculoPropriedade.produtor))
    )
    if not v:
        raise ValueError("Vínculo não encontrado")
    if not v.ativo:
        raise ValueError("Vínculo já está inativo")

    # Não permitir remover o último proprietário ativo
    if v.tipo_vinculo == "proprietario":
        outros = db.scalars(
            select(VinculoPropriedade).where(
                VinculoPropriedade.propriedade_id == propriedade_id,
                VinculoPropriedade.tipo_vinculo == "proprietario",
                VinculoPropriedade.ativo.is_(True),
                VinculoPropriedade.id != vinculo_id,
            )
        ).all()
        if not outros:
            raise ValueError("Não é possível excluir o único proprietário. Inclua outro antes.")

    v.ativo = False
    v.data_fim = date.today()
    db.commit()
    db.refresh(v)
    return _vinculo_out(v)


def tipos_vinculo() -> list[str]:
    return list(TIPOS_VINCULO)


def garantir_vinculos_seed(db: Session) -> None:
    """Backfill: propriedades sem vínculo ativo ganham proprietário a partir do titular."""
    props = db.scalars(select(Propriedade)).all()
    for p in props:
        tem = db.scalar(
            select(VinculoPropriedade).where(
                VinculoPropriedade.propriedade_id == p.id,
                VinculoPropriedade.ativo.is_(True),
            )
        )
        if not tem and p.produtor_id:
            db.add(
                VinculoPropriedade(
                    propriedade_id=p.id,
                    produtor_id=p.produtor_id,
                    tipo_vinculo="proprietario",
                    ativo=True,
                    data_inicio=date.today(),
                    observacao="Migrado do titular cadastral",
                )
            )
    db.commit()


# ---- Veterinários ----

def listar_veterinarios(db: Session, apenas_ativos: bool = True) -> list[VeterinarioOut]:
    q = select(Veterinario).order_by(Veterinario.nome)
    if apenas_ativos:
        q = q.where(Veterinario.ativo.is_(True))
    return [VeterinarioOut.model_validate(v) for v in db.scalars(q).all()]


def criar_veterinario(db: Session, payload: VeterinarioCreate) -> VeterinarioOut:
    existe = db.scalar(
        select(Veterinario).where(
            Veterinario.crmv == payload.crmv.strip(),
            Veterinario.uf_crmv == payload.uf_crmv.upper(),
        )
    )
    if existe:
        raise ValueError("CRMV já cadastrado nesta UF")
    v = Veterinario(
        crmv=payload.crmv.strip(),
        uf_crmv=payload.uf_crmv.upper(),
        nome=payload.nome.strip(),
        cpf="".join(c for c in (payload.cpf or "") if c.isdigit()) or None,
        telefone=payload.telefone,
        email=payload.email,
        ativo=True,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return VeterinarioOut.model_validate(v)


def atualizar_veterinario(
    db: Session, vet_id: int, payload: VeterinarioUpdate
) -> VeterinarioOut:
    v = db.get(Veterinario, vet_id)
    if not v:
        raise ValueError("Veterinário não encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "cpf" in data and data["cpf"]:
        data["cpf"] = "".join(c for c in data["cpf"] if c.isdigit())
    if "uf_crmv" in data and data["uf_crmv"]:
        data["uf_crmv"] = data["uf_crmv"].upper()
    for k, val in data.items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return VeterinarioOut.model_validate(v)
