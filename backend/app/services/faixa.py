from datetime import date


FAIXAS = ("0-12", "13-24", "25-36", "36+")


def idade_meses(nascimento: date, ref: date | None = None) -> int:
    ref = ref or date.today()
    return (ref.year - nascimento.year) * 12 + (ref.month - nascimento.month)


def faixa_por_nascimento(nascimento: date, ref: date | None = None) -> str:
    m = idade_meses(nascimento, ref)
    if m <= 12:
        return "0-12"
    if m <= 24:
        return "13-24"
    if m <= 36:
        return "25-36"
    return "36+"
