from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


TIPOS_VINCULO = (
    "proprietario",
    "arrendatario",
    "parceiro",
    "comodato",
    "posseiro",
    "administrador",
    "outro",
)


class Produtor(Base):
    __tablename__ = "produtores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpf_cnpj: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    telefone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Titular cadastral legado (espelha vínculo proprietário principal)
    propriedades_titular: Mapped[list[Propriedade]] = relationship(back_populates="titular")
    vinculos: Mapped[list[VinculoPropriedade]] = relationship(back_populates="produtor")


class Propriedade(Base):
    __tablename__ = "propriedades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    produtor_id: Mapped[int] = mapped_column(ForeignKey("produtores.id"))
    codigo: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    municipio: Mapped[str] = mapped_column(String(120))
    uf: Mapped[str] = mapped_column(String(2), default="RN")
    interditada: Mapped[bool] = mapped_column(Boolean, default=False)

    titular: Mapped[Produtor] = relationship(back_populates="propriedades_titular")
    exploracoes: Mapped[list[Exploracao]] = relationship(back_populates="propriedade")
    vinculos: Mapped[list[VinculoPropriedade]] = relationship(
        back_populates="propriedade", cascade="all, delete-orphan"
    )


class VinculoPropriedade(Base):
    """Pessoas vinculadas à propriedade (proprietário, arrendatário, parceiros…)."""

    __tablename__ = "vinculos_propriedade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    propriedade_id: Mapped[int] = mapped_column(ForeignKey("propriedades.id"), index=True)
    produtor_id: Mapped[int] = mapped_column(ForeignKey("produtores.id"), index=True)
    tipo_vinculo: Mapped[str] = mapped_column(String(40))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    data_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    propriedade: Mapped[Propriedade] = relationship(back_populates="vinculos")
    produtor: Mapped[Produtor] = relationship(back_populates="vinculos")


class Veterinario(Base):
    __tablename__ = "veterinarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crmv: Mapped[str] = mapped_column(String(20), index=True)
    uf_crmv: Mapped[str] = mapped_column(String(2), default="RN")
    nome: Mapped[str] = mapped_column(String(200))
    cpf: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Exploracao(Base):
    __tablename__ = "exploracoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    propriedade_id: Mapped[int] = mapped_column(ForeignKey("propriedades.id"))
    especie: Mapped[str] = mapped_column(String(40), default="bovino")
    finalidade: Mapped[str] = mapped_column(String(80), default="corte")
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

    propriedade: Mapped[Propriedade] = relationship(back_populates="exploracoes")
    saldos: Mapped[list[SaldoFaixa]] = relationship(back_populates="exploracao")
    animais: Mapped[list[Animal]] = relationship(back_populates="exploracao")


class SaldoFaixa(Base):
    __tablename__ = "saldos_faixa"
    __table_args__ = (UniqueConstraint("exploracao_id", "sexo", "faixa", name="uq_saldo_celula"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exploracao_id: Mapped[int] = mapped_column(ForeignKey("exploracoes.id"))
    sexo: Mapped[str] = mapped_column(String(1))  # M / F
    faixa: Mapped[str] = mapped_column(String(20))  # 0-12, 13-24, 25-36, 36+
    quantidade: Mapped[int] = mapped_column(Integer, default=0)

    exploracao: Mapped[Exploracao] = relationship(back_populates="saldos")


class Animal(Base):
    __tablename__ = "animais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exploracao_id: Mapped[int] = mapped_column(ForeignKey("exploracoes.id"))
    id_oficial: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    brinco_visual: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    sexo: Mapped[str] = mapped_column(String(1))
    data_nascimento: Mapped[date] = mapped_column(Date)
    nascimento_estimado: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="ativo")
    # ativo | em_transito | morto | abatido | identificador_pendente
    sync_status: Mapped[str] = mapped_column(String(20), default="pendente")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    exploracao: Mapped[Exploracao] = relationship(back_populates="animais")
    eventos: Mapped[list[EventoAnimal]] = relationship(back_populates="animal")


class EstoqueIdentificador(Base):
    __tablename__ = "estoque_identificadores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    propriedade_id: Mapped[int] = mapped_column(ForeignKey("propriedades.id"))
    id_oficial: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    brinco_visual: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    tipo_dispositivo: Mapped[str] = mapped_column(String(40), default="convencional")
    status: Mapped[str] = mapped_column(String(20), default="disponivel")
    # disponivel | reservado | aplicado | perdido | substituido
    lote_remessa: Mapped[str] = mapped_column(String(60), default="LOTE-DEMO")


class EventoAnimal(Base):
    __tablename__ = "eventos_animal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animais.id"))
    tipo: Mapped[str] = mapped_column(String(40))
    data_evento: Mapped[date] = mapped_column(Date)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    animal: Mapped[Animal] = relationship(back_populates="eventos")


class GTA(Base):
    __tablename__ = "gtas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    exploracao_origem_id: Mapped[int] = mapped_column(ForeignKey("exploracoes.id"))
    destino_codigo: Mapped[str] = mapped_column(String(40))
    destino_nome: Mapped[str] = mapped_column(String(200))
    finalidade: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="emitida")
    total_cabecas: Mapped[int] = mapped_column(Integer, default=0)
    exige_ids: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    animais: Mapped[list[GTAAnimal]] = relationship(back_populates="gta")


class GTAAnimal(Base):
    __tablename__ = "gta_animais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gta_id: Mapped[int] = mapped_column(ForeignKey("gtas.id"))
    animal_id: Mapped[int] = mapped_column(ForeignKey("animais.id"))

    gta: Mapped[GTA] = relationship(back_populates="animais")
    animal: Mapped[Animal] = relationship()


class VacinacaoBrucelose(Base):
    __tablename__ = "vacinacoes_brucelose"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    protocolo: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    exploracao_id: Mapped[int] = mapped_column(ForeignKey("exploracoes.id"))
    data_vacinacao: Mapped[date] = mapped_column(Date)
    produto: Mapped[str] = mapped_column(String(120))
    partida: Mapped[str] = mapped_column(String(80))
    rt_nome: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="confirmada")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    animais: Mapped[list[VacinacaoAnimal]] = relationship(back_populates="vacinacao")


class VacinacaoAnimal(Base):
    __tablename__ = "vacinacao_animais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vacinacao_id: Mapped[int] = mapped_column(ForeignKey("vacinacoes_brucelose.id"))
    animal_id: Mapped[int] = mapped_column(ForeignKey("animais.id"))

    vacinacao: Mapped[VacinacaoBrucelose] = relationship(back_populates="animais")


class DeclaracaoRebanho(Base):
    """Nascimento ou morte no estilo SIAPEC (quantidade por faixa e/ou por ID)."""

    __tablename__ = "declaracoes_rebanho"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exploracao_id: Mapped[int] = mapped_column(ForeignKey("exploracoes.id"))
    tipo: Mapped[str] = mapped_column(String(20))  # nascimento | morte
    data_evento: Mapped[date] = mapped_column(Date)
    sexo: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    faixa: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    quantidade: Mapped[int] = mapped_column(Integer, default=0)
    ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo_baixa: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    # morte | abate | desaparecimento
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="confirmada")
    # confirmada | em_analise_oesa | homologada | estornada
    acima_indice: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
