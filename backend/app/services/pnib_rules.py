"""Motor mínimo de regras PNIB por etapa."""

from app.core.config import settings


def etapa_atual() -> int:
    return settings.pnib_etapa


def gta_exige_ids(
    *,
    total_cabecas: int,
    ids_informados: int,
    finalidade: str,
    forcar: bool = False,
) -> tuple[bool, str | None]:
    """Retorna (exige_100%, mensagem_erro ou None)."""
    if forcar or finalidade.lower() in {"protocolo_privado", "abate_exportacao"}:
        if ids_informados < total_cabecas:
            return True, "Finalidade exige 100% dos animais identificados."
        return True, None

    et = etapa_atual()
    if et >= 4:
        if ids_informados < total_cabecas:
            return True, "Etapa 4 PNIB: identificação obrigatória antes da movimentação."
        return True, None

    # Etapas 2–3: IDs opcionais, mas se informar parcial ok; não pode informar mais que total
    if ids_informados > total_cabecas:
        return False, "Quantidade de IDs maior que o embarque."
    return False, None


def vacina_brucelose_exige_ids() -> bool:
    # Greenfield IDIARN: sempre exigir (Etapa 3 antecipável)
    return True
