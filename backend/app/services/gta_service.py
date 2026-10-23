import json
from collections import Counter
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Animal, EventoAnimal, Exploracao, GTA, GTAAnimal, Propriedade
from app.schemas.dto import ChegadaCreate, GTACreate, GTAOut, GTAQuantidadeIn
from app.services.faixa import faixa_por_nascimento
from app.services.pnib_rules import gta_exige_ids
from app.services.saldo import ajustar_saldo


def _quantidades(g: GTA) -> list[GTAQuantidadeIn]:
    if not g.quantidades_json:
        return []
    raw = json.loads(g.quantidades_json)
    return [GTAQuantidadeIn(**item) for item in raw]


def _to_out(g: GTA) -> GTAOut:
    ids = [link.animal.id_oficial for link in g.animais if link.animal]
    return GTAOut(
        id=g.id,
        numero=g.numero,
        exploracao_origem_id=g.exploracao_origem_id,
        exploracao_destino_id=g.exploracao_destino_id,
        destino_codigo=g.destino_codigo,
        destino_nome=g.destino_nome,
        finalidade=g.finalidade,
        status=g.status,
        total_cabecas=g.total_cabecas,
        exige_ids=g.exige_ids,
        quantidades=_quantidades(g),
        ids_vinculados=ids,
        ocorrencia=g.ocorrencia,
        data_chegada=g.data_chegada,
        criado_em=g.criado_em,
    )


def emitir_gta(db: Session, payload: GTACreate) -> GTAOut:
    if payload.exploracao_origem_id == payload.exploracao_destino_id:
        raise ValueError("Origem e destino não podem ser a mesma exploração")

    origem = db.get(Exploracao, payload.exploracao_origem_id)
    destino = db.scalars(
        select(Exploracao)
        .where(Exploracao.id == payload.exploracao_destino_id)
        .options(joinedload(Exploracao.propriedade))
    ).first()
    if not origem or not origem.ativa:
        raise ValueError("Exploração de origem inválida")
    if not destino or not destino.ativa:
        raise ValueError("Exploração de destino inválida")
    if destino.propriedade.interditada:
        raise ValueError("Propriedade de destino interditada")
    if origem.especie != destino.especie:
        raise ValueError("Origem e destino devem ser da mesma espécie (bovino ou bubalino)")

    quantidades = [q for q in payload.quantidades if q.quantidade > 0]
    total = sum(q.quantidade for q in quantidades)
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

    cotas = {(q.sexo, q.faixa): q.quantidade for q in quantidades}
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
                raise ValueError(f"Mais IDs do que a quantidade em {animal.sexo}/{faixa}")
            animal.status = "em_transito"
            animais.append(animal)

        if exige and len(animais) != total:
            raise ValueError("Regra PNIB: todos os animais do embarque devem ter ID vinculado")

    for q in quantidades:
        ajustar_saldo(db, payload.exploracao_origem_id, q.sexo, q.faixa, -q.quantidade)

    prop: Propriedade = destino.propriedade
    numero = f"GTA-RN-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    gta = GTA(
        numero=numero,
        exploracao_origem_id=payload.exploracao_origem_id,
        exploracao_destino_id=destino.id,
        destino_codigo=prop.codigo,
        destino_nome=prop.nome,
        finalidade=payload.finalidade,
        status="emitida",
        total_cabecas=total,
        exige_ids=exige,
        quantidades_json=json.dumps([q.model_dump() for q in quantidades]),
    )
    db.add(gta)
    db.flush()
    for a in animais:
        db.add(GTAAnimal(gta_id=gta.id, animal_id=a.id))
    db.commit()
    gta = _carregar(db, gta.id)
    return _to_out(gta)


def confirmar_chegada(db: Session, gta_id: int, payload: ChegadaCreate) -> GTAOut:
    gta = _carregar(db, gta_id)
    if not gta:
        raise ValueError("GTA não encontrada")
    if gta.status != "emitida":
        raise ValueError("Só é possível confirmar chegada de GTA emitida")
    if not gta.exploracao_destino_id:
        raise ValueError("GTA sem exploração de destino. Emita novamente escolhendo o destino cadastrado.")

    emitidas = {(q.sexo, q.faixa): q.quantidade for q in _quantidades(gta)}
    recebidas = {(q.sexo, q.faixa): q.quantidade for q in payload.quantidades}
    for key, qtd in recebidas.items():
        if qtd < 0:
            raise ValueError("Quantidade recebida não pode ser negativa")
        if qtd > emitidas.get(key, 0):
            sexo, faixa = key
            raise ValueError(f"Recebido maior que o embarque em {sexo}/{faixa}")

    ids_gta = {link.animal.id_oficial: link.animal for link in gta.animais}
    ids_recebidos = list(dict.fromkeys(payload.ids_oficiais))
    desconhecidos = [i for i in ids_recebidos if i not in ids_gta]
    if desconhecidos:
        raise ValueError(f"ID não pertence a esta GTA: {desconhecidos[0]}")

    usados: Counter[tuple[str, str]] = Counter()
    for id_of in ids_recebidos:
        animal = ids_gta[id_of]
        if animal.status != "em_transito":
            raise ValueError(f"Animal {id_of} não está em trânsito")
        key = (animal.sexo, faixa_por_nascimento(animal.data_nascimento))
        usados[key] += 1
        if usados[key] > recebidas.get(key, 0):
            raise ValueError(
                f"Mais IDs recebidos do que a quantidade conferida em {key[0]}/{key[1]}"
            )

    faltas = []
    for key, qtd_emitida in emitidas.items():
        qtd_recebida = recebidas.get(key, 0)
        if qtd_recebida != qtd_emitida:
            faltas.append(f"{key[0]}/{key[1]}: emitido {qtd_emitida}, recebido {qtd_recebida}")

    ids_faltantes = sorted(set(ids_gta) - set(ids_recebidos))
    if ids_faltantes:
        faltas.append("IDs não recebidos: " + ", ".join(ids_faltantes))

    hoje = date.today()
    for key, qtd in recebidas.items():
        if qtd:
            sexo, faixa = key
            ajustar_saldo(db, gta.exploracao_destino_id, sexo, faixa, qtd)

    for id_of in ids_recebidos:
        animal = ids_gta[id_of]
        animal.exploracao_id = gta.exploracao_destino_id
        animal.status = "ativo"
        db.add(
            EventoAnimal(
                animal_id=animal.id,
                tipo="CHEGADA_GTA",
                data_evento=hoje,
                payload_json=json.dumps({"gta": gta.numero}),
            )
        )

    gta.data_chegada = hoje
    if faltas:
        extra = f" Obs.: {payload.observacao}" if payload.observacao else ""
        gta.status = "divergente"
        gta.ocorrencia = "Divergência na chegada. " + "; ".join(faltas) + extra
    else:
        gta.status = "recebida"
        gta.ocorrencia = payload.observacao

    db.commit()
    return _to_out(_carregar(db, gta.id))


def listar_gtas(db: Session, status: str | None = None) -> list[GTAOut]:
    q = select(GTA).options(joinedload(GTA.animais).joinedload(GTAAnimal.animal)).order_by(GTA.id.desc())
    if status:
        q = q.where(GTA.status == status)
    rows = db.scalars(q).unique().all()
    return [_to_out(g) for g in rows]


def _carregar(db: Session, gta_id: int) -> GTA | None:
    return db.scalars(
        select(GTA)
        .where(GTA.id == gta_id)
        .options(joinedload(GTA.animais).joinedload(GTAAnimal.animal))
    ).unique().first()
