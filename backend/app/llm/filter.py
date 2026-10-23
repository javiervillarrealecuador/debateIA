import re
from typing import Tuple

# Patrones de cifras, porcentajes, montos y estadísticas
NUMERICAL_PATTERN = re.compile(
    r"(\d+([.,]\d+)?\s*(%|por ciento|millones|mil|billones|dólares|pesos|euros|soles)|"
    r"\b(primero|segundo|cero|uno|dos|tres|cuatro|cinco|diez|cien|mil)\b|"
    r"\$\s*\d+)",
    re.IGNORECASE,
)

# Verbos de acción factual, acusación, impacto o promesa
ACTION_VERBS_PATTERN = re.compile(
    r"\b(aument[oó]|reduj[oó]|subi[oó]|baj[oó]|creci[oó]|cay[oó]|disminuy[oó]|"
    r"gast[oó]|invirti[oó]|prometi[oó]|mintió|rob[oó]|ocult[oó]|desvi[oó]|"
    r"firm[oó]|aprob[oó]|elimin[oó]|cre[oó]|dej[oó]|endeud[oó]|fracas[oó]|"
    r"increment[oó]|devalu[oó]|recort[oó])\b",
    re.IGNORECASE,
)

# Temas clave de debate político/económico
POLICY_KEYWORDS = re.compile(
    r"\b(pib|inflaci[oó]n|desempleo|pobreza|d[eé]ficit|deuda|seguridad|homicidios|delincuencia|"
    r"corrupci[oó]n|salud|hospitales|educaci[oó]n|pensiones|afp|impuestos|reforma|constituci[oó]n|"
    r"presupuesto|ministerio|gobierno|candidat[oa]|propuesta|ley|congreso|fiscal[ií]a|contrato)\b",
    re.IGNORECASE,
)

# Frases de relleno / cortesía que deben descartarse inmediatamente si no hay datos
DISCARD_GREETINGS = re.compile(
    r"^(muchas gracias|buenas noches|gracias moderador|gracias a todos|un saludo|estimados compatriotas|"
    r"como dec[ií]a|para responder|en primer lugar|por supuesto|sin duda alguna)$",
    re.IGNORECASE,
)


def evaluate_claim_trigger(text: str) -> Tuple[bool, str]:
    """
    Evalúa en submilisegundos si el texto transcrito justifica activar el pipeline RAG + LLM.
    Evita búsquedas y llamadas a APIs de pago en saludos, muletillas o frases retóricas vacías.
    """
    cleaned = text.strip().lower()

    # Mínimo de longitud de palabras útiles
    words = cleaned.split()
    if len(words) < 3:
        return False, "Frase demasiado corta"

    # Saludos o muletillas exactas
    if DISCARD_GREETINGS.match(cleaned):
        return False, "Cortesía o saludo descartado"

    # Detección de cifras numéricas o estadísticas
    if NUMERICAL_PATTERN.search(cleaned):
        return True, "Contiene cifras numéricas o estadísticas"

    # Detección combinada: Verbo factual + Palabra clave temática
    has_action = bool(ACTION_VERBS_PATTERN.search(cleaned))
    has_policy = bool(POLICY_KEYWORDS.search(cleaned))

    if has_action and has_policy:
        return True, "Afirmación factual con métrica/política"

    if has_policy and len(words) >= 6:
        return True, "Afirmación temática de política pública"

    if has_action and len(words) >= 8:
        return True, "Declaración con impacto de acción/resultado"

    return False, "Rango retórico sin evidencia factual necesaria"
