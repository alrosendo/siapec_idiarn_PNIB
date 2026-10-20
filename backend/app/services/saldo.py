from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Animal, Exploracao, Propriedade, SaldoFaixa
from app.schemas.dto import SaldoCelulaOut, SaldoResumoOut
from app.services.faixa import faixa_por_nascimento


def resumo_saldo(db: Session, exploracao_id: int) -> SaldoResumoOut:
    exp = db.get(Exploracao, exploracao_id)
    if not exp:
        raise ValueError("Exploração não encontrada")
    prop = db.get(Propriedade, exp.propriedade_id)

    saldos = db.scalars(select(SaldoFaixa).where(SaldoFaixa.exploracao_id == exploracao_id)).all()
    animais = db.scalars(
        select(Animal).where(Animal.exploracao_id == exploracao_id, Animal.status == "ativo")
    ).all()

    com_id_map: dict[tuple[str, str], int] = {}
    for a in animais:
        key = (a.sexo, faixa_por_nascimento(a.data_nascimento))
        com_id_map[key] = com_id_map.get(key, 0) + 1

    celulas: list[SaldoCelulaOut] = []
    total = 0
    identificados = 0
    for s in sorted(saldos, key=lambda x: (x.sexo, x.faixa)):
        com = com_id_map.get((s.sexo, s.faixa), 0)
        # com_id não pode ultrapassar saldo na visão; divergência fica em sem_id negativo → clamp
        com_eff = min(com, s.quantidade)
        sem = max(s.quantidade - com_eff, 0)
        celulas.append(
            SaldoCelulaOut(
                sexo=s.sexo,
                faixa=s.faixa,
                quantidade=s.quantidade,
                com_id=com_eff,
                sem_id=sem,
            )
        )
        total += s.quantidade
        identificados += com_eff

    cobertura = (identificados / total * 100.0) if total else 0.0
    return SaldoResumoOut(
        exploracao_id=exploracao_id,
        propriedade_nome=prop.nome if prop else "",
        total=total,
        identificados=identificados,
        sem_id=max(total - identificados, 0),
        cobertura_pct=round(cobertura, 1),
        pnib_etapa=settings.pnib_etapa,
        celulas=celulas,
    )


def ajustar_saldo(db: Session, exploracao_id: int, sexo: str, faixa: str, delta: int) -> SaldoFaixa:
    saldo = db.scalar(
        select(SaldoFaixa).where(
            SaldoFaixa.exploracao_id == exploracao_id,
            SaldoFaixa.sexo == sexo,
            SaldoFaixa.faixa == faixa,
        )
    )
    if not saldo:
        saldo = SaldoFaixa(exploracao_id=exploracao_id, sexo=sexo, faixa=faixa, quantidade=0)
        db.add(saldo)
        db.flush()
    novo = saldo.quantidade + delta
    if novo < 0:
        raise ValueError(f"Saldo insuficiente em {sexo}/{faixa}")
    saldo.quantidade = novo
    return saldo


def count_animais_ativos(db: Session, exploracao_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Animal).where(
            Animal.exploracao_id == exploracao_id, Animal.status == "ativo"
        )
    ) or 0
