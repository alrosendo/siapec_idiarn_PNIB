from __future__ import annotations

import json
from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Animal, DeclaracaoRebanho, EventoAnimal, Exploracao, SaldoFaixa
from app.schemas.dto import (
    DeclaracaoOut,
    MorteCreate,
    NascimentoCreate,
    SaldoResumoOut,
)
from app.services.faixa import faixa_por_nascimento
from app.services.saldo import ajustar_saldo, resumo_saldo


def _femeas_adultas(db: Session, exploracao_id: int) -> int:
    rows = db.scalars(
        select(SaldoFaixa).where(
            SaldoFaixa.exploracao_id == exploracao_id,
            SaldoFaixa.sexo == "F",
            SaldoFaixa.faixa.in_(("25-36", "36+")),
        )
    ).all()
    return sum(r.quantidade for r in rows)


def _nascimentos_mes(db: Session, exploracao_id: int, ref: date) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(DeclaracaoRebanho.quantidade), 0)).where(
            DeclaracaoRebanho.exploracao_id == exploracao_id,
            DeclaracaoRebanho.tipo == "nascimento",
            DeclaracaoRebanho.status != "estornada",
            extract("year", DeclaracaoRebanho.data_evento) == ref.year,
            extract("month", DeclaracaoRebanho.data_evento) == ref.month,
        )
    )
    return int(total or 0)


def _mortes_mes(db: Session, exploracao_id: int, ref: date) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(DeclaracaoRebanho.quantidade), 0)).where(
            DeclaracaoRebanho.exploracao_id == exploracao_id,
            DeclaracaoRebanho.tipo == "morte",
            DeclaracaoRebanho.status != "estornada",
            extract("year", DeclaracaoRebanho.data_evento) == ref.year,
            extract("month", DeclaracaoRebanho.data_evento) == ref.month,
        )
    )
    return int(total or 0)


def _to_out(d: DeclaracaoRebanho) -> DeclaracaoOut:
    ids = json.loads(d.ids_json) if d.ids_json else []
    return DeclaracaoOut(
        id=d.id,
        exploracao_id=d.exploracao_id,
        tipo=d.tipo,
        data_evento=d.data_evento,
        sexo=d.sexo,
        faixa=d.faixa,
        quantidade=d.quantidade,
        ids_oficiais=ids,
        tipo_baixa=d.tipo_baixa,
        observacao=d.observacao,
        status=d.status,
        acima_indice=d.acima_indice,
        criado_em=d.criado_em,
    )


def declarar_nascimento(db: Session, payload: NascimentoCreate) -> tuple[DeclaracaoOut, SaldoResumoOut]:
    exp = db.get(Exploracao, payload.exploracao_id)
    if not exp:
        raise ValueError("Exploração não encontrada")
    if payload.quantidade <= 0:
        raise ValueError("Quantidade deve ser > 0")
    if payload.faixa != "0-12":
        raise ValueError("Nascimento deve ser declarado na faixa 0-12")

    adultas = _femeas_adultas(db, payload.exploracao_id)
    teto = max(int(adultas * settings.indice_paricao), 1 if adultas == 0 else 0)
    ja = _nascimentos_mes(db, payload.exploracao_id, payload.data_evento)
    if ja + payload.quantidade > teto and adultas > 0:
        raise ValueError(
            f"Acima do índice de parição do mês (máx. {teto}, já declarado {ja}). "
            f"Fêmeas adultas: {adultas}."
        )

    ajustar_saldo(db, payload.exploracao_id, payload.sexo, payload.faixa, payload.quantidade)

    ids = payload.ids_oficiais or []
    if ids and len(ids) > payload.quantidade:
        raise ValueError("Mais IDs do que a quantidade declarada")

    if ids:
        from app.schemas.dto import IdentificacaoItemIn

        itens = [
            IdentificacaoItemIn(
                id_oficial=i,
                sexo=payload.sexo,
                data_nascimento=payload.data_evento,
                nascimento_estimado=False,
            )
            for i in ids
        ]
        _aplicar_ids_inline(db, payload.exploracao_id, payload.data_evento, itens)

    decl = DeclaracaoRebanho(
        exploracao_id=payload.exploracao_id,
        tipo="nascimento",
        data_evento=payload.data_evento,
        sexo=payload.sexo,
        faixa=payload.faixa,
        quantidade=payload.quantidade,
        ids_json=json.dumps(ids) if ids else None,
        observacao=payload.observacao,
        status="confirmada",
        acima_indice=False,
    )
    db.add(decl)
    db.commit()
    db.refresh(decl)
    return _to_out(decl), resumo_saldo(db, payload.exploracao_id)


def _aplicar_ids_inline(db: Session, exploracao_id: int, data_evento: date, itens) -> None:
    from app.models import EstoqueIdentificador

    exp = db.get(Exploracao, exploracao_id)
    for item in itens:
        estoque = db.scalar(
            select(EstoqueIdentificador).where(
                EstoqueIdentificador.id_oficial == item.id_oficial,
                EstoqueIdentificador.propriedade_id == exp.propriedade_id,
            )
        )
        if not estoque or estoque.status not in {"disponivel", "reservado"}:
            raise ValueError(f"Identificador indisponível: {item.id_oficial}")
        if db.scalar(select(Animal).where(Animal.id_oficial == item.id_oficial)):
            raise ValueError(f"Identificador já aplicado: {item.id_oficial}")
        animal = Animal(
            exploracao_id=exploracao_id,
            id_oficial=item.id_oficial,
            brinco_visual=estoque.brinco_visual,
            sexo=item.sexo,
            data_nascimento=item.data_nascimento,
            nascimento_estimado=False,
            status="ativo",
            sync_status="pendente",
        )
        db.add(animal)
        db.flush()
        db.add(
            EventoAnimal(
                animal_id=animal.id,
                tipo="IDENTIFICACAO_APLICADA",
                data_evento=data_evento,
            )
        )
        db.add(
            EventoAnimal(
                animal_id=animal.id,
                tipo="NASCIMENTO",
                data_evento=data_evento,
            )
        )
        estoque.status = "aplicado"


