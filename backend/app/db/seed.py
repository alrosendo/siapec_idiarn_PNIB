from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import (
    EstoqueIdentificador,
    Exploracao,
    Produtor,
    Propriedade,
    SaldoFaixa,
    Veterinario,
    VinculoPropriedade,
)


def migrate_sqlite_columns(db: Session) -> None:
    """Acrescenta colunas novas em SQLite já existente (create_all não altera)."""
    try:
        cols = {r[1] for r in db.execute(text("PRAGMA table_info(produtores)")).fetchall()}
        if cols and "telefone" not in cols:
            db.execute(text("ALTER TABLE produtores ADD COLUMN telefone VARCHAR(30)"))
        if cols and "email" not in cols:
            db.execute(text("ALTER TABLE produtores ADD COLUMN email VARCHAR(120)"))
        db.commit()
    except Exception:
        db.rollback()


def seed_if_empty(db: Session) -> None:
    migrate_sqlite_columns(db)

    if db.scalar(select(Produtor).limit(1)):
        _ensure_demo_vinculos(db)
        return

    dono = Produtor(
        cpf_cnpj="12345678901",
        nome="José Produtor Demo",
        telefone="84999990001",
        email="jose@demo.rn.gov.br",
    )
    arrend = Produtor(
        cpf_cnpj="98765432100",
        nome="Maria Arrendatária",
        telefone="84999990002",
    )
    parceiro = Produtor(
        cpf_cnpj="11122233344",
        nome="Carlos Parceiro",
        telefone="84999990003",
    )
    db.add_all([dono, arrend, parceiro])
    db.flush()

    prop = Propriedade(
        produtor_id=dono.id,
        codigo="PROP-RN-001",
        nome="Fazenda Seridó Demo",
        municipio="Caicó",
        uf="RN",
    )
    db.add(prop)
    db.flush()

    hoje = date.today()
    db.add_all(
        [
            VinculoPropriedade(
                propriedade_id=prop.id,
                produtor_id=dono.id,
                tipo_vinculo="proprietario",
                ativo=True,
                data_inicio=hoje,
            ),
            VinculoPropriedade(
                propriedade_id=prop.id,
                produtor_id=arrend.id,
                tipo_vinculo="arrendatario",
                ativo=True,
                data_inicio=hoje,
                observacao="Contrato demo",
            ),
            VinculoPropriedade(
                propriedade_id=prop.id,
                produtor_id=parceiro.id,
                tipo_vinculo="parceiro",
                ativo=True,
                data_inicio=hoje,
            ),
        ]
    )

    exp = Exploracao(propriedade_id=prop.id, especie="bovino", finalidade="corte")
    db.add(exp)
    db.flush()

    celulas = [
        ("M", "0-12", 40),
        ("M", "13-24", 28),
        ("F", "0-12", 55),
        ("F", "13-24", 42),
        ("F", "25-36", 30),
        ("F", "36+", 26),
    ]
    for sexo, faixa, qtd in celulas:
        db.add(SaldoFaixa(exploracao_id=exp.id, sexo=sexo, faixa=faixa, quantidade=qtd))

    for i in range(1, 81):
        db.add(
            EstoqueIdentificador(
                propriedade_id=prop.id,
                id_oficial=f"BR-RN-{i:05d}",
                brinco_visual=str(10000 + i),
                tipo_dispositivo="convencional",
                status="disponivel",
                lote_remessa="LOTE-DEMO-2026",
            )
        )

    db.add(
        Veterinario(
            crmv="1234",
            uf_crmv="RN",
            nome="Dra. Ana Veterinária Demo",
            cpf="55566677788",
            telefone="84988887777",
        )
    )

    db.commit()


def _ensure_demo_vinculos(db: Session) -> None:
    from app.services.cadastros import garantir_vinculos_seed

    garantir_vinculos_seed(db)
    # Se só há 1 produtor, cria arrendatário/parceiro demo para a prop 1
    prop = db.get(Propriedade, 1)
    if not prop:
        return
    ativos = db.scalars(
        select(VinculoPropriedade).where(
            VinculoPropriedade.propriedade_id == prop.id,
            VinculoPropriedade.ativo.is_(True),
        )
    ).all()
    if len(ativos) >= 2:
        return

    def _get_or_create(cpf: str, nome: str) -> Produtor:
        p = db.scalar(select(Produtor).where(Produtor.cpf_cnpj == cpf))
        if p:
            return p
        p = Produtor(cpf_cnpj=cpf, nome=nome, ativo=True)
        db.add(p)
        db.flush()
        return p

    tipos_presentes = {v.tipo_vinculo for v in ativos}
    if "arrendatario" not in tipos_presentes:
        a = _get_or_create("98765432100", "Maria Arrendatária")
        db.add(
            VinculoPropriedade(
                propriedade_id=prop.id,
                produtor_id=a.id,
                tipo_vinculo="arrendatario",
                ativo=True,
                data_inicio=date.today(),
            )
        )
    if "parceiro" not in tipos_presentes:
        p = _get_or_create("11122233344", "Carlos Parceiro")
        db.add(
            VinculoPropriedade(
                propriedade_id=prop.id,
                produtor_id=p.id,
                tipo_vinculo="parceiro",
                ativo=True,
                data_inicio=date.today(),
            )
        )
    if not db.scalar(select(Veterinario).limit(1)):
        db.add(
            Veterinario(
                crmv="1234",
                uf_crmv="RN",
                nome="Dra. Ana Veterinária Demo",
            )
        )
    db.commit()


def data_nasc_faixa(faixa: str) -> date:
    hoje = date.today()
    mapa = {
        "0-12": 180,
        "13-24": 540,
        "25-36": 900,
        "36+": 1400,
    }
    return hoje - timedelta(days=mapa.get(faixa, 180))
