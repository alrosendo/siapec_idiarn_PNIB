from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Animal, GTA, GTAAnimal
from app.schemas.dto import GTACreate, GTAOut
from app.services.faixa import faixa_por_nascimento
from app.services.pnib_rules import gta_exige_ids
from app.services.saldo import ajustar_saldo


def emitir_gta(db: Session, payload: GTACreate) -> GTAOut:
    total = sum(q.quantidade for q in payload.quantidades)
    if total <= 0:
        raise ValueError("Informe ao menos uma cabeça")

    exige, erro = gta_exige_ids(
        total_cabecas=total,
        ids_informados=len(payload.ids_oficiais),
        finalidade=payload.finalidade,
        forcar=payload.forcar_exigir_ids,
    )
    if erro:
        raise ValueError(erro)

    cotas = {(q.sexo, q.faixa): q.quantidade for q in payload.quantidades}
    usados: Counter[tuple[str, str]] = Counter()

    animais: list[Animal] = []
    if payload.ids_oficiais:
        for id_of in payload.ids_oficiais:
            animal = db.scalar(
                select(Animal).where(
                    Animal.id_oficial == id_of,
                    Animal.exploracao_id == payload.exploracao_origem_id,
                    Animal.status == "ativo",
                )
            )
            if not animal:
                raise ValueError(f"Animal não disponível na origem: {id_of}")
            faixa = faixa_por_nascimento(animal.data_nascimento)
            key = (animal.sexo, faixa)
            if key not in cotas:
                raise ValueError(
                    f"Animal {id_of} fora das quantidades declaradas ({animal.sexo}/{faixa})"
                )
            usados[key] += 1
            if usados[key] > cotas[key]:
                raise ValueError(
                    f"Mais IDs do que a quantidade em {animal.sexo}/{faixa}"
                )
            animal.status = "em_transito"
            animais.append(animal)

        if exige and len(animais) != total:
            raise ValueError("Regra PNIB: todos os animais do embarque devem ter ID vinculado")

    # Debita saldo por célula (após validar IDs)
    for q in payload.quantidades:
        ajustar_saldo(db, payload.exploracao_origem_id, q.sexo, q.faixa, -q.quantidade)

    numero = f"GTA-RN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    gta = GTA(
        numero=numero,
        exploracao_origem_id=payload.exploracao_origem_id,
        destino_codigo=payload.destino_codigo,
        destino_nome=payload.destino_nome,
        finalidade=payload.finalidade,
        status="emitida",
        total_cabecas=total,
        exige_ids=exige,
    )
    db.add(gta)
    db.flush()
    for a in animais:
        db.add(GTAAnimal(gta_id=gta.id, animal_id=a.id))
    db.commit()
    db.refresh(gta)
    return GTAOut(
        id=gta.id,
        numero=gta.numero,
        destino_codigo=gta.destino_codigo,
        destino_nome=gta.destino_nome,
        finalidade=gta.finalidade,
        status=gta.status,
        total_cabecas=gta.total_cabecas,
        exige_ids=gta.exige_ids,
        ids_vinculados=[a.id_oficial for a in animais],
        criado_em=gta.criado_em,
    )


def listar_gtas(db: Session) -> list[GTAOut]:
    rows = db.scalars(select(GTA).order_by(GTA.id.desc())).all()
    out: list[GTAOut] = []
    for g in rows:
        ids = [link.animal.id_oficial for link in g.animais]
        out.append(
            GTAOut(
                id=g.id,
                numero=g.numero,
                destino_codigo=g.destino_codigo,
                destino_nome=g.destino_nome,
                finalidade=g.finalidade,
                status=g.status,
                total_cabecas=g.total_cabecas,
                exige_ids=g.exige_ids,
                ids_vinculados=ids,
                criado_em=g.criado_em,
            )
        )
    return out
