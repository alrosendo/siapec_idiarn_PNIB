from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Animal, EventoAnimal, VacinacaoAnimal, VacinacaoBrucelose
from app.schemas.dto import VacinacaoCreate, VacinacaoOut
from app.services.pnib_rules import vacina_brucelose_exige_ids


def declarar_vacinacao(db: Session, payload: VacinacaoCreate) -> VacinacaoOut:
    if vacina_brucelose_exige_ids() and not payload.ids_oficiais:
        raise ValueError("PNIB: vacinação de brucelose exige vínculo de identificadores")

    animais: list[Animal] = []
    for id_of in payload.ids_oficiais:
        animal = db.scalar(
            select(Animal).where(
                Animal.id_oficial == id_of,
                Animal.exploracao_id == payload.exploracao_id,
                Animal.status == "ativo",
            )
        )
        if not animal:
            raise ValueError(f"Animal não encontrado/ativo na exploração: {id_of}")
        if animal.sexo != "F":
            raise ValueError(f"Animal {id_of} não elegível (sexo)")
        animais.append(animal)

    if len(set(payload.ids_oficiais)) != len(payload.ids_oficiais):
        raise ValueError("IDs duplicados no lote")

    total_prev = len(db.scalars(select(VacinacaoBrucelose.id)).all())
    protocolo = f"VN-{datetime.utcnow().strftime('%Y')}-{total_prev + 1:06d}"
    vac = VacinacaoBrucelose(
        protocolo=protocolo,
        exploracao_id=payload.exploracao_id,
        data_vacinacao=payload.data_vacinacao,
        produto=payload.produto,
        partida=payload.partida,
        rt_nome=payload.rt_nome,
        status="confirmada",
    )
    db.add(vac)
    db.flush()

    sync_pendentes = 0
    for a in animais:
        db.add(VacinacaoAnimal(vacinacao_id=vac.id, animal_id=a.id))
        db.add(
            EventoAnimal(
                animal_id=a.id,
                tipo="VACINA_BRUCELOSE",
                data_evento=payload.data_vacinacao,
                payload_json=f'{{"protocolo":"{protocolo}","partida":"{payload.partida}"}}',
            )
        )
        if a.sync_status != "ok":
            a.sync_status = "pendente"
            sync_pendentes += 1

    db.commit()
    db.refresh(vac)
    return VacinacaoOut(
        id=vac.id,
        protocolo=vac.protocolo,
        data_vacinacao=vac.data_vacinacao,
        produto=vac.produto,
        partida=vac.partida,
        rt_nome=vac.rt_nome,
        status=vac.status,
        total_animais=len(animais),
        ids_oficiais=[a.id_oficial for a in animais],
        sync_pendentes=sync_pendentes,
    )