def declarar_morte(db: Session, payload: MorteCreate) -> tuple[DeclaracaoOut, SaldoResumoOut]:
    exp = db.get(Exploracao, payload.exploracao_id)
    if not exp:
        raise ValueError("Exploração não encontrada")

    ids = payload.ids_oficiais or []
    qtd = payload.quantidade
    sexo = payload.sexo
    faixa = payload.faixa

    if ids:
        animais: list[Animal] = []
        for id_of in ids:
            a = db.scalar(
                select(Animal).where(
                    Animal.id_oficial == id_of,
                    Animal.exploracao_id == payload.exploracao_id,
                    Animal.status == "ativo",
                )
            )
            if not a:
                raise ValueError(f"Animal não disponível: {id_of}")
            animais.append(a)
        qtd = len(animais)
        # Debita por célula real de cada animal
        for a in animais:
            f = faixa_por_nascimento(a.data_nascimento)
            ajustar_saldo(db, payload.exploracao_id, a.sexo, f, -1)
            a.status = "morto" if payload.tipo_baixa == "morte" else payload.tipo_baixa
            db.add(
                EventoAnimal(
                    animal_id=a.id,
                    tipo="BAIXA_" + payload.tipo_baixa.upper(),
                    data_evento=payload.data_evento,
                )
            )
        sexo = animais[0].sexo if len(set(a.sexo for a in animais)) == 1 else None
        faixa = None
    else:
        if not sexo or not faixa or qtd <= 0:
            raise ValueError("Informe sexo, faixa e quantidade (ou lista de IDs)")
        # Baixa só no agregado (sem ID)
        resumo = resumo_saldo(db, payload.exploracao_id)
        cel = next((c for c in resumo.celulas if c.sexo == sexo and c.faixa == faixa), None)
        if not cel or cel.sem_id < qtd:
            raise ValueError(
                f"Saldo sem ID insuficiente em {sexo}/{faixa} "
                f"(disponível sem ID: {cel.sem_id if cel else 0}). "
                "Para baixar animal identificado, informe o ID."
            )
        ajustar_saldo(db, payload.exploracao_id, sexo, faixa, -qtd)

    resumo_atual = resumo_saldo(db, payload.exploracao_id)
    # total já debitado — índice usa saldo + mortes do mês (aproximação: saldo antes ≈ atual + qtd)
    base = resumo_atual.total + qtd
    teto = max(int(base * settings.indice_mortalidade_mes), 1)
    ja = _mortes_mes(db, payload.exploracao_id, payload.data_evento)
    acima = (ja + qtd) > teto

    status = "em_analise_oesa" if acima else "confirmada"
    decl = DeclaracaoRebanho(
        exploracao_id=payload.exploracao_id,
        tipo="morte",
        data_evento=payload.data_evento,
        sexo=sexo,
        faixa=faixa,
        quantidade=qtd,
        ids_json=json.dumps(ids) if ids else None,
        tipo_baixa=payload.tipo_baixa,
        observacao=payload.observacao
        or (f"Acima do índice de mortalidade (máx. {teto}/mês)" if acima else None),
        status=status,
        acima_indice=acima,
    )
    db.add(decl)
    db.commit()
    db.refresh(decl)
    return _to_out(decl), resumo_saldo(db, payload.exploracao_id)


def listar_declaracoes(
    db: Session,
    *,
    exploracao_id: int | None = None,
    status: str | None = None,
    tipo: str | None = None,
) -> list[DeclaracaoOut]:
    q = select(DeclaracaoRebanho).order_by(DeclaracaoRebanho.id.desc())
    if exploracao_id:
        q = q.where(DeclaracaoRebanho.exploracao_id == exploracao_id)
    if status:
        q = q.where(DeclaracaoRebanho.status == status)
    if tipo:
        q = q.where(DeclaracaoRebanho.tipo == tipo)
    return [_to_out(d) for d in db.scalars(q).all()]


def homologar_declaracao(db: Session, declaracao_id: int, aprovar: bool) -> DeclaracaoOut:
    d = db.get(DeclaracaoRebanho, declaracao_id)
    if not d:
        raise ValueError("Declaração não encontrada")
    if d.status != "em_analise_oesa":
        raise ValueError("Só declarações em análise podem ser homologadas/estornadas")

    if aprovar:
        d.status = "homologada"
    else:
        # Estorna efeito no saldo
        if d.tipo == "morte" and d.quantidade and d.sexo and d.faixa and not d.ids_json:
            ajustar_saldo(db, d.exploracao_id, d.sexo, d.faixa, d.quantidade)
        elif d.tipo == "morte" and d.ids_json:
            ids = json.loads(d.ids_json)
            for id_of in ids:
                a = db.scalar(select(Animal).where(Animal.id_oficial == id_of))
                if a and a.status in {"morto", "abate", "desaparecimento"}:
                    f = faixa_por_nascimento(a.data_nascimento)
                    ajustar_saldo(db, d.exploracao_id, a.sexo, f, 1)
                    a.status = "ativo"
        d.status = "estornada"
    db.commit()
    db.refresh(d)
    return _to_out(d)
