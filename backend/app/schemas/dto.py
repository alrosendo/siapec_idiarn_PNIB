from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProdutorOut(BaseModel):
    id: int
    cpf_cnpj: str
    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativo: bool = True

    model_config = {"from_attributes": True}


class ProdutorCreate(BaseModel):
    cpf_cnpj: str
    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None


class ProdutorUpdate(BaseModel):
    cpf_cnpj: Optional[str] = None
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativo: Optional[bool] = None


class ExploracaoOut(BaseModel):
    id: int
    propriedade_id: int
    especie: str
    finalidade: str
    ativa: bool

    model_config = {"from_attributes": True}


class PropriedadeOut(BaseModel):
    id: int
    codigo: str
    nome: str
    municipio: str
    uf: str
    interditada: bool
    produtor_id: int
    titular_nome: Optional[str] = None
    exploracoes: list[ExploracaoOut] = []

    model_config = {"from_attributes": True}


class VinculoOut(BaseModel):
    id: int
    propriedade_id: int
    produtor_id: int
    produtor_nome: str
    produtor_cpf_cnpj: str
    tipo_vinculo: str
    ativo: bool
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    observacao: Optional[str] = None
    criado_em: datetime


class VinculoCreate(BaseModel):
    produtor_id: int
    tipo_vinculo: str
    data_inicio: Optional[date] = None
    observacao: Optional[str] = None


class PropriedadeDetalheOut(PropriedadeOut):
    vinculos: list[VinculoOut] = []


class PropriedadeCreate(BaseModel):
    codigo: str
    nome: str
    municipio: str
    uf: str = "RN"
    produtor_id: int  # titular / proprietário inicial


class PropriedadeUpdate(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    produtor_id: Optional[int] = None
    interditada: Optional[bool] = None


class VeterinarioOut(BaseModel):
    id: int
    crmv: str
    uf_crmv: str
    nome: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativo: bool

    model_config = {"from_attributes": True}


class VeterinarioCreate(BaseModel):
    crmv: str
    uf_crmv: str = "RN"
    nome: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None


class VeterinarioUpdate(BaseModel):
    crmv: Optional[str] = None
    uf_crmv: Optional[str] = None
    nome: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativo: Optional[bool] = None


class SaldoCelulaOut(BaseModel):
    sexo: str
    faixa: str
    quantidade: int
    com_id: int
    sem_id: int


class SaldoResumoOut(BaseModel):
    exploracao_id: int
    propriedade_nome: str
    total: int
    identificados: int
    sem_id: int
    cobertura_pct: float
    pnib_etapa: int
    celulas: list[SaldoCelulaOut]


class AnimalOut(BaseModel):
    id: int
    id_oficial: str
    brinco_visual: Optional[str]
    sexo: str
    data_nascimento: date
    nascimento_estimado: bool
    status: str
    sync_status: str
    faixa: str

    model_config = {"from_attributes": True}


class IdentificacaoItemIn(BaseModel):
    id_oficial: str
    sexo: str = Field(pattern="^[MF]$")
    data_nascimento: date
    nascimento_estimado: bool = False
    brinco_visual: Optional[str] = None


class AplicarIdentificacaoIn(BaseModel):
    exploracao_id: int
    data_aplicacao: date
    itens: list[IdentificacaoItemIn]


class AplicarIdentificacaoOut(BaseModel):
    aplicados: int
    animais: list[AnimalOut]
    sync_pendentes: int


class GTAQuantidadeIn(BaseModel):
    sexo: str
    faixa: str
    quantidade: int


class GTACreate(BaseModel):
    exploracao_origem_id: int
    destino_codigo: str
    destino_nome: str
    finalidade: str
    quantidades: list[GTAQuantidadeIn]
    ids_oficiais: list[str] = []
    forcar_exigir_ids: bool = False


class GTAOut(BaseModel):
    id: int
    numero: str
    destino_codigo: str
    destino_nome: str
    finalidade: str
    status: str
    total_cabecas: int
    exige_ids: bool
    ids_vinculados: list[str]
    criado_em: datetime

    model_config = {"from_attributes": True}


class VacinacaoCreate(BaseModel):
    exploracao_id: int
    data_vacinacao: date
    produto: str = "Vacina Brucelose B19"
    partida: str
    rt_nome: str
    ids_oficiais: list[str]


class VacinacaoOut(BaseModel):
    id: int
    protocolo: str
    data_vacinacao: date
    produto: str
    partida: str
    rt_nome: str
    status: str
    total_animais: int
    ids_oficiais: list[str]
    sync_pendentes: int


class NascimentoCreate(BaseModel):
    exploracao_id: int
    data_evento: date
    sexo: str = Field(pattern="^[MF]$")
    faixa: str = "0-12"
    quantidade: int = Field(gt=0)
    ids_oficiais: list[str] = []
    observacao: Optional[str] = None


class MorteCreate(BaseModel):
    exploracao_id: int
    data_evento: date
    tipo_baixa: str = "morte"  # morte | abate | desaparecimento
    sexo: Optional[str] = Field(default=None, pattern="^[MF]$")
    faixa: Optional[str] = None
    quantidade: int = 0
    ids_oficiais: list[str] = []
    observacao: Optional[str] = None


class DeclaracaoOut(BaseModel):
    id: int
    exploracao_id: int
    tipo: str
    data_evento: date
    sexo: Optional[str]
    faixa: Optional[str]
    quantidade: int
    ids_oficiais: list[str] = []
    tipo_baixa: Optional[str]
    observacao: Optional[str]
    status: str
    acima_indice: bool
    criado_em: datetime


class HomologarIn(BaseModel):
    aprovar: bool = True
