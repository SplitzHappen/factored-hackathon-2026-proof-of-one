"""RF1Q language-scope guard for the declared Spanish / Portuguese product.

The product declares Spanish and Brazilian Portuguese only (``docs/LIMITATIONS.md``
section 2). Its unauthorized-activity recognition is built for those languages, so
an explicit English report of unauthorized activity can go unrecognized and,
before this guard, could be answered with an ordinary transaction or account status.

English stays formally out of scope. The safe fallback is that a turn written
predominantly in English never receives account data: the interpretation post-check
maps it to an unsupported request, which abstains and offers human review. A
recognized unauthorized-activity report still takes precedence and escalates.

The check counts closed sets of function words only. Words shared between
English and Spanish/Portuguese ("a", "no", "me", "he", "has", "as", "do") are in
neither set, and a Spanish/Portuguese message with an English fragment stays in
scope: English must clearly dominate.
"""

from __future__ import annotations

import re
import unicodedata


_ENGLISH_FUNCTION_WORDS = frozenset(
    {
        "the", "i", "im", "ive", "id", "my", "mine", "this", "that", "these", "those",
        "was", "were", "is", "isnt", "wasnt", "are", "arent", "did", "didnt",
        "dont", "does", "doesnt", "not", "it", "its", "you", "your", "what", "whats",
        "where", "wheres", "when", "why", "how", "who", "which", "can", "cant",
        "could", "would", "should", "will", "wont", "have", "had", "havent", "been",
        "of", "and", "to", "for", "with", "from", "on", "at", "by", "an", "someone",
        "somebody", "nobody", "anyone", "anybody", "never", "please", "there",
        "theres", "they", "she", "her", "him", "his", "our", "we", "just",
        "about", "after", "before", "because", "but", "or", "if", "any", "all",
        "out", "up", "into", "be", "am",
    }
)
_SUPPORTED_FUNCTION_WORDS = frozenset(
    {
        # Spanish
        "el", "la", "los", "las", "de", "del", "que", "y", "en", "un", "una", "unos",
        "unas", "mi", "mis", "es", "por", "con", "para", "se", "lo", "le", "les",
        "su", "sus", "yo", "tu", "al", "pero", "como", "porque", "esta", "este",
        "ese", "esa", "eso", "esto", "ya", "hay", "muy", "mas", "sin", "cuenta",
        "tarjeta", "cargo", "hice", "fue", "son", "estoy", "tengo", "nunca",
        "nadie", "alguien", "usted", "ustedes", "hola", "gracias", "favor", "ayer",
        "hoy", "cuando", "donde", "cual", "quiero", "necesito", "puedo", "reconozco",
        "saldo", "movimiento", "transaccion", "compra", "pago", "retiro", "cobro",
        "tambien", "ahora",
        # Portuguese
        "o", "os", "da", "dos", "das", "meu", "minha", "meus", "minhas",
        "nao", "eu", "um", "uma", "uns", "umas", "na", "nos", "isso", "isto",
        "essa", "esse", "voce", "voces", "foi", "ele", "ela", "tem", "ao", "pela",
        "pelo", "com", "sem", "mas", "e", "conta", "cartao", "fiz", "ninguem",
        "alguem", "obrigado", "obrigada", "ontem", "hoje", "quando", "onde", "qual",
        "quero", "preciso", "posso", "reconheco", "transacao", "pagamento", "saque",
        "cobranca", "tambem", "agora", "oi",
    }
)
_WORD = re.compile(r"[a-z]+")
# Identifiers and codes ("DEMO-ES-1001", "R$ 850", "ATT-5B19") carry no language
# signal, and their letters must not count: otherwise two references of different
# shape could route differently and reveal which one exists.
_IDENTIFIER = re.compile(r"\S*\d\S*|\b[^\W\d_]+(?:-[^\W_]+)+\b")
_MIN_ENGLISH_WORDS = 2
_ENGLISH_DOMINANCE = 4


def _words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.replace("'", "").replace("’", "")
    return _WORD.findall(_IDENTIFIER.sub(" ", normalized))


def unsupported_language_dominant(text: str) -> bool:
    """Return True when ``text`` is predominantly English, an unsupported language."""

    english = supported = 0
    for word in _words(text):
        if word in _ENGLISH_FUNCTION_WORDS:
            english += 1
        elif word in _SUPPORTED_FUNCTION_WORDS:
            supported += 1
    if english < _MIN_ENGLISH_WORDS:
        return False
    return supported == 0 or english >= _ENGLISH_DOMINANCE * supported
