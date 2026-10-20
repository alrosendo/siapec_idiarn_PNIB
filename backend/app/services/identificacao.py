from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Animal, EstoqueIdentificador, EventoAnimal, Exploracao
from app.schemas.dto import AnimalOut, AplicarIdentificacaoIn, AplicarIdentificacaoOut
from app.services.faixa import faixa_por_nascimento


def _animal_out(a: Animal) -> AnimalOut:
    return AnimalOut(
        id=a.id,
        id_oficial=a.id_oficial,
        brinco_visual=a.brinco_visual,
        sexo=a.sexo,
        data_nascimento=a.data_nascimento,
        nascimento_estimado=a.nascimento_estimado,
        status=a.status,
        sync_status=a.sync_status,
        faixa=faixa_por_nascimento(a.data_nascimento),
    )


def aplicar_identificacao(db: Session, payload: AplicarIdentificacaoIn) -> AplicarIdentificacaoOut:
    exp = db.get(Exploracao, payload.exploracao_id)
    if not exp:
        raise ValueError("Exploração não encontrada")
    if exp.propriedade.interditada:
        raise ValueError("Propriedade interditada")

    aplicados: list[Animal] = []
    for item in payload.itens:
        estoque = db.scalar(
            select(EstoqueIdentificador).where(
                EstoqueIdentificador.id_oficial == item.id_oficial,
                EstoqueIdentificador.propriedade_id == exp.propriedade_id,
            )
        )
        if not estoque or estoque.status not in {"disponivel", "reservado"}:
            raise ValueError(f"Identificador indisponível: {item.id_oficial}")

        existe = db.scalar(select(Animal).where(Animal.id_oficial == item.id_oficial))
        if existe:
            raise ValueError(f"Identificador já aplicado: {item.id_oficial}")

        animal = Animal(
            exploracao_id=exp.id,
            id_oficial=item.id_oficial,
            brinco_visual=item.brinco_visual or estoque.brinco_visual,
            sexo=item.sexo,
            data_nascimento=item.data_nascimento,
            nascimento_estimado=item.nascimento_estimado,
            status="ativo",
            sync_status="pendente",
        )
        db.add(animal)
        db.flush()
        db.add(
            EventoAnimal(
                animal_id=animal.id,
                tipo="IDENTIFICACAO_APLICADA",
                data_evento=payload.data_aplicacao,
                payload_json=None,
            )
        )
        estoque.status = "aplicado"
        aplicados.append(animal)

    db.commit()
    for a in aplicados:
        db.refresh(a)

    outs = [_animal_out(a) for a in aplicados]
    return AplicarIdentificacaoOut(
        aplicados=len(outs),
        animais=outs,
        sync_pendentes=sum(1 for a in outs if a.sync_status == "pendente"),
    )


def listar_animais(db: Session, exploracao_id: int) -> list[AnimalOut]:
    rows = db.scalars(
        select(Animal).where(Animal.exploracao_id == exploracao_id).order_by(Animal.id_oficial)
    ).all()
    return [_animal_out(a) for a in rows]


def listar_estoque(db: Session, propriedade_id: int, apenas_disponiveis: bool = True):
    q = select(EstoqueIdentificador).where(EstoqueIdentificador.propriedade_id == propriedade_id)
    if apenas_disponiveis:
        q = q.where(EstoqueIdentificador.status == "disponivel")
    return db.scalars(q.order_by(EstoqueIdentificador.id_oficial)).all()
