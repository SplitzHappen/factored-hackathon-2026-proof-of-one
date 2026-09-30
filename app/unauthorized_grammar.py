from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
import unicodedata
from typing import Iterable


_TXID_RE = re.compile(
    r"(?i)\bdemo(?:[-\s]*)(es|pt)(?:[-\s]*)(\d{4})\b"
)

_WORD_RE = re.compile(r"[\w]+(?:[\'’][\w]+)*", re.UNICODE)

_STRUCTURAL_PUNCTUATION = frozenset(".?!;:,¿¡-—–")


class PredicateFamily(str, Enum):
    PERFORM = "perform"
    ORIGINATE = "originate"
    AUTHORIZE = "authorize"
    GIVE_PERMISSION = "give_permission"
    RECOGNIZE = "recognize"
    USE_ACCESS = "use_access"
    COMPROMISE = "compromise"


class SelfRole(str, Enum):
    SUBJECT = "self_subject"
    AGENT = "self_agent"
    SOURCE = "self_source"
    POSSESSOR = "self_possessor"
    DATIVE = "self_dative"


class LexicalTag(str, Enum):
    ACTIVITY = "activity"
    INSTRUMENT = "instrument"
    SELF = "self"
    THIRD_PARTY = "third_party"
    NEGATOR = "negator"
    NEG_QUANTIFIER = "neg_quantifier"
    COORD_NEGATION = "coord_negation"
    OWNERSHIP = "ownership"
    AUTH_NOUN = "auth_noun"
    FRAUD_MARKER = "fraud_marker"
    DESCRIPTOR_NOUN = "descriptor_noun"
    SECURITY_INFO = "security_info"
    UNCERTAINTY = "uncertainty"
    CONDITIONAL = "conditional"
    RETRACTION = "retraction"
    AFFIRM_SELF = "affirm_self"
    TXID = "txid"
    QUESTION_OPEN = "question_open"
    QUESTION_CLOSE = "question_close"
    CONTRAST = "contrast"


@dataclass(frozen=True)
class Token:
    surface: str
    normalized: str
    start: int
    end: int
    had_acute: bool
    is_txid: bool = False
    txid_language: str | None = None
    txid_digits: str | None = None


@dataclass(frozen=True)
class ClauseSegment:
    index: int
    token_start: int
    token_end: int
    source_start: int
    source_end: int


@dataclass(frozen=True)
class PredicateForm:
    family: PredicateFamily
    lemma: str
    language: str
    person: int | None
    number: str | None
    tense_aspect: str
    mood: str
    voice: str
    accent_required: bool


@dataclass(frozen=True)
class PredicateMatch:
    form: PredicateForm
    token_start: int
    token_end: int
    accent_ambiguous: bool = False


@dataclass(frozen=True)
class SelfEvidence:
    role: SelfRole
    token_start: int
    token_end: int
    implicit_from_predicate: bool = False
    ambiguous: bool = False


@dataclass(frozen=True)
class FoundationAnalysis:
    tokens: tuple[Token, ...]
    clauses: tuple[ClauseSegment, ...]
    predicates: tuple[PredicateMatch, ...]
    tags: tuple[frozenset[LexicalTag], ...]
    self_evidence: tuple[SelfEvidence, ...]


def _strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _has_acute(text: str) -> bool:
    decomposed = unicodedata.normalize("NFD", text)
    return "\u0301" in decomposed


def _normalize_word(text: str) -> str:
    return _strip_diacritics(text).replace("’", "'")


def tokenize_with_source(text: str) -> tuple[Token, ...]:
    """Tokenize while retaining exact source offsets and accent metadata."""

    tokens: list[Token] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue

        txid_match = _TXID_RE.match(text, index)
        if txid_match is not None:
            surface = txid_match.group(0)
            tokens.append(
                Token(
                    surface=surface,
                    normalized="<txid>",
                    start=index,
                    end=txid_match.end(),
                    had_acute=False,
                    is_txid=True,
                    txid_language=txid_match.group(1).lower(),
                    txid_digits=txid_match.group(2),
                )
            )
            index = txid_match.end()
            continue

        char = text[index]
        if char in _STRUCTURAL_PUNCTUATION:
            normalized = "-" if char in {"—", "–"} else char
            tokens.append(
                Token(
                    surface=char,
                    normalized=normalized,
                    start=index,
                    end=index + 1,
                    had_acute=False,
                )
            )
            index += 1
            continue

        word_match = _WORD_RE.match(text, index)
        if word_match is not None:
            surface = word_match.group(0)
            tokens.append(
                Token(
                    surface=surface,
                    normalized=_normalize_word(surface),
                    start=index,
                    end=word_match.end(),
                    had_acute=_has_acute(surface),
                )
            )
            index = word_match.end()
            continue

        tokens.append(
            Token(
                surface=char,
                normalized=_normalize_word(char),
                start=index,
                end=index + 1,
                had_acute=_has_acute(char),
            )
        )
        index += 1

    return tuple(tokens)


def _is_numeric_punctuation(text: str, token: Token) -> bool:
    if token.surface not in {".", ","}:
        return False
    before = text[token.start - 1] if token.start > 0 else ""
    after = text[token.end] if token.end < len(text) else ""
    return before.isdigit() and after.isdigit()


def _has_following_whitespace(text: str, token: Token) -> bool:
    return token.end >= len(text) or text[token.end].isspace()


def _is_whitespace_adjacent_dash(text: str, token: Token) -> bool:
    if token.normalized != "-":
        return False
    before_ok = token.start == 0 or text[token.start - 1].isspace()
    after_ok = token.end == len(text) or text[token.end].isspace()
    return before_ok and after_ok


def _is_primary_boundary(text: str, token: Token) -> bool:
    if token.normalized in {"?", "!", ";"}:
        return True
    if token.normalized == ".":
        if _is_numeric_punctuation(text, token):
            return False
        return _has_following_whitespace(text, token)
    if token.normalized == "-":
        return _is_whitespace_adjacent_dash(text, token)
    return False


def _form(
    family: PredicateFamily,
    lemma: str,
    language: str,
    person: int | None,
    number: str | None,
    tense_aspect: str,
    mood: str,
    surface: str,
    *,
    voice: str = "active",
) -> tuple[str, PredicateForm]:
    return (
        _normalize_word(surface),
        PredicateForm(
            family=family,
            lemma=lemma,
            language=language,
            person=person,
            number=number,
            tense_aspect=tense_aspect,
            mood=mood,
            voice=voice,
            accent_required=_has_acute(surface),
        ),
    )


_ES_REGULAR_ENDINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "ar": {
        "present": ("o", "as", "a", "amos", "áis", "an"),
        "preterite": ("é", "aste", "ó", "amos", "asteis", "aron"),
        "imperfect": ("aba", "abas", "aba", "ábamos", "abais", "aban"),
        "present_subjunctive": ("e", "es", "e", "emos", "éis", "en"),
    },
    "er": {
        "present": ("o", "es", "e", "emos", "éis", "en"),
        "preterite": ("í", "iste", "ió", "imos", "isteis", "ieron"),
        "imperfect": ("ía", "ías", "ía", "íamos", "íais", "ían"),
        "present_subjunctive": ("a", "as", "a", "amos", "áis", "an"),
    },
    "ir": {
        "present": ("o", "es", "e", "imos", "ís", "en"),
        "preterite": ("í", "iste", "ió", "imos", "isteis", "ieron"),
        "imperfect": ("ía", "ías", "ía", "íamos", "íais", "ían"),
        "present_subjunctive": ("a", "as", "a", "amos", "áis", "an"),
    },
}

_PT_REGULAR_ENDINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "ar": {
        "present": ("o", "as", "a", "amos", "ais", "am"),
        "preterite": ("ei", "aste", "ou", "amos", "astes", "aram"),
        "imperfect": ("ava", "avas", "ava", "ávamos", "áveis", "avam"),
        "present_subjunctive": ("e", "es", "e", "emos", "eis", "em"),
    },
    "er": {
        "present": ("o", "es", "e", "emos", "eis", "em"),
        "preterite": ("i", "este", "eu", "emos", "estes", "eram"),
        "imperfect": ("ia", "ias", "ia", "íamos", "íeis", "iam"),
        "present_subjunctive": ("a", "as", "a", "amos", "ais", "am"),
    },
    "ir": {
        "present": ("o", "es", "e", "imos", "is", "em"),
        "preterite": ("i", "iste", "iu", "imos", "istes", "iram"),
        "imperfect": ("ia", "ias", "ia", "íamos", "íeis", "iam"),
        "present_subjunctive": ("a", "as", "a", "amos", "ais", "am"),
    },
}


def _spanish_stem_for_ending(stem: str, ending: str) -> str:
    if not ending.startswith(("e", "é")):
        return stem
    if stem.endswith("z"):
        return stem[:-1] + "c"
    if stem.endswith("c"):
        return stem[:-1] + "qu"
    if stem.endswith("g"):
        return stem + "u"
    return stem


def _portuguese_stem_for_ending(stem: str, ending: str) -> str:
    if not ending.startswith(("e", "é")):
        return stem
    if stem.endswith("c"):
        return stem[:-1] + "qu"
    if stem.endswith("g"):
        return stem + "u"
    return stem


def _regular_forms(
    language: str,
    family: PredicateFamily,
    lemma: str,
) -> list[tuple[str, PredicateForm]]:
    endings_table = _ES_REGULAR_ENDINGS if language == "es" else _PT_REGULAR_ENDINGS
    conjugation = lemma[-2:]
    if conjugation not in endings_table:
        return []

    stem = lemma[:-2]
    person_number = (
        (1, "singular"),
        (2, "singular"),
        (3, "singular"),
        (1, "plural"),
        (2, "plural"),
        (3, "plural"),
    )
    output: list[tuple[str, PredicateForm]] = []
    for tense_aspect, endings in endings_table[conjugation].items():
        mood = "subjunctive" if "subjunctive" in tense_aspect else "indicative"
        for (person, number), ending in zip(person_number, endings, strict=True):
            adjusted_stem = (
                _spanish_stem_for_ending(stem, ending)
                if language == "es"
                else _portuguese_stem_for_ending(stem, ending)
            )
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    mood,
                    adjusted_stem + ending,
                )
            )

    if language == "es":
        future_endings = ("é", "ás", "á", "emos", "éis", "án")
        conditional_endings = ("ía", "ías", "ía", "íamos", "íais", "ían")
    else:
        future_endings = ("ei", "ás", "á", "emos", "eis", "ão")
        conditional_endings = ("ia", "ias", "ia", "íamos", "íeis", "iam")

    for tense_aspect, endings in (
        ("future", future_endings),
        ("conditional", conditional_endings),
    ):
        for (person, number), ending in zip(person_number, endings, strict=True):
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    "indicative",
                    lemma + ending,
                )
            )
    return output


_ES_IRREGULAR: dict[str, dict[str, tuple[str, ...]]] = {
    "hacer": {
        "present": ("hago", "haces", "hace", "hacemos", "hacéis", "hacen"),
        "preterite": ("hice", "hiciste", "hizo", "hicimos", "hicisteis", "hicieron"),
        "imperfect": ("hacía", "hacías", "hacía", "hacíamos", "hacíais", "hacían"),
        "present_subjunctive": ("haga", "hagas", "haga", "hagamos", "hagáis", "hagan"),
    },
    "dar": {
        "present": ("doy", "das", "da", "damos", "dais", "dan"),
        "preterite": ("di", "diste", "dio", "dimos", "disteis", "dieron"),
        "imperfect": ("daba", "dabas", "daba", "dábamos", "dabais", "daban"),
        "present_subjunctive": ("dé", "des", "dé", "demos", "deis", "den"),
    },
    "salir": {
        "present": ("salgo", "sales", "sale", "salimos", "salís", "salen"),
        "preterite": ("salí", "saliste", "salió", "salimos", "salisteis", "salieron"),
        "imperfect": ("salía", "salías", "salía", "salíamos", "salíais", "salían"),
        "present_subjunctive": ("salga", "salgas", "salga", "salgamos", "salgáis", "salgan"),
    },
    "venir": {
        "present": ("vengo", "vienes", "viene", "venimos", "venís", "vienen"),
        "preterite": ("vine", "viniste", "vino", "vinimos", "vinisteis", "vinieron"),
        "imperfect": ("venía", "venías", "venía", "veníamos", "veníais", "venían"),
        "present_subjunctive": ("venga", "vengas", "venga", "vengamos", "vengáis", "vengan"),
    },
    "provenir": {
        "present": ("provengo", "provienes", "proviene", "provenimos", "provenís", "provienen"),
        "preterite": ("provine", "proviniste", "provino", "provinimos", "provinisteis", "provinieron"),
        "imperfect": ("provenía", "provenías", "provenía", "proveníamos", "proveníais", "provenían"),
        "present_subjunctive": ("provenga", "provengas", "provenga", "provengamos", "provengáis", "provengan"),
    },
    "reconocer": {
        "present": ("reconozco", "reconoces", "reconoce", "reconocemos", "reconocéis", "reconocen"),
        "preterite": ("reconocí", "reconociste", "reconoció", "reconocimos", "reconocisteis", "reconocieron"),
        "imperfect": ("reconocía", "reconocías", "reconocía", "reconocíamos", "reconocíais", "reconocían"),
        "present_subjunctive": ("reconozca", "reconozcas", "reconozca", "reconozcamos", "reconozcáis", "reconozcan"),
    },
}

_PT_IRREGULAR: dict[str, dict[str, tuple[str, ...]]] = {
    "fazer": {
        "present": ("faço", "fazes", "faz", "fazemos", "fazeis", "fazem"),
        "preterite": ("fiz", "fizeste", "fez", "fizemos", "fizestes", "fizeram"),
        "imperfect": ("fazia", "fazias", "fazia", "fazíamos", "fazíeis", "faziam"),
        "present_subjunctive": ("faça", "faças", "faça", "façamos", "façais", "façam"),
    },
    "dar": {
        "present": ("dou", "dás", "dá", "damos", "dais", "dão"),
        "preterite": ("dei", "deste", "deu", "demos", "destes", "deram"),
        "imperfect": ("dava", "davas", "dava", "dávamos", "dáveis", "davam"),
        "present_subjunctive": ("dê", "dês", "dê", "demos", "deis", "deem"),
    },
    "sair": {
        "present": ("saio", "sais", "sai", "saímos", "saís", "saem"),
        "preterite": ("saí", "saíste", "saiu", "saímos", "saístes", "saíram"),
        "imperfect": ("saía", "saías", "saía", "saíamos", "saíeis", "saíam"),
        "present_subjunctive": ("saia", "saias", "saia", "saiamos", "saiais", "saiam"),
    },
    "vir": {
        "present": ("venho", "vens", "vem", "vimos", "vindes", "vêm"),
        "preterite": ("vim", "vieste", "veio", "viemos", "viestes", "vieram"),
        "imperfect": ("vinha", "vinhas", "vinha", "vínhamos", "vínheis", "vinham"),
        "present_subjunctive": ("venha", "venhas", "venha", "venhamos", "venhais", "venham"),
    },
    "reconhecer": {
        "present": ("reconheço", "reconheces", "reconhece", "reconhecemos", "reconheceis", "reconhecem"),
        "preterite": ("reconheci", "reconheceste", "reconheceu", "reconhecemos", "reconhecestes", "reconheceram"),
        "imperfect": ("reconhecia", "reconhecias", "reconhecia", "reconhecíamos", "reconhecíeis", "reconheciam"),
        "present_subjunctive": ("reconheça", "reconheças", "reconheça", "reconheçamos", "reconheçais", "reconheçam"),
    },
}


_ES_LEMMAS: dict[PredicateFamily, tuple[str, ...]] = {
    PredicateFamily.PERFORM: (
        "hacer",
        "realizar",
        "efectuar",
        "ordenar",
        "mandar",
        "pagar",
        "retirar",
        "transferir",
        "comprar",
        "gastar",
    ),
    PredicateFamily.ORIGINATE: ("salir", "partir", "provenir", "venir"),
    PredicateFamily.AUTHORIZE: ("autorizar", "aprobar", "consentir", "permitir"),
    PredicateFamily.GIVE_PERMISSION: ("dar",),
    PredicateFamily.RECOGNIZE: ("reconocer", "identificar"),
    PredicateFamily.USE_ACCESS: (
        "usar",
        "utilizar",
        "entrar",
        "acceder",
        "agarrar",
        "coger",
        "tomar",
        "sacar",
    ),
    PredicateFamily.COMPROMISE: ("robar", "clonar", "hackear"),
}

_PT_LEMMAS: dict[PredicateFamily, tuple[str, ...]] = {
    PredicateFamily.PERFORM: (
        "fazer",
        "realizar",
        "efetuar",
        "mandar",
        "pagar",
        "sacar",
        "transferir",
        "comprar",
        "gastar",
    ),
    PredicateFamily.ORIGINATE: ("partir", "sair", "vir"),
    PredicateFamily.AUTHORIZE: ("autorizar", "aprovar", "consentir", "permitir"),
    PredicateFamily.GIVE_PERMISSION: ("dar",),
    PredicateFamily.RECOGNIZE: ("reconhecer", "identificar"),
    PredicateFamily.USE_ACCESS: (
        "usar",
        "utilizar",
        "entrar",
        "acessar",
        "pegar",
        "tomar",
    ),
    PredicateFamily.COMPROMISE: ("roubar", "clonar", "hackear", "invadir", "furtar"),
}


_ES_FUTURE_STEMS = {
    "hacer": "har",
    "salir": "saldr",
    "venir": "vendr",
    "provenir": "provendr",
}
_PT_FUTURE_STEMS = {
    "fazer": "far",
    "vir": "vir",
}


def _irregular_forms(
    language: str,
    family: PredicateFamily,
    lemma: str,
) -> list[tuple[str, PredicateForm]]:
    table = _ES_IRREGULAR if language == "es" else _PT_IRREGULAR
    if lemma not in table:
        return []

    person_number = (
        (1, "singular"),
        (2, "singular"),
        (3, "singular"),
        (1, "plural"),
        (2, "plural"),
        (3, "plural"),
    )
    output: list[tuple[str, PredicateForm]] = []
    for tense_aspect, surfaces in table[lemma].items():
        mood = "subjunctive" if "subjunctive" in tense_aspect else "indicative"
        for (person, number), surface in zip(person_number, surfaces, strict=True):
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    mood,
                    surface,
                )
            )

    if language == "es":
        future_stem = _ES_FUTURE_STEMS.get(lemma, lemma)
        future_endings = ("é", "ás", "á", "emos", "éis", "án")
        conditional_endings = ("ía", "ías", "ía", "íamos", "íais", "ían")
    else:
        future_stem = _PT_FUTURE_STEMS.get(lemma, lemma)
        future_endings = ("ei", "ás", "á", "emos", "eis", "ão")
        conditional_endings = ("ia", "ias", "ia", "íamos", "íeis", "iam")

    for tense_aspect, endings in (
        ("future", future_endings),
        ("conditional", conditional_endings),
    ):
        for (person, number), ending in zip(person_number, endings, strict=True):
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    "indicative",
                    future_stem + ending,
                )
            )
    return output


def _participle(language: str, lemma: str) -> str:
    if language == "es":
        irregular = {
            "hacer": "hecho",
        }
        if lemma in irregular:
            return irregular[lemma]
        if lemma.endswith("ar"):
            return lemma[:-2] + "ado"
        return lemma[:-2] + "ido"

    irregular = {
        "fazer": "feito",
    }
    if lemma in irregular:
        return irregular[lemma]
    if lemma.endswith("ar"):
        return lemma[:-2] + "ado"
    return lemma[:-2] + "ido"


_ES_AUXILIARIES: dict[str, tuple[tuple[str, int, str], ...]] = {
    "present_perfect": (
        ("he", 1, "singular"),
        ("has", 2, "singular"),
        ("ha", 3, "singular"),
        ("hemos", 1, "plural"),
        ("habéis", 2, "plural"),
        ("han", 3, "plural"),
    ),
    "pluperfect": (
        ("había", 1, "singular"),
        ("habías", 2, "singular"),
        ("había", 3, "singular"),
        ("habíamos", 1, "plural"),
        ("habíais", 2, "plural"),
        ("habían", 3, "plural"),
    ),
}

_PT_AUXILIARIES: dict[str, tuple[tuple[str, int, str], ...]] = {
    "iterative_compound": (
        ("tenho", 1, "singular"),
        ("tens", 2, "singular"),
        ("tem", 3, "singular"),
        ("temos", 1, "plural"),
        ("tendes", 2, "plural"),
        ("têm", 3, "plural"),
    ),
    "pluperfect": (
        ("tinha", 1, "singular"),
        ("tinhas", 2, "singular"),
        ("tinha", 3, "singular"),
        ("tínhamos", 1, "plural"),
        ("tínheis", 2, "plural"),
        ("tinham", 3, "plural"),
    ),
}


def _build_paradigm(language: str) -> dict[str, tuple[PredicateForm, ...]]:
    lemma_map = _ES_LEMMAS if language == "es" else _PT_LEMMAS
    forms: dict[str, list[PredicateForm]] = {}

    for family, lemmas in lemma_map.items():
        for lemma in lemmas:
            generated = _irregular_forms(language, family, lemma)
            if not generated:
                generated = _regular_forms(language, family, lemma)

            for normalized, form in generated:
                forms.setdefault(normalized, []).append(form)

            participle = _participle(language, lemma)
            normalized_participle, participle_form = _form(
                family,
                lemma,
                language,
                None,
                None,
                "participle",
                "participle",
                participle,
                voice="participle",
            )
            forms.setdefault(normalized_participle, []).append(participle_form)

    return {surface: tuple(entries) for surface, entries in forms.items()}


PARADIGMS: dict[str, dict[str, tuple[PredicateForm, ...]]] = {
    "es": _build_paradigm("es"),
    "pt": _build_paradigm("pt"),
}


def _compound_match(
    tokens: tuple[Token, ...],
    index: int,
    language: str,
) -> list[PredicateMatch]:
    if index + 1 >= len(tokens):
        return []

    aux_table = _ES_AUXILIARIES if language == "es" else _PT_AUXILIARIES
    aux = tokens[index]
    participle = tokens[index + 1]

    results: list[PredicateMatch] = []
    for tense_aspect, auxiliaries in aux_table.items():
        for aux_surface, person, number in auxiliaries:
            if aux.normalized != _normalize_word(aux_surface):
                continue
            for form in PARADIGMS[language].get(participle.normalized, ()):
                if form.tense_aspect != "participle":
                    continue
                compound_form = PredicateForm(
                    family=form.family,
                    lemma=form.lemma,
                    language=language,
                    person=person,
                    number=number,
                    tense_aspect=tense_aspect,
                    mood="indicative",
                    voice="active",
                    accent_required=_has_acute(aux_surface),
                )
                results.append(
                    PredicateMatch(
                        form=compound_form,
                        token_start=index,
                        token_end=index + 2,
                        accent_ambiguous=(
                            compound_form.accent_required and not aux.had_acute
                        ),
                    )
                )
    return results


_ES_NOMINAL_DETERMINERS = frozenset(
    {
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
        "aquel", "aquella", "aquellos", "aquellas",
        "mi", "mis", "su", "sus",
        "del", "al", "otro", "otra", "otros", "otras",
    }
)
_PT_NOMINAL_DETERMINERS = frozenset(
    {
        "o", "a", "os", "as", "um", "uma", "uns", "umas",
        "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
        "aquele", "aquela", "aqueles", "aquelas",
        "meu", "minha", "meus", "minhas", "seu", "sua", "seus", "suas",
        "deste", "desta", "destes", "destas",
        "desse", "dessa", "desses", "dessas",
        "neste", "nesta", "nestes", "nestas",
        "nesse", "nessa", "nesses", "nessas",
        "outro", "outra", "outros", "outras",
    }
)
_ES_NOMINAL_QUANTIFIERS = frozenset(
    {
        "ningun", "ninguno", "ninguna", "ningunos", "ningunas",
        "algun", "alguno", "alguna", "algunos", "algunas",
        "varios", "varias", "muchos", "muchas", "pocos", "pocas",
        "cada",
    }
)
_PT_NOMINAL_QUANTIFIERS = frozenset(
    {
        "nenhum", "nenhuma", "nenhuns", "nenhumas",
        "algum", "alguma", "alguns", "algumas",
        "varios", "varias", "muitos", "muitas", "poucos", "poucas",
        "cada",
    }
)
_ES_NOMINAL_NUMERALS = frozenset(
    {"uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"}
)
_PT_NOMINAL_NUMERALS = frozenset(
    {"um", "uma", "dois", "duas", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"}
)
_ES_CLOSED_PRENOMINAL_MODIFIERS = frozenset(
    {
        "otro", "otra", "otros", "otras",
        *_ES_NOMINAL_NUMERALS,
        "primer", "primero", "primera", "primeros", "primeras",
        "segundo", "segunda", "segundos", "segundas",
        "ultimo", "ultima", "ultimos", "ultimas",
    }
)
_PT_CLOSED_PRENOMINAL_MODIFIERS = frozenset(
    {
        "outro", "outra", "outros", "outras",
        *_PT_NOMINAL_NUMERALS,
        "primeiro", "primeira", "primeiros", "primeiras",
        "segundo", "segunda", "segundos", "segundas",
        "ultimo", "ultima", "ultimos", "ultimas",
    }
)


def _is_closed_prenominal_modifier(word: str, language: str) -> bool:
    modifiers = (
        _ES_CLOSED_PRENOMINAL_MODIFIERS
        if language == "es"
        else _PT_CLOSED_PRENOMINAL_MODIFIERS
    )
    return word in modifiers or word.isdigit()


def _closed_nominal_head_index(
    analysis: FoundationAnalysis,
    start: int,
    stop: int,
    language: str,
) -> int | None:
    index = start
    while (
        index < stop
        and _is_closed_prenominal_modifier(
            analysis.tokens[index].normalized,
            language,
        )
    ):
        index += 1
    return index if index < stop else None
_ES_NOMINAL_EXISTENTIALS = frozenset(
    {"tengo", "tenemos", "hay", "habia", "hubo", "aparecio", "aparecieron"}
)
_PT_NOMINAL_EXISTENTIALS = frozenset(
    {"tenho", "temos", "ha", "havia", "houve", "apareceu", "apareceram"}
)
_ES_NOMINAL_ACTIVITY_ADJECTIVES = frozenset(
    {
        "fraudulento", "fraudulenta", "fraudulentos", "fraudulentas",
        "autorizado", "autorizada", "autorizados", "autorizadas",
    }
)
_PT_NOMINAL_ACTIVITY_ADJECTIVES = frozenset(
    {
        "fraudulento", "fraudulenta", "fraudulentos", "fraudulentas",
        "autorizado", "autorizada", "autorizados", "autorizadas",
    }
)
_NOMINAL_ACTIVITY_BOUNDARIES = frozenset({".", "?", "!", ";", ":", "¿", "¡"})


def _activity_nominal_modifier_follows(
    tokens: tuple[Token, ...],
    index: int,
    language: str,
) -> bool:
    adjectives = (
        _ES_NOMINAL_ACTIVITY_ADJECTIVES
        if language == "es"
        else _PT_NOMINAL_ACTIVITY_ADJECTIVES
    )
    following = index + 1
    if following >= len(tokens):
        return False
    if tokens[following].normalized in adjectives:
        return True

    denial = "no" if language == "es" else "nao"
    return (
        tokens[following].normalized == denial
        and following + 1 < len(tokens)
        and tokens[following + 1].normalized in adjectives
    )


def _looks_nominal(
    tokens: tuple[Token, ...],
    index: int,
    language: str,
) -> bool:
    activity = _ES_ACTIVITY if language == "es" else _PT_ACTIVITY
    if tokens[index].normalized not in activity:
        return False

    determiners = (
        _ES_NOMINAL_DETERMINERS
        if language == "es"
        else _PT_NOMINAL_DETERMINERS
    )
    quantifiers = (
        _ES_NOMINAL_QUANTIFIERS
        if language == "es"
        else _PT_NOMINAL_QUANTIFIERS
    )
    numerals = (
        _ES_NOMINAL_NUMERALS
        if language == "es"
        else _PT_NOMINAL_NUMERALS
    )
    existentials = (
        _ES_NOMINAL_EXISTENTIALS
        if language == "es"
        else _PT_NOMINAL_EXISTENTIALS
    )

    if index > 0:
        previous = tokens[index - 1]
        if previous.normalized in determiners | quantifiers | numerals | existentials:
            return True
        if previous.normalized.isdigit() or previous.is_txid:
            return True

        if _is_closed_prenominal_modifier(previous.normalized, language):
            cursor = index - 1
            while cursor >= 0 and _is_closed_prenominal_modifier(
                tokens[cursor].normalized,
                language,
            ):
                cursor -= 1
            if (
                cursor >= 0
                and tokens[cursor].normalized in determiners | quantifiers
            ):
                return True

    clause_initial = (
        index == 0
        or tokens[index - 1].normalized in _NOMINAL_ACTIVITY_BOUNDARIES
    )
    if clause_initial and _activity_nominal_modifier_follows(
        tokens,
        index,
        language,
    ):
        return True

    if index + 1 < len(tokens) and tokens[index + 1].is_txid:
        return True
    return False


def find_predicates(
    tokens: Iterable[Token],
    language: str,
) -> tuple[PredicateMatch, ...]:
    token_tuple = tuple(tokens)
    if language not in PARADIGMS:
        raise ValueError(f"unsupported language: {language}")

    matches: list[PredicateMatch] = []
    compound_consumed: set[int] = set()
    for index, token in enumerate(token_tuple):
        compounds = _compound_match(token_tuple, index, language)
        if compounds:
            matches.extend(compounds)
            compound_consumed.add(index + 1)

        if index in compound_consumed:
            continue
        if _looks_nominal(token_tuple, index, language):
            continue

        for form in PARADIGMS[language].get(token.normalized, ()):
            if form.tense_aspect == "participle":
                continue
            matches.append(
                PredicateMatch(
                    form=form,
                    token_start=index,
                    token_end=index + 1,
                    accent_ambiguous=form.accent_required and not token.had_acute,
                )
            )

    return tuple(matches)


_ES_ACTIVITY = frozenset(
    {
        "cargo",
        "cargos",
        "cobro",
        "cobros",
        "compra",
        "compras",
        "pago",
        "pagos",
        "movimiento",
        "movimientos",
        "operacion",
        "operaciones",
        "transaccion",
        "transacciones",
        "transferencia",
        "transferencias",
        "debito",
        "debitos",
        "retiro",
        "retiros",
        "consumo",
        "consumos",
    }
)

_PT_ACTIVITY = frozenset(
    {
        "cobranca",
        "cobrancas",
        "compra",
        "compras",
        "pagamento",
        "pagamentos",
        "lancamento",
        "lancamentos",
        "operacao",
        "operacoes",
        "transacao",
        "transacoes",
        "transferencia",
        "transferencias",
        "pix",
        "debito",
        "debitos",
        "saque",
        "saques",
        "gasto",
        "gastos",
        "ted",
        "boleto",
        "boletos",
        "movimentacao",
        "movimentacoes",
    }
)

_ES_INSTRUMENT = frozenset({"tarjeta", "cuenta", "billetera", "wallet"})
_PT_INSTRUMENT = frozenset({"cartao", "conta", "carteira", "wallet"})

_ES_SELF = frozenset({"yo", "me", "mi", "mio", "mia", "mios", "mias", "nosotros", "nosotras"})
_PT_SELF = frozenset({"eu", "me", "mim", "meu", "minha", "meus", "minhas", "nos"})

_ES_THIRD = frozenset({"alguien", "tercero", "tercera", "persona"})
_PT_THIRD = frozenset({"alguem", "terceiro", "terceira", "pessoa"})

_ES_RELATIONAL_NOUNS = frozenset(
    {
        "hermano", "hermana", "madre", "padre", "mama", "papa",
        "hijo", "hija", "esposo", "esposa", "marido", "pareja",
        "novio", "novia", "amigo", "amiga", "companero", "companera",
        "vecino", "vecina", "empleado", "empleada",
        "primo", "prima", "sobrino", "sobrina", "tio", "tia",
        "nieto", "nieta", "cunado", "cunada", "abuelo", "abuela",
    }
)
_PT_RELATIONAL_NOUNS = frozenset(
    {
        "irmao", "irma", "mae", "pai",
        "filho", "filha", "marido", "esposa", "esposo",
        "parceiro", "parceira", "namorado", "namorada",
        "amigo", "amiga", "companheiro", "companheira", "colega",
        "vizinho", "vizinha", "funcionario", "funcionaria",
        "primo", "prima", "sobrinho", "sobrinha", "tio", "tia",
        "neto", "neta", "cunhado", "cunhada", "avo",
    }
)

_ES_NEG_QUANT = frozenset({"nadie", "ninguno", "ninguna", "ningunos", "ningunas"})
_PT_NEG_QUANT = frozenset({"ninguem", "nenhum", "nenhuma", "nenhuns", "nenhumas"})

_ES_AUTH_NOUN = frozenset({"autorizacion", "permiso", "consentimiento"})
_PT_AUTH_NOUN = frozenset({"autorizacao", "permissao", "consentimento", "anuencia"})

_ES_FRAUD = frozenset({"fraude", "fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"})
_PT_FRAUD = frozenset({"fraude", "golpe", "fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"})

_ES_DESCRIPTOR = frozenset({"nombre", "comercio", "establecimiento", "descriptor", "descripcion"})
_PT_DESCRIPTOR = frozenset({"nome", "comercio", "estabelecimento", "descritor", "descricao"})

_ES_SECURITY = frozenset({"seguridad", "proteccion", "alerta", "alertas", "notificacion", "notificaciones", "medidas", "controles"})
_PT_SECURITY = frozenset({"seguranca", "protecao", "alerta", "alertas", "notificacao", "notificacoes", "medidas", "controles", "cuidados"})

_ES_UNCERTAINTY = frozenset({"quizas", "talvez"})
_PT_UNCERTAINTY = frozenset({"talvez"})

_ES_CONTRAST = frozenset({"pero", "sino", "aunque"})
_PT_CONTRAST = frozenset({"mas", "porem", "embora"})


def _next_predicate_index(
    index: int,
    predicates: tuple[PredicateMatch, ...],
    *,
    max_gap: int = 2,
) -> int | None:
    for predicate in predicates:
        if predicate.token_start < index:
            continue
        if predicate.token_start - index <= max_gap:
            return predicate.token_start
        break
    return None


def _is_conditional_marker(
    index: int,
    tokens: tuple[Token, ...],
    predicates: tuple[PredicateMatch, ...],
    language: str,
) -> bool:
    token = tokens[index]
    word = token.normalized
    if language == "es":
        if word != "si" or token.had_acute:
            return False
    else:
        if word not in {"se", "caso"}:
            return False

    if index > 0:
        previous = tokens[index - 1].normalized
        if previous not in {".", "?", "!", ";", ":", "-", "¿", "¡", "pero", "mas", "porem"}:
            return False

    for predicate in predicates:
        if predicate.token_start <= index:
            continue
        if predicate.token_start - index > 5:
            break
        if language == "pt" and word == "caso" and predicate.form.mood != "subjunctive":
            continue
        return True
    return False


def tag_tokens(
    tokens: Iterable[Token],
    language: str,
    predicates: Iterable[PredicateMatch] = (),
) -> tuple[frozenset[LexicalTag], ...]:
    token_tuple = tuple(tokens)
    predicate_tuple = tuple(predicates)
    if language not in {"es", "pt"}:
        raise ValueError(f"unsupported language: {language}")

    activity = _ES_ACTIVITY if language == "es" else _PT_ACTIVITY
    instrument = _ES_INSTRUMENT if language == "es" else _PT_INSTRUMENT
    self_words = _ES_SELF if language == "es" else _PT_SELF
    third_party = _ES_THIRD if language == "es" else _PT_THIRD
    neg_quant = _ES_NEG_QUANT if language == "es" else _PT_NEG_QUANT
    auth_noun = _ES_AUTH_NOUN if language == "es" else _PT_AUTH_NOUN
    fraud = _ES_FRAUD if language == "es" else _PT_FRAUD
    descriptor = _ES_DESCRIPTOR if language == "es" else _PT_DESCRIPTOR
    security = _ES_SECURITY if language == "es" else _PT_SECURITY
    uncertainty = _ES_UNCERTAINTY if language == "es" else _PT_UNCERTAINTY
    contrast = _ES_CONTRAST if language == "es" else _PT_CONTRAST

    predicate_starts = {predicate.token_start for predicate in predicate_tuple}
    tags: list[frozenset[LexicalTag]] = []
    for index, token in enumerate(token_tuple):
        current: set[LexicalTag] = set()
        word = token.normalized

        if token.is_txid:
            current.add(LexicalTag.TXID)
            current.add(LexicalTag.ACTIVITY)
        if word in activity and index not in predicate_starts:
            current.add(LexicalTag.ACTIVITY)
        if word in instrument:
            current.add(LexicalTag.INSTRUMENT)
        if word in self_words:
            current.add(LexicalTag.SELF)
        if (
            language == "pt"
            and word in {"a", "gente"}
            and (
                (word == "a" and index + 1 < len(token_tuple) and token_tuple[index + 1].normalized == "gente")
                or (word == "gente" and index > 0 and token_tuple[index - 1].normalized == "a")
            )
        ):
            current.add(LexicalTag.SELF)
        if word in third_party:
            current.add(LexicalTag.THIRD_PARTY)
        if word in neg_quant:
            current.add(LexicalTag.NEG_QUANTIFIER)
        if word in auth_noun:
            current.add(LexicalTag.AUTH_NOUN)
        if word in fraud:
            current.add(LexicalTag.FRAUD_MARKER)
        if word in descriptor:
            current.add(LexicalTag.DESCRIPTOR_NOUN)
        if word in security:
            current.add(LexicalTag.SECURITY_INFO)
        if word in uncertainty:
            current.add(LexicalTag.UNCERTAINTY)
        if word in contrast:
            current.add(LexicalTag.CONTRAST)

        if language == "es":
            if word == "no":
                next_predicate = _next_predicate_index(index + 1, predicate_tuple, max_gap=1)
                if next_predicate is not None:
                    current.add(LexicalTag.NEGATOR)
            if word in {"ni"}:
                current.add(LexicalTag.COORD_NEGATION)
            if word in {"mio", "mia", "mios", "mias"}:
                current.add(LexicalTag.OWNERSHIP)
            if _is_conditional_marker(index, token_tuple, predicate_tuple, language):
                current.add(LexicalTag.CONDITIONAL)
            if token.surface == "¿":
                current.add(LexicalTag.QUESTION_OPEN)
            if token.surface == "?":
                current.add(LexicalTag.QUESTION_CLOSE)
        else:
            if word == "nao":
                current.add(LexicalTag.NEGATOR)
            if word == "nem":
                current.add(LexicalTag.COORD_NEGATION)
            if word in {"meu", "minha", "meus", "minhas"}:
                current.add(LexicalTag.OWNERSHIP)
            if _is_conditional_marker(index, token_tuple, predicate_tuple, language):
                current.add(LexicalTag.CONDITIONAL)

        tags.append(frozenset(current))

    return tuple(tags)


def _spanish_mi_pair_allows_self_role(
    tokens: tuple[Token, ...],
    mi_index: int,
) -> bool:
    """Distinguish accented pronoun mí from possessive mi before a noun."""

    token = tokens[mi_index]
    if token.normalized != "mi":
        return True
    if token.had_acute:
        return True
    if mi_index + 1 >= len(tokens):
        return True

    following = tokens[mi_index + 1].normalized
    if following == "parte":
        return True

    nominal_heads = (
        _ES_ACTIVITY
        | _ES_INSTRUMENT
        | _ES_RELATIONAL_NOUNS
        | _ES_AUTH_NOUN
        | _ES_DESCRIPTOR
        | _ES_SECURITY
    )
    return following not in nominal_heads


def find_self_evidence(
    tokens: Iterable[Token],
    predicates: Iterable[PredicateMatch],
    language: str,
) -> tuple[SelfEvidence, ...]:
    token_tuple = tuple(tokens)
    predicate_tuple = tuple(predicates)
    evidence: list[SelfEvidence] = []

    if language == "es":
        subject_words = {"yo", "nosotros", "nosotras"}
        possessor_words = {"mi", "mio", "mia", "mios", "mias"}
        dative_words = {"me"}
        agent_pairs = {("por", "mi")}
        source_pairs = {("de", "mi")}
        source_triplets = {("de", "mi", "parte")}
        dative_pairs = {("a", "mi"), ("para", "mi")}
    elif language == "pt":
        subject_words = {"eu", "nos"}
        possessor_words = {"meu", "minha", "meus", "minhas"}
        dative_words = {"me"}
        agent_pairs = {("por", "mim")}
        source_pairs = {("de", "mim")}
        source_triplets = {("da", "minha", "parte")}
        dative_pairs = {("a", "mim"), ("para", "mim"), ("pra", "mim")}
    else:
        raise ValueError(f"unsupported language: {language}")

    words = [token.normalized for token in token_tuple]

    for index, word in enumerate(words):
        if word in subject_words and not (
            language == "pt"
            and word == "nos"
            and not token_tuple[index].had_acute
        ):
            evidence.append(SelfEvidence(SelfRole.SUBJECT, index, index + 1))
        if language == "pt" and index + 1 < len(words) and (word, words[index + 1]) == ("a", "gente"):
            evidence.append(SelfEvidence(SelfRole.SUBJECT, index, index + 2))
        if word in possessor_words and not (
            language == "es" and word == "mi" and token_tuple[index].had_acute
        ):
            evidence.append(SelfEvidence(SelfRole.POSSESSOR, index, index + 1))
        if word in dative_words:
            evidence.append(SelfEvidence(SelfRole.DATIVE, index, index + 1))

        if index + 1 < len(words):
            pair = (word, words[index + 1])
            if pair in agent_pairs:
                evidence.append(SelfEvidence(SelfRole.AGENT, index, index + 2))
            if pair in source_pairs and (
                language != "es"
                or _spanish_mi_pair_allows_self_role(token_tuple, index + 1)
            ):
                evidence.append(SelfEvidence(SelfRole.SOURCE, index, index + 2))
            if pair in dative_pairs and (
                language != "es"
                or _spanish_mi_pair_allows_self_role(token_tuple, index + 1)
            ):
                evidence.append(SelfEvidence(SelfRole.DATIVE, index, index + 2))

        if index + 2 < len(words):
            triplet = (word, words[index + 1], words[index + 2])
            if triplet in source_triplets:
                evidence.append(SelfEvidence(SelfRole.SOURCE, index, index + 3))

    for predicate in predicate_tuple:
        if predicate.form.person != 1:
            continue
        evidence.append(
            SelfEvidence(
                SelfRole.SUBJECT,
                predicate.token_start,
                predicate.token_end,
                implicit_from_predicate=True,
                ambiguous=predicate.accent_ambiguous,
            )
        )

    unique: dict[tuple[SelfRole, int, int, bool, bool], SelfEvidence] = {}
    for item in evidence:
        unique[
            (
                item.role,
                item.token_start,
                item.token_end,
                item.implicit_from_predicate,
                item.ambiguous,
            )
        ] = item
    return tuple(unique.values())


def _colon_has_finite_predicate(
    token_index: int,
    tokens: tuple[Token, ...],
    predicates: tuple[PredicateMatch, ...],
    text: str,
) -> bool:
    next_boundary = len(tokens)
    for index in range(token_index + 1, len(tokens)):
        if _is_primary_boundary(text, tokens[index]):
            next_boundary = index
            break

    return any(
        predicate.token_start > token_index
        and predicate.token_start < next_boundary
        and predicate.form.person is not None
        for predicate in predicates
    )


def segment_clauses(
    text: str,
    tokens: Iterable[Token],
    predicates: Iterable[PredicateMatch] = (),
) -> tuple[ClauseSegment, ...]:
    token_tuple = tuple(tokens)
    predicate_tuple = tuple(predicates)
    if not token_tuple:
        return ()

    boundaries: list[int] = []
    for index, token in enumerate(token_tuple):
        is_boundary = _is_primary_boundary(text, token)
        if token.normalized == ":":
            is_boundary = _colon_has_finite_predicate(
                index,
                token_tuple,
                predicate_tuple,
                text,
            )
        if is_boundary:
            boundaries.append(index)

    segments: list[ClauseSegment] = []
    start = 0
    segment_index = 0
    for boundary in boundaries:
        if boundary > start:
            segments.append(
                ClauseSegment(
                    index=segment_index,
                    token_start=start,
                    token_end=boundary,
                    source_start=token_tuple[start].start,
                    source_end=token_tuple[boundary - 1].end,
                )
            )
            segment_index += 1
        start = boundary + 1

    if start < len(token_tuple):
        segments.append(
            ClauseSegment(
                index=segment_index,
                token_start=start,
                token_end=len(token_tuple),
                source_start=token_tuple[start].start,
                source_end=token_tuple[-1].end,
            )
        )

    return tuple(segments)


def analyze_foundation(text: str, language: str) -> FoundationAnalysis:
    """Return RF1H-B1 structural primitives without classifying authorization."""

    tokens = tokenize_with_source(text)
    predicates = find_predicates(tokens, language)
    tags = tag_tokens(tokens, language, predicates)
    self_evidence = find_self_evidence(tokens, predicates, language)
    clauses = segment_clauses(text, tokens, predicates)
    return FoundationAnalysis(
        tokens=tokens,
        clauses=clauses,
        predicates=predicates,
        tags=tags,
        self_evidence=self_evidence,
    )


class PropositionFamily(str, Enum):
    OWNERSHIP_DENIAL = "ownership_denial"
    PERFORMANCE_DENIAL = "performance_denial"
    ORIGINATION_DENIAL = "origination_denial"
    AUTHORIZATION_DENIAL = "authorization_denial"
    THIRD_PARTY_UNAUTHORIZED_USE = "third_party_unauthorized_use"
    FRAUD_CHARACTERIZATION = "fraud_characterization"
    ACTIVITY_NONRECOGNITION = "activity_nonrecognition"
    COMPROMISE_LINKED_ACTIVITY = "compromise_linked_activity"


class EvidenceAtomKind(str, Enum):
    SELF_PERFORMED = "self_performed"
    SELF_AUTHORIZED = "self_authorized"


class PropositionMode(str, Enum):
    """RF1H-B3 local proposition modes."""

    ASSERTIVE = "assertive"
    HYPOTHETICAL = "hypothetical"
    UNCERTAIN = "uncertain"
    INFORMATION_REQUEST = "information_request"
    DESCRIPTOR_CLARIFICATION = "descriptor_clarification"
    AUTHORIZED_THIRD_PARTY = "authorized_third_party"
    RETRACTED = "retracted"
    QUESTIONED = "questioned"
    REPORTED_PRIOR_BELIEF = "reported_prior_belief"


@dataclass(frozen=True)
class ScopeDomain:
    """Bounded B3 operator domain over token positions."""

    mode: PropositionMode
    token_start: int
    token_end: int
    provenance: str




@dataclass(frozen=True)
class EvidenceAtom:
    kind: EvidenceAtomKind
    activity_token_span: tuple[int, int]
    predicate_token_span: tuple[int, int]
    self_token_span: tuple[int, int]


@dataclass(frozen=True)
class PositiveProposition:
    """Unresolved RF1H-B2 positive proposition.

    Scope/exclusion and retraction fields are intentionally present now so B3 can
    resolve propositions without changing the proposition audit shape.
    """

    family: PropositionFamily
    rule: str
    language: str
    clause_index: int
    token_start: int
    token_end: int
    source_start: int
    source_end: int
    activity_token_span: tuple[int, int] | None
    activity_ref: str
    predicate_token_span: tuple[int, int] | None
    evidence_token_spans: tuple[tuple[int, int], ...]
    counter_evidence: tuple[EvidenceAtom, ...] = ()
    mode: str = "unresolved"
    exclusion_provenance: tuple[str, ...] = ()
    retraction_provenance: tuple[str, ...] = ()


_ES_COPULA = frozenset({"es", "son", "era", "eran", "fue", "fueron"})
_PT_COPULA = frozenset({"e", "sao", "era", "eram", "foi", "foram"})

_ES_ALIENATION_WORDS = frozenset({"ajeno", "ajena", "ajenos", "ajenas"})
_PT_ALIENATION_WORDS = frozenset({"alheio", "alheia", "alheios", "alheias"})

_ES_ALIENATION_PHRASES = (
    ("de", "otra", "persona"),
    ("de", "otras", "personas"),
    ("de", "un", "tercero"),
    ("de", "terceros"),
)
_PT_ALIENATION_PHRASES = (
    ("de", "outra", "pessoa"),
    ("de", "outras", "pessoas"),
    ("de", "um", "terceiro"),
    ("de", "terceiros"),
)

_ES_DENIAL_WORDS = frozenset({"no", "nunca", "jamas"})
_PT_DENIAL_WORDS = frozenset({"nao", "nunca", "jamais"})


def _in_clause(span_start: int, span_end: int, clause: ClauseSegment) -> bool:
    return span_start >= clause.token_start and span_end <= clause.token_end


def _negative_indices(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[int, ...]:
    denial_words = _ES_DENIAL_WORDS if language == "es" else _PT_DENIAL_WORDS
    indices: list[int] = []
    for index in range(clause.token_start, clause.token_end):
        if analysis.tokens[index].normalized in denial_words:
            indices.append(index)
            continue
        if analysis.tags[index] & {
            LexicalTag.NEGATOR,
            LexicalTag.NEG_QUANTIFIER,
            LexicalTag.COORD_NEGATION,
        }:
            indices.append(index)
    return tuple(dict.fromkeys(indices))


def _activity_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.ACTIVITY in analysis.tags[index]
    )


def _nearest_activity_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch | None,
) -> tuple[int, int] | None:
    spans = _activity_spans(analysis, clause)
    if not spans:
        return None
    if predicate is None:
        return spans[0]
    return min(
        spans,
        key=lambda span: min(
            abs(span[0] - predicate.token_start),
            abs(span[0] - (predicate.token_end - 1)),
        ),
    )


def _self_roles_in_clause(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[SelfEvidence, ...]:
    return tuple(
        item
        for item in analysis.self_evidence
        if _in_clause(item.token_start, item.token_end, clause)
    )


_ES_DENIAL_BRIDGE_WORDS = frozenset(
    {
        "yo", "nosotros", "nosotras",
        "me", "te", "se", "lo", "la", "los", "las", "le", "les",
        "de", "mi", "mis", "nuestro", "nuestra", "nuestros", "nuestras",
        "nunca", "jamas", "tampoco", "ni",
    }
)
_PT_DENIAL_BRIDGE_WORDS = frozenset(
    {
        "eu", "nos",
        "me", "te", "se", "o", "a", "os", "as", "lhe", "lhes",
        "de", "do", "da", "dos", "das", "meu", "minha", "meus", "minhas",
        "nunca", "jamais", "tambem", "tampouco", "nem", "que",
    }
)
_DENIAL_BINDING_BARRIERS = frozenset({",", ";", "?", "¿", "!", "¡", ":"})


def _bound_denial_index_for_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    token_start: int,
    token_end: int,
    language: str,
) -> int | None:
    bridge_words = (
        _ES_DENIAL_BRIDGE_WORDS
        if language == "es"
        else _PT_DENIAL_BRIDGE_WORDS
    )
    candidates: list[int] = []

    for index in _negative_indices(analysis, clause, language):
        if index <= token_start:
            if token_start - index > 5:
                continue
            between = range(index + 1, token_start)
            if any(
                analysis.tokens[item].surface in _DENIAL_BINDING_BARRIERS
                for item in between
            ):
                continue
            non_bridge = tuple(
                item
                for item in between
                if analysis.tokens[item].normalized not in bridge_words
            )
            if non_bridge:
                token_tags = analysis.tags[index]
                has_prior_correlative = (
                    LexicalTag.COORD_NEGATION in token_tags
                    and any(
                        prior < index
                        and LexicalTag.COORD_NEGATION in analysis.tags[prior]
                        for prior in _negative_indices(
                            analysis,
                            clause,
                            language,
                        )
                    )
                )
                if not has_prior_correlative:
                    continue
            candidates.append(index)
            continue

        if index >= token_end:
            if index - token_end > 2:
                continue
            if language != "pt":
                continue
            if analysis.tokens[index].normalized != "nao":
                continue
            if index != clause.token_end - 1:
                continue
            between = range(token_end, index)
            if any(
                analysis.tokens[item].surface in _DENIAL_BINDING_BARRIERS
                for item in between
            ):
                continue
            if any(
                (
                    analysis.tokens[item].normalized == "nem"
                    or (
                        analysis.tokens[item].normalized == "e"
                        and not analysis.tokens[item].had_acute
                    )
                )
                for item in between
            ):
                continue
            candidates.append(index)

    if not candidates:
        return None
    return min(
        candidates,
        key=lambda index: min(
            abs(index - token_start),
            abs(index - token_end),
        ),
    )



def _bound_denial_index(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> int | None:
    return _bound_denial_index_for_span(
        analysis,
        clause,
        predicate.token_start,
        predicate.token_end,
        language,
    )


def _span_has_bound_denial(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    token_start: int,
    token_end: int,
    language: str,
) -> bool:
    return _bound_denial_index_for_span(
        analysis,
        clause,
        token_start,
        token_end,
        language,
    ) is not None

def _predicate_has_denial(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    return _bound_denial_index(
        analysis,
        clause,
        predicate,
        language,
    ) is not None


def _source_span_for_token_span(
    analysis: FoundationAnalysis,
    span: tuple[int, int],
) -> tuple[int, int]:
    start, end = span
    return analysis.tokens[start].start, analysis.tokens[end - 1].end


def _make_proposition(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    *,
    family: PropositionFamily,
    rule: str,
    language: str,
    evidence_spans: Iterable[tuple[int, int]],
    activity_span: tuple[int, int] | None,
    predicate: PredicateMatch | None,
    activity_ref: str | None = None,
    counter_evidence: Iterable[EvidenceAtom] = (),
) -> PositiveProposition:
    evidence = tuple(evidence_spans)
    concrete_spans = list(evidence)
    if activity_span is not None and activity_span not in concrete_spans:
        concrete_spans.append(activity_span)
    if predicate is not None:
        predicate_span = (predicate.token_start, predicate.token_end)
        if predicate_span not in concrete_spans:
            concrete_spans.append(predicate_span)
    else:
        predicate_span = None

    token_start = min(span[0] for span in concrete_spans)
    token_end = max(span[1] for span in concrete_spans)
    source_start = analysis.tokens[token_start].start
    source_end = analysis.tokens[token_end - 1].end

    return PositiveProposition(
        family=family,
        rule=rule,
        language=language,
        clause_index=clause.index,
        token_start=token_start,
        token_end=token_end,
        source_start=source_start,
        source_end=source_end,
        activity_token_span=activity_span,
        activity_ref=(
            activity_ref
            if activity_ref is not None
            else ("explicit_activity" if activity_span is not None else "topic_transaction")
        ),
        predicate_token_span=predicate_span,
        evidence_token_spans=tuple(concrete_spans),
        counter_evidence=tuple(counter_evidence),
    )


_ES_P1_NEG_QUANT_BRIDGES = frozenset(
    {
        "de", "del",
        "el", "la", "los", "las",
        "este", "esta", "estos", "estas",
        "ese", "esa", "esos", "esas",
        "aquel", "aquella", "aquellos", "aquellas",
    }
)
_PT_P1_NEG_QUANT_BRIDGES = frozenset(
    {
        "de", "do", "da", "dos", "das",
        "o", "a", "os", "as",
        "deste", "desta", "destes", "destas",
        "desse", "dessa", "desses", "dessas",
        "daquele", "daquela", "daqueles", "daquelas",
    }
)


def _p1_negative_quantifier_anchor(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
) -> int | None:
    bridges = (
        _ES_P1_NEG_QUANT_BRIDGES
        if language == "es"
        else _PT_P1_NEG_QUANT_BRIDGES
    )
    activity_start, activity_end = activity_span
    if activity_end > copula_index or copula_index - activity_end > 2:
        return None

    for index in range(activity_start - 1, clause.token_start - 1, -1):
        if activity_start - index > 4:
            break
        if LexicalTag.NEG_QUANTIFIER not in analysis.tags[index]:
            continue
        if all(
            analysis.tokens[item].normalized in bridges
            for item in range(index + 1, activity_start)
        ):
            return index
    return None


def _p1_correlative_negative_anchors(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
) -> tuple[int, int] | None:
    activity_start, activity_end = activity_span
    markers = [
        index
        for index in range(clause.token_start, copula_index)
        if LexicalTag.COORD_NEGATION in analysis.tags[index]
    ]

    for second in reversed(markers):
        if second < activity_end or copula_index - second > 5:
            continue
        if any(
            predicate.token_start > second
            and predicate.token_start < copula_index
            and _in_clause(predicate.token_start, predicate.token_end, clause)
            for predicate in analysis.predicates
        ):
            continue

        first = next(
            (
                index
                for index in reversed(markers)
                if index < activity_start
                and activity_start - index <= 3
            ),
            None,
        )
        if first is None:
            continue
        if second < activity_end or second - activity_end > 1:
            continue
        return first, second
    return None


_ES_P1_ELLIPTICAL_ACTIVITY_HEADS = frozenset(
    {"otro", "otra", "otros", "otras"}
)
_PT_P1_ELLIPTICAL_ACTIVITY_HEADS = frozenset(
    {"outro", "outra", "outros", "outras"}
)
_ES_P1_SIMPLE_ARTICLES = frozenset({"el", "la", "los", "las"})
_PT_P1_SIMPLE_ARTICLES = frozenset({"o", "a", "os", "as"})
_ES_P1_ELLIPTICAL_DETERMINERS = frozenset(
    {
        *_ES_P1_SIMPLE_ARTICLES,
        "este", "esta", "estos", "estas",
        "ese", "esa", "esos", "esas",
        "aquel", "aquella", "aquellos", "aquellas",
    }
)
_PT_P1_ELLIPTICAL_DETERMINERS = frozenset(
    {
        *_PT_P1_SIMPLE_ARTICLES,
        "este", "esta", "estes", "estas",
        "esse", "essa", "esses", "essas",
        "aquele", "aquela", "aqueles", "aquelas",
    }
)
_ES_P1_TEMPORAL_WORDS = frozenset({"hoy", "ayer", "antes", "anteayer"})
_PT_P1_TEMPORAL_WORDS = frozenset({"hoje", "ontem", "antes", "anteontem"})
_ES_P1_PREPOSITIONS = frozenset({"de", "en", "por", "para", "con", "sobre"})
_PT_P1_PREPOSITIONS = frozenset({"de", "em", "por", "para", "com", "sobre"})
_PT_P1_FUSED_PREPOSITION_DETERMINERS = frozenset(
    {
        "deste", "desta", "destes", "destas",
        "desse", "dessa", "desses", "dessas",
        "neste", "nesta", "nestes", "nestas",
        "nesse", "nessa", "nesses", "nessas",
    }
)


def _p1_has_pre_copular_nominal_subject(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    copula_index: int,
    language: str,
) -> bool:
    """Recognize only a bounded determiner-headed non-activity subject."""

    words = [token.normalized for token in analysis.tokens]
    determiners = (
        _ES_NOMINAL_DETERMINERS
        if language == "es"
        else _PT_NOMINAL_DETERMINERS
    )
    prepositions = (
        _ES_P1_PREPOSITIONS
        if language == "es"
        else _PT_P1_PREPOSITIONS
    )
    denial_words = (
        {"no", "nunca", "jamas", "tampoco"}
        if language == "es"
        else {"nao", "nunca", "jamais", "tampouco"}
    )
    lower_bound = max(clause.token_start, copula_index - 6)

    for determiner_index in range(copula_index - 1, lower_bound - 1, -1):
        if words[determiner_index] not in determiners:
            continue
        if (
            determiner_index > clause.token_start
            and words[determiner_index - 1] in prepositions
        ):
            continue

        head_index = _closed_nominal_head_index(
            analysis,
            determiner_index + 1,
            copula_index,
            language,
        )
        if head_index is None:
            continue
        if LexicalTag.ACTIVITY in analysis.tags[head_index]:
            continue
        if analysis.tokens[head_index].normalized in _NOMINAL_ACTIVITY_BOUNDARIES:
            continue
        if any(
            predicate.token_start == head_index
            and _in_clause(predicate.token_start, predicate.token_end, clause)
            for predicate in analysis.predicates
        ):
            continue
        if any(
            words[index] not in denial_words
            for index in range(head_index + 1, copula_index)
        ):
            continue
        return True

    return False


def _p1_postcopular_activity_is_prepositional(
    analysis: FoundationAnalysis,
    owner_index: int,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    """Reject fallback activity NPs introduced only as PP material."""

    words = [token.normalized for token in analysis.tokens]
    determiners = (
        _ES_NOMINAL_DETERMINERS
        if language == "es"
        else _PT_NOMINAL_DETERMINERS
    )
    prepositions = (
        _ES_P1_PREPOSITIONS
        if language == "es"
        else _PT_P1_PREPOSITIONS
    )

    index = activity_span[0] - 1
    while index > owner_index:
        word = words[index]
        if (
            language == "pt"
            and word in _PT_P1_FUSED_PREPOSITION_DETERMINERS
        ):
            return True
        if word in determiners or _is_closed_prenominal_modifier(word, language):
            index -= 1
            continue
        return word in prepositions
    return False


def _p1_bounded_elliptical_coordination(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
) -> bool:
    """Allow only a bounded elliptical coordinated activity subject."""

    words = [token.normalized for token in analysis.tokens]
    coordinator = "y" if language == "es" else "e"
    simple_articles = (
        _ES_P1_SIMPLE_ARTICLES
        if language == "es"
        else _PT_P1_SIMPLE_ARTICLES
    )
    determiners = (
        _ES_P1_ELLIPTICAL_DETERMINERS
        if language == "es"
        else _PT_P1_ELLIPTICAL_DETERMINERS
    )
    elliptical_heads = (
        _ES_P1_ELLIPTICAL_ACTIVITY_HEADS
        if language == "es"
        else _PT_P1_ELLIPTICAL_ACTIVITY_HEADS
    )
    numerals = (
        _ES_NOMINAL_NUMERALS
        if language == "es"
        else _PT_NOMINAL_NUMERALS
    )
    temporal_words = (
        _ES_P1_TEMPORAL_WORDS
        if language == "es"
        else _PT_P1_TEMPORAL_WORDS
    )
    denial_words = {"no"} if language == "es" else {"nao"}

    index = activity_span[1]
    temporal_preposition_indices: set[int] = set()

    # The overt first conjunct may carry one closed temporal tail:
    # "cargo de hoy y ..." / "compra de hoje e ...".
    if (
        index + 2 < copula_index
        and words[index] == "de"
        and words[index + 1] in temporal_words
        and words[index + 2] == coordinator
    ):
        temporal_preposition_indices.add(index)
        index += 2

    if index >= copula_index or words[index] != coordinator:
        return False
    index += 1

    determiner: str | None = None
    if index < copula_index and words[index] in determiners:
        determiner = words[index]
        index += 1

    if index < copula_index and words[index] in elliptical_heads:
        index += 1
        while (
            index < copula_index
            and (
                words[index] in numerals
                or words[index].isdigit()
            )
        ):
            index += 1
    elif (
        determiner in simple_articles
        and index + 1 < copula_index
        and words[index] == "de"
        and words[index + 1] in temporal_words
    ):
        temporal_preposition_indices.add(index)
        index += 2
    else:
        return False

    while index < copula_index and words[index] in denial_words:
        index += 1
    if index != copula_index:
        return False

    return not any(
        predicate.token_start >= activity_span[1]
        and predicate.token_start < copula_index
        and _in_clause(predicate.token_start, predicate.token_end, clause)
        and not (
            predicate.token_start in temporal_preposition_indices
            and predicate.token_end == predicate.token_start + 1
            and words[predicate.token_start] == "de"
            and not analysis.tokens[predicate.token_start].had_acute
        )
        for predicate in analysis.predicates
    )


def _p1_activity_subject(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    copula_index: int,
    owner_index: int,
    language: str,
) -> tuple[int, int] | None:
    """Bind P1 ownership to the copula's local activity subject."""

    words = [token.normalized for token in analysis.tokens]
    hard_separators = {
        ",", ";", "?", "¿", "!", "¡", ":",
        *(_ES_CONTRAST if language == "es" else _PT_CONTRAST),
    }
    coordinator = "y" if language == "es" else "e"

    left_candidates = [
        span
        for span in _activity_spans(analysis, clause)
        if span[1] <= copula_index
    ]
    for span in sorted(left_candidates, key=lambda item: item[0], reverse=True):
        if any(
            words[index] in hard_separators
            for index in range(span[1], copula_index)
        ):
            continue

        coordinator_indices = [
            index
            for index in range(span[1], copula_index)
            if words[index] == coordinator
        ]
        if coordinator_indices and not _p1_bounded_elliptical_coordination(
            analysis,
            clause,
            span,
            copula_index,
            language,
        ):
            continue
        return span

    # Bounded post-copular fallback for forms such as "no es mío ese cargo".
    if _p1_has_pre_copular_nominal_subject(
        analysis,
        clause,
        copula_index,
        language,
    ):
        return None

    right_candidates = [
        span
        for span in _activity_spans(analysis, clause)
        if span[0] >= owner_index + 1
        and span[0] - owner_index <= 4
    ]
    for span in sorted(right_candidates, key=lambda item: item[0]):
        if any(
            words[index] in hard_separators or words[index] == coordinator
            for index in range(copula_index + 1, span[0])
        ):
            continue
        if _p1_postcopular_activity_is_prepositional(
            analysis,
            owner_index,
            span,
            language,
        ):
            continue
        return span

    return None


def _ownership_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    activity_spans = _activity_spans(analysis, clause)
    if not activity_spans:
        return []

    copulas = _ES_COPULA if language == "es" else _PT_COPULA
    ownership_indices = [
        index
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.OWNERSHIP in analysis.tags[index]
    ]
    output: list[PositiveProposition] = []

    for copula_index in range(clause.token_start, clause.token_end):
        token = analysis.tokens[copula_index]
        if token.normalized not in copulas:
            continue

        owner_index = next(
            (
                index
                for index in ownership_indices
                if index > copula_index and index - copula_index <= 3
            ),
            None,
        )
        if owner_index is None:
            continue

        activity_span = _p1_activity_subject(
            analysis,
            clause,
            copula_index,
            owner_index,
            language,
        )
        if activity_span is None:
            continue

        if language == "pt" and token.normalized == "e" and not token.had_acute:
            immediately_owned = owner_index == copula_index + 1
            ownership_copula = (
                immediately_owned
                and activity_span[1] == copula_index
            )
            immediately_negated = (
                copula_index > clause.token_start
                and analysis.tokens[copula_index - 1].normalized
                in _PT_DENIAL_WORDS
            )
            intervening_predicate = any(
                predicate.token_start >= activity_span[1]
                and predicate.token_end <= copula_index
                for predicate in analysis.predicates
                if _in_clause(predicate.token_start, predicate.token_end, clause)
            )
            if (
                intervening_predicate
                or not (ownership_copula or immediately_negated)
            ):
                continue

        rule = "P1"
        denial_evidence: tuple[tuple[int, int], ...]

        quantifier_index = _p1_negative_quantifier_anchor(
            analysis,
            clause,
            activity_span,
            copula_index,
            language,
        )
        if quantifier_index is not None:
            rule = "P1-neg-quantifier"
            denial_evidence = ((quantifier_index, quantifier_index + 1),)
        else:
            correlative = _p1_correlative_negative_anchors(
                analysis,
                clause,
                activity_span,
                copula_index,
            )
            if correlative is not None:
                first, second = correlative
                rule = "P1-correlative"
                denial_evidence = (
                    (first, first + 1),
                    (second, second + 1),
                )
            else:
                neg_index = _bound_denial_index_for_span(
                    analysis,
                    clause,
                    copula_index,
                    copula_index + 1,
                    language,
                )
                if neg_index is None:
                    continue
                denial_evidence = ((neg_index, neg_index + 1),)

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.OWNERSHIP_DENIAL,
                rule=rule,
                language=language,
                evidence_spans=(
                    activity_span,
                    *denial_evidence,
                    (copula_index, copula_index + 1),
                    (owner_index, owner_index + 1),
                ),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output


def _alienation_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    activity_spans = _activity_spans(analysis, clause)
    if not activity_spans:
        return []

    words = [token.normalized for token in analysis.tokens]
    singletons = _ES_ALIENATION_WORDS if language == "es" else _PT_ALIENATION_WORDS
    phrases = _ES_ALIENATION_PHRASES if language == "es" else _PT_ALIENATION_PHRASES
    marker_spans: list[tuple[int, int]] = []

    for index in range(clause.token_start, clause.token_end):
        if words[index] in singletons:
            marker_spans.append((index, index + 1))

    for phrase in phrases:
        width = len(phrase)
        for index in range(clause.token_start, clause.token_end - width + 1):
            if tuple(words[index : index + width]) == phrase:
                marker_spans.append((index, index + width))

    output: list[PositiveProposition] = []
    for marker_span in marker_spans:
        activity_span = min(
            activity_spans,
            key=lambda span: abs(span[0] - marker_span[0]),
        )
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.OWNERSHIP_DENIAL,
                rule="P1b",
                language=language,
                evidence_spans=(activity_span, marker_span),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output


def _role_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    allowed: frozenset[SelfRole],
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (item.token_start, item.token_end)
        for item in _self_roles_in_clause(analysis, clause)
        if item.role in allowed
    )


def _bound_self_evidence(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    allowed: frozenset[SelfRole],
) -> SelfEvidence | None:
    candidates: list[SelfEvidence] = []

    for item in _self_roles_in_clause(analysis, clause):
        if item.role not in allowed:
            continue

        if item.implicit_from_predicate:
            if (
                item.token_start == predicate.token_start
                and item.token_end == predicate.token_end
                and predicate.form.person == 1
            ):
                candidates.append(item)
            continue

        if item.role is SelfRole.SUBJECT and predicate.form.person != 1:
            continue

        distance = min(
            abs(item.token_start - predicate.token_end),
            abs(predicate.token_start - item.token_end),
        )
        if distance > 5:
            continue

        left = min(item.token_start, predicate.token_start)
        right = max(item.token_end, predicate.token_end)
        intervening = any(
            other.token_start >= left
            and other.token_end <= right
            and not (
                other.token_start == predicate.token_start
                and other.token_end == predicate.token_end
            )
            and not (
                other.token_start >= item.token_start
                and other.token_end <= item.token_end
            )
            and other.form.person is not None
            and not other.accent_ambiguous
            for other in analysis.predicates
            if _in_clause(other.token_start, other.token_end, clause)
        )
        if intervening:
            continue

        candidates.append(item)

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda item: (
            0 if item.implicit_from_predicate else 1,
            min(
                abs(item.token_start - predicate.token_end),
                abs(predicate.token_start - item.token_end),
            ),
        ),
    )


_DENIAL_ASSERTIVE_TENSES = frozenset(
    {"preterite", "present_perfect", "pluperfect", "participle"}
)
_ES_DIRECTIVE_MARKERS = (
    ("por", "favor"),
    ("para", "que"),
    ("ojala",),
)
_PT_DIRECTIVE_MARKERS = (
    ("por", "favor"),
    ("para", "que"),
    ("tomara", "que"),
)


def _phrase_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    phrase: tuple[str, ...],
    *,
    max_gap: int = 6,
) -> bool:
    width = len(phrase)
    start = max(clause.token_start, predicate.token_start - max_gap)
    words = [token.normalized for token in analysis.tokens]
    for index in range(start, predicate.token_start - width + 1):
        if tuple(words[index : index + width]) == phrase:
            return True
    return False


def _relative_specific_activity_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    words = [token.normalized for token in analysis.tokens]
    for index in range(
        max(clause.token_start, predicate.token_start - 6),
        predicate.token_start,
    ):
        if words[index] != "que":
            continue
        activity_span = next(
            (
                span
                for span in _activity_spans(analysis, clause)
                if span[1] <= index
                and index - span[1] <= 2
                and _customer_anchored_activity(
                    analysis,
                    clause,
                    span,
                    language,
                )
            ),
            None,
        )
        if activity_span is not None:
            return True
    return False


def _explicit_self_subject_binds(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
) -> bool:
    for item in _self_roles_in_clause(analysis, clause):
        if item.role is not SelfRole.SUBJECT or item.implicit_from_predicate:
            continue
        distance = min(
            abs(item.token_start - predicate.token_end),
            abs(predicate.token_start - item.token_end),
        )
        if distance > 5:
            continue
        left = min(item.token_start, predicate.token_start)
        right = max(item.token_end, predicate.token_end)
        if any(
            other.token_start >= left
            and other.token_end <= right
            and not (
                other.token_start == predicate.token_start
                and other.token_end == predicate.token_end
            )
            and other.form.person is not None
            and not other.accent_ambiguous
            for other in analysis.predicates
            if _in_clause(other.token_start, other.token_end, clause)
        ):
            continue
        return True
    return False


def _has_directive_marker_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    markers = (
        _ES_DIRECTIVE_MARKERS
        if language == "es"
        else _PT_DIRECTIVE_MARKERS
    )
    words = [token.normalized for token in analysis.tokens]
    for marker in markers:
        width = len(marker)
        for index in range(
            clause.token_start,
            max(clause.token_start, predicate.token_start - width + 1),
        ):
            if tuple(words[index : index + width]) == marker:
                return True
    return False


def _denial_reference_allowed(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    form = predicate.form

    if (
        predicate.accent_ambiguous
        and predicate.token_end - predicate.token_start == 1
        and not analysis.tokens[predicate.token_start].had_acute
        and analysis.tokens[predicate.token_start].normalized in {"de", "da"}
    ):
        return False

    if predicate.accent_ambiguous and form.person == 1:
        if not _explicit_self_subject_binds(analysis, clause, predicate):
            return False
        if _has_directive_marker_before_predicate(
            analysis,
            clause,
            predicate,
            language,
        ):
            return False

    if form.tense_aspect in _DENIAL_ASSERTIVE_TENSES:
        return True

    if form.mood == "subjunctive":
        introducer = ("sin", "que") if language == "es" else ("sem", "que")
        return _phrase_before_predicate(
            analysis,
            clause,
            predicate,
            introducer,
        )

    if form.tense_aspect in {"present", "imperfect"}:
        return _relative_specific_activity_before_predicate(
            analysis,
            clause,
            predicate,
            language,
        )

    return False


def _predicate_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    *,
    predicate_family: PredicateFamily,
    proposition_family: PropositionFamily,
    rule: str,
    self_roles: frozenset[SelfRole],
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family is not predicate_family:
            continue
        if not _denial_reference_allowed(
            analysis,
            clause,
            predicate,
            language,
        ):
            continue
        if not _predicate_has_denial(analysis, clause, predicate, language):
            continue

        self_evidence = _bound_self_evidence(
            analysis,
            clause,
            predicate,
            self_roles,
        )
        if self_evidence is None:
            continue

        activity_span = _nearest_activity_span(analysis, clause, predicate)
        denial_index = _bound_denial_index(
            analysis,
            clause,
            predicate,
            language,
        )
        if denial_index is None:
            continue
        denial_span = (denial_index, denial_index + 1)
        nearest_self = (
            self_evidence.token_start,
            self_evidence.token_end,
        )
        evidence: list[tuple[int, int]] = [denial_span, nearest_self]
        proposition_rule = rule
        activity_ref = (
            "explicit_activity"
            if activity_span is not None
            else "topic_transaction"
        )

        if (
            activity_span is None
            and proposition_family is PropositionFamily.PERFORMANCE_DENIAL
        ):
            d2_link = _d2_anaphoric_prior_activity(
                analysis,
                clause,
                predicate,
                language,
            )
            if d2_link is not None:
                anaphor_span, activity_span, activity_ref = d2_link
                evidence.extend((anaphor_span, activity_span))
                proposition_rule = f"{rule}-R3-activity-anaphora"

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=proposition_family,
                rule=proposition_rule,
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=activity_ref,
            )
        )
    return output




_ES_KNOWN_ACTORS = frozenset(
    {
        "hermano",
        "hermana",
        "esposo",
        "esposa",
        "marido",
        "pareja",
        "novio",
        "novia",
        "amigo",
        "amiga",
        "companero",
        "companera",
        "empleado",
        "empleada",
        "padre",
        "madre",
        "papa",
        "mama",
        "hijo",
        "hija",
        "primo",
        "prima",
        "sobrino",
        "sobrina",
        "tio",
        "tia",
        "nieto",
        "nieta",
        "cunado",
        "cunada",
    }
)
_PT_KNOWN_ACTORS = frozenset(
    {
        "irmao",
        "irma",
        "marido",
        "esposa",
        "esposo",
        "parceiro",
        "parceira",
        "namorado",
        "namorada",
        "amigo",
        "amiga",
        "companheiro",
        "companheira",
        "colega",
        "funcionario",
        "funcionaria",
        "pai",
        "mae",
        "filho",
        "filha",
        "primo",
        "prima",
        "sobrinho",
        "sobrinha",
        "tio",
        "tia",
        "neto",
        "neta",
        "cunhado",
        "cunhada",
    }
)


def _authorization_participle_forms(language: str) -> frozenset[str]:
    forms: set[str] = set()
    for surface, entries in PARADIGMS[language].items():
        if not any(
            entry.family is PredicateFamily.AUTHORIZE
            and entry.tense_aspect == "participle"
            for entry in entries
        ):
            continue
        forms.add(surface)
        if surface.endswith("o"):
            stem = surface[:-1]
            forms.update({stem + "a", stem + "os", stem + "as"})
    return frozenset(forms)


_AUTH_PARTICIPLES = {
    "es": _authorization_participle_forms("es"),
    "pt": _authorization_participle_forms("pt"),
}


def _auth_noun_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.AUTH_NOUN in analysis.tags[index]
    )


def _known_actor_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    actor_words = _ES_KNOWN_ACTORS if language == "es" else _PT_KNOWN_ACTORS
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if analysis.tokens[index].normalized in actor_words
    )


def _same_clause_permission_denial_backlink(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    authorization: PredicateMatch,
) -> tuple[ClauseSegment, tuple[int, int], tuple[int, int] | None, PredicateMatch] | None:
    words = [token.normalized for token in analysis.tokens]
    connector = "y" if language == "es" else "e"
    actor_spans = _known_actor_spans(analysis, clause, language)
    if not actor_spans:
        return None

    customer_instruments = tuple(
        item
        for item in _customer_instrument_spans(analysis, clause)
        if item[0][0] < authorization.token_start
    )

    candidates = [
        predicate
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, clause)
        and predicate.token_end <= authorization.token_start
        and predicate.form.family in {
            PredicateFamily.PERFORM,
            PredicateFamily.USE_ACCESS,
        }
        and _source_accent_selects_predicate(analysis, predicate)
    ]
    for action in reversed(candidates):
        if not _third_party_action_allowed(action):
            continue

        boundary_present = any(
            analysis.tokens[index].normalized in {",", connector}
            for index in range(action.token_end, authorization.token_start)
        )
        if not boundary_present:
            continue

        intervening_finite = any(
            predicate.form.person is not None
            and predicate.token_start >= action.token_end
            and predicate.token_end <= authorization.token_start
            and not (
                predicate.token_start == action.token_start
                and predicate.token_end == action.token_end
            )
            for predicate in analysis.predicates
            if _in_clause(predicate.token_start, predicate.token_end, clause)
        )
        if intervening_finite:
            continue

        preceding_actors = tuple(
            span for span in actor_spans if span[0] < action.token_start
        )
        if not preceding_actors:
            continue
        actor_span = min(
            preceding_actors,
            key=lambda span: action.token_start - span[0],
        )

        activity_span = _nearest_activity_span(analysis, clause, action)
        if (
            action.form.family is PredicateFamily.PERFORM
            and activity_span is not None
            and activity_span[0] < authorization.token_start
        ):
            return clause, actor_span, activity_span, action

        if (
            action.form.family is PredicateFamily.USE_ACCESS
            and customer_instruments
        ):
            return clause, actor_span, activity_span, action

    return None


def _permission_denial_backlink(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    authorization: PredicateMatch,
) -> tuple[ClauseSegment, tuple[int, int], tuple[int, int] | None, PredicateMatch] | None:
    same_clause = _same_clause_permission_denial_backlink(
        analysis,
        clause,
        language,
        authorization,
    )
    if same_clause is not None:
        return same_clause

    if clause.index <= 0:
        return None

    prior = analysis.clauses[clause.index - 1]
    actor_spans = _known_actor_spans(analysis, prior, language)
    if not actor_spans:
        return None

    prior_activity = _nearest_activity_span(analysis, prior, None)
    prior_instruments = tuple(
        (index, index + 1)
        for index in range(prior.token_start, prior.token_end)
        if LexicalTag.INSTRUMENT in analysis.tags[index]
    )
    prior_self_possession = _role_spans(
        analysis,
        prior,
        frozenset({SelfRole.POSSESSOR}),
    )

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, prior):
            continue
        if not _source_accent_selects_predicate(analysis, predicate):
            continue
        if not _third_party_action_allowed(predicate):
            continue
        if predicate.form.family is PredicateFamily.PERFORM and prior_activity is not None:
            return prior, actor_spans[0], prior_activity, predicate
        if predicate.form.family is PredicateFamily.USE_ACCESS:
            if prior_instruments and prior_self_possession:
                return prior, actor_spans[0], prior_activity, predicate
    return None


def _authorization_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    auth_nouns = _auth_noun_spans(analysis, clause)

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family not in {
            PredicateFamily.AUTHORIZE,
            PredicateFamily.GIVE_PERMISSION,
        }:
            continue
        if not _denial_reference_allowed(
            analysis,
            clause,
            predicate,
            language,
        ):
            continue
        if not _predicate_has_denial(analysis, clause, predicate, language):
            continue

        self_evidence = _bound_self_evidence(
            analysis,
            clause,
            predicate,
            frozenset({SelfRole.SUBJECT, SelfRole.AGENT}),
        )
        if self_evidence is None:
            continue

        if predicate.form.family is PredicateFamily.GIVE_PERMISSION:
            nearby_auth_nouns = tuple(
                span
                for span in auth_nouns
                if 0 <= span[0] - predicate.token_end <= 4
                or 0 <= predicate.token_start - span[1] <= 2
            )
            if not nearby_auth_nouns:
                continue
        else:
            nearby_auth_nouns = ()

        activity_span = _nearest_activity_span(analysis, clause, predicate)
        denial_index = _bound_denial_index(
            analysis,
            clause,
            predicate,
            language,
        )
        if denial_index is None:
            continue
        denial_span = (denial_index, denial_index + 1)
        nearest_self = (
            self_evidence.token_start,
            self_evidence.token_end,
        )

        evidence: list[tuple[int, int]] = [denial_span, nearest_self]
        if nearby_auth_nouns:
            evidence.append(nearby_auth_nouns[0])

        rule = "P4"
        activity_ref = (
            "explicit_activity"
            if activity_span is not None
            else "topic_transaction"
        )

        if (
            predicate.form.family is PredicateFamily.AUTHORIZE
            and activity_span is None
        ):
            d2_link = _d2_anaphoric_prior_activity(
                analysis,
                clause,
                predicate,
                language,
            )
            if d2_link is not None:
                anaphor_span, activity_span, activity_ref = d2_link
                evidence.extend((anaphor_span, activity_span))
                rule = "P4-R3-activity-anaphora"

        if (
            predicate.form.family is PredicateFamily.GIVE_PERMISSION
            and activity_span is None
        ):
            backlink = _permission_denial_backlink(
                analysis,
                clause,
                language,
                predicate,
            )
            if backlink is None:
                continue
            _, actor_span, prior_activity, prior_predicate = backlink
            evidence.extend(
                [
                    actor_span,
                    (prior_predicate.token_start, prior_predicate.token_end),
                ]
            )
            if prior_activity is not None:
                activity_span = prior_activity
                activity_ref = "linked_prior_activity"
            else:
                activity_ref = "linked_instrument_use"
            rule = "P4-R3-permission-backlink"

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.AUTHORIZATION_DENIAL,
                rule=rule,
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=activity_ref,
            )
        )

    return output


def _possessive_authorization_absence(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    words = [token.normalized for token in analysis.tokens]
    introducer = "sin" if language == "es" else "sem"
    activity_span = _nearest_activity_span(analysis, clause, None)
    if activity_span is None:
        return []

    possessor_spans = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    auth_nouns = _auth_noun_spans(analysis, clause)
    output: list[PositiveProposition] = []

    articles = (
        {"el", "la", "los", "las"}
        if language == "es"
        else {"o", "a", "os", "as"}
    )

    for possessor_span in possessor_spans:
        possessor_index = possessor_span[0]
        if possessor_index <= clause.token_start:
            continue

        introducer_index: int | None = None
        if words[possessor_index - 1] == introducer:
            introducer_index = possessor_index - 1
        elif (
            possessor_index - 2 >= clause.token_start
            and words[possessor_index - 1] in articles
            and words[possessor_index - 2] == introducer
        ):
            introducer_index = possessor_index - 2
        if introducer_index is None:
            continue

        auth_span = next(
            (
                span
                for span in auth_nouns
                if span[0] == possessor_span[1]
            ),
            None,
        )
        if auth_span is None:
            continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.AUTHORIZATION_DENIAL,
                rule="P4",
                language=language,
                evidence_spans=(
                    activity_span,
                    (introducer_index, introducer_index + 1),
                    possessor_span,
                    auth_span,
                ),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output


def _unauthorized_participle_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    activity_span = _nearest_activity_span(analysis, clause, None)
    if activity_span is None:
        return []

    negatives = _negative_indices(analysis, clause, language)
    output: list[PositiveProposition] = []
    for index in range(clause.token_start, clause.token_end):
        if analysis.tokens[index].normalized not in _AUTH_PARTICIPLES[language]:
            continue
        neg_index = next(
            (
                candidate
                for candidate in reversed(negatives)
                if candidate < index and index - candidate <= 2
            ),
            None,
        )
        if neg_index is None:
            continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.AUTHORIZATION_DENIAL,
                rule="P4",
                language=language,
                evidence_spans=(
                    activity_span,
                    (neg_index, neg_index + 1),
                    (index, index + 1),
                ),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output




_ES_PERMISSION_ABSENCE_PHRASES = (
    ("sin", "preguntarme"),
    ("sin", "avisarme"),
    ("a", "escondidas"),
)
_PT_PERMISSION_ABSENCE_PHRASES = (
    ("sem", "me", "perguntar"),
    ("sem", "me", "avisar"),
    ("escondido",),
    ("escondida",),
)


def _customer_instrument_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    instruments = tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.INSTRUMENT in analysis.tags[index]
    )

    linked: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for instrument in instruments:
        possessor = next(
            (
                span
                for span in possessors
                if min(
                    abs(span[0] - instrument[0]),
                    abs(span[1] - instrument[0]),
                )
                <= 2
            ),
            None,
        )
        if possessor is not None:
            linked.append((instrument, possessor))
    return tuple(linked)


_ES_UNKNOWN_ACTOR_WORDS = frozenset({"alguien", "tercero", "tercera"})
_PT_UNKNOWN_ACTOR_WORDS = frozenset({"alguem", "terceiro", "terceira"})


def _unknown_actor_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    actor_words = (
        _ES_UNKNOWN_ACTOR_WORDS
        if language == "es"
        else _PT_UNKNOWN_ACTOR_WORDS
    )
    person_phrase = ("otra", "persona") if language == "es" else ("outra", "pessoa")
    spans: list[tuple[int, int]] = []

    for index in range(clause.token_start, clause.token_end):
        if words[index] in actor_words:
            spans.append((index, index + 1))
        if (
            index + 1 < clause.token_end
            and (words[index], words[index + 1]) == person_phrase
        ):
            spans.append((index, index + 2))

    return tuple(spans)


def _permission_absence_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    phrases = (
        _ES_PERMISSION_ABSENCE_PHRASES
        if language == "es"
        else _PT_PERMISSION_ABSENCE_PHRASES
    )
    spans: list[tuple[int, int]] = []

    introducer = "sin" if language == "es" else "sem"
    auth_nouns = _auth_noun_spans(analysis, clause)
    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    for possessor in possessors:
        possessor_index = possessor[0]
        if possessor_index <= clause.token_start:
            continue
        if words[possessor_index - 1] != introducer:
            continue
        auth_span = next(
            (span for span in auth_nouns if span[0] == possessor[1]),
            None,
        )
        if auth_span is not None:
            spans.append((possessor_index - 1, auth_span[1]))

    for auth_span in auth_nouns:
        if auth_span[0] <= clause.token_start:
            continue
        if words[auth_span[0] - 1] == introducer:
            spans.append((auth_span[0] - 1, auth_span[1]))

    for phrase in phrases:
        width = len(phrase)
        for index in range(clause.token_start, clause.token_end - width + 1):
            if tuple(words[index : index + width]) == phrase:
                spans.append((index, index + width))

    negative_indices = set(_negative_indices(analysis, clause, language))
    filtered = tuple(
        span
        for span in dict.fromkeys(spans)
        if span[0] <= clause.token_start
        or (span[0] - 1) not in negative_indices
    )
    return filtered


def _permission_absence_for_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    permission_spans: tuple[tuple[int, int], ...],
) -> tuple[int, int] | None:
    local_spans = tuple(
        span
        for span in permission_spans
        if min(
            abs(span[0] - predicate.token_end),
            abs(predicate.token_start - span[1]),
        )
        <= 6
    )
    ordered = sorted(
        local_spans,
        key=lambda span: min(
            abs(span[0] - predicate.token_end),
            abs(predicate.token_start - span[1]),
        ),
    )

    for span in ordered:
        left = min(span[0], predicate.token_start)
        right = max(span[1], predicate.token_end)
        intervening_action = any(
            candidate.token_start > left
            and candidate.token_start < right
            and not (
                candidate.token_start == predicate.token_start
                and candidate.token_end == predicate.token_end
            )
            and candidate.form.family in {
                PredicateFamily.PERFORM,
                PredicateFamily.USE_ACCESS,
            }
            for candidate in analysis.predicates
            if _in_clause(candidate.token_start, candidate.token_end, clause)
        )
        if not intervening_action:
            return span

    return None


def _third_party_action_allowed(predicate: PredicateMatch) -> bool:
    """Return whether a finite action can represent a non-customer actor."""

    return predicate.form.person != 1


def _perform_customer_instrument_complement(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    customer_instruments: tuple[
        tuple[tuple[int, int], tuple[int, int]], ...
    ],
    language: str,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Bind PERFORM only to a bounded customer-instrument complement."""

    if predicate.form.family is not PredicateFamily.PERFORM:
        return None

    words = [token.normalized for token in analysis.tokens]
    prepositions = (
        {"con", "en", "de"}
        if language == "es"
        else {"com", "no", "na", "nos", "nas", "de", "do", "da", "dos", "das"}
    )

    candidates: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for instrument_span, possessor_span in customer_instruments:
        left = min(instrument_span[0], possessor_span[0])
        if left <= predicate.token_end:
            continue
        if left - predicate.token_end > 7:
            continue

        prep_index = left - 1
        if prep_index < clause.token_start:
            continue
        if words[prep_index] not in prepositions:
            continue

        intervening_predicate = any(
            candidate.token_start >= predicate.token_end
            and candidate.token_start < prep_index
            and not (
                candidate.token_start == predicate.token_start
                and candidate.token_end == predicate.token_end
            )
            for candidate in analysis.predicates
            if _in_clause(candidate.token_start, candidate.token_end, clause)
        )
        if intervening_predicate:
            continue

        candidates.append((instrument_span, possessor_span))

    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: item[0][0] - predicate.token_end,
    )


def _p5_known_actor_embedded_under_prior_unknown(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    known_actor: tuple[int, int],
    unknown_actors: tuple[tuple[int, int], ...],
) -> bool:
    """Return whether a known actor is only a modifier of an earlier unknown actor."""

    prior_unknowns = tuple(
        span
        for span in unknown_actors
        if span[1] <= known_actor[0]
    )
    if not prior_unknowns:
        return False

    prior_unknown = max(prior_unknowns, key=lambda span: span[1])
    words = [token.normalized for token in analysis.tokens]

    introducers = (
        {"de", "del", "a", "al"}
        if language == "es"
        else {"de", "do", "da", "dos", "das", "a", "ao", "aos"}
    )
    bridge_words = (
        {"mi", "mis"}
        if language == "es"
        else {"meu", "minha", "meus", "minhas"}
    )
    relative_bridge_words = (
        {"me", "te", "se", "lo", "la", "los", "las", "le", "les"}
        if language == "es"
        else {"me", "te", "se", "o", "a", "os", "as", "lhe", "lhes"}
    ) | introducers | bridge_words
    relative_fallback_nonverbs = (
        {
            "hoy", "ayer", "anteayer", "antes", "ya", "tambien",
            "luego", "despues", "solo", "fue", "era", "es",
        }
        if language == "es"
        else {
            "hoje", "ontem", "anteontem", "antes", "ja", "tambem",
            "logo", "depois", "so", "foi", "era", "e",
        }
    )

    if (
        prior_unknown[1] < clause.token_end
        and words[prior_unknown[1]] == "que"
        and prior_unknown[1] < known_actor[0]
    ):
        relative_start = prior_unknown[1] + 1
        finite_spans = tuple(
            sorted(
                {
                    (predicate.token_start, predicate.token_end)
                    for predicate in analysis.predicates
                    if _in_clause(predicate.token_start, predicate.token_end, clause)
                    and predicate.form.person is not None
                    and predicate.token_start >= relative_start
                    and predicate.token_end <= known_actor[0]
                }
            )
        )
        if len(finite_spans) == 1:
            predicate_span = finite_spans[0]
            bridge_indexes = tuple(
                index
                for index in range(relative_start, known_actor[0])
                if not (
                    predicate_span[0] <= index < predicate_span[1]
                )
            )
            if all(
                words[index] in relative_bridge_words
                for index in bridge_indexes
            ):
                return True

        if not finite_spans:
            relative_material = tuple(
                words[index]
                for index in range(relative_start, known_actor[0])
            )
            if (
                1 <= len(relative_material) <= 3
                and "que" not in relative_material
                and relative_material[0] not in relative_bridge_words
                and relative_material[0] not in relative_fallback_nonverbs
                and all(
                    word in relative_bridge_words
                    for word in relative_material[1:]
                )
            ):
                return True


    left = known_actor[0] - 1
    while left >= max(prior_unknown[1], known_actor[0] - 3):
        word = words[left]
        if word in introducers:
            return all(
                words[index] in bridge_words
                for index in range(left + 1, known_actor[0])
            )
        if word not in bridge_words:
            break
        left -= 1

    return False


def _third_party_unauthorized_use(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    customer_instruments = _customer_instrument_spans(analysis, clause)
    if not customer_instruments:
        return []

    unknown_actors = _unknown_actor_spans(analysis, clause, language)
    known_actors = _known_actor_spans(analysis, clause, language)
    absence_spans = _permission_absence_spans(analysis, clause, language)
    activity_span = _nearest_activity_span(analysis, clause, None)
    output: list[PositiveProposition] = []

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family not in {
            PredicateFamily.USE_ACCESS,
            PredicateFamily.PERFORM,
        }:
            continue
        if not _source_accent_selects_predicate(analysis, predicate):
            continue
        if not _third_party_action_allowed(predicate):
            continue
        if _predicate_has_denial(analysis, clause, predicate, language):
            continue

        if predicate.form.family is PredicateFamily.PERFORM:
            linked_instrument = _perform_customer_instrument_complement(
                analysis,
                clause,
                predicate,
                customer_instruments,
                language,
            )
            if linked_instrument is None:
                continue
        else:
            linked_instrument = None

        actor_span: tuple[int, int] | None = None
        permission_span: tuple[int, int] | None = None
        actor_kind: str | None = None

        actor_candidates = [
            ("unknown", span)
            for span in unknown_actors
            if span[0] < predicate.token_start
        ] + [
            ("known", span)
            for span in known_actors
            if (
                span[0] < predicate.token_start
                and not _p5_known_actor_embedded_under_prior_unknown(
                    analysis,
                    clause,
                    language,
                    span,
                    unknown_actors,
                )
            )
        ]

        if actor_candidates:
            nearest_kind, nearest_span = max(
                actor_candidates,
                key=lambda item: item[1][0],
            )
            if nearest_kind == "unknown":
                actor_span = nearest_span
                actor_kind = "unknown"
            else:
                local_permission = _permission_absence_for_predicate(
                    analysis,
                    clause,
                    predicate,
                    absence_spans,
                )
                if local_permission is not None:
                    actor_span = nearest_span
                    permission_span = local_permission
                    actor_kind = "known"

        if actor_span is None or actor_kind is None:
            continue

        if linked_instrument is not None:
            instrument_span, possessor_span = linked_instrument
        else:
            instrument_span, possessor_span = min(
                customer_instruments,
                key=lambda item: min(
                    abs(item[0][0] - predicate.token_start),
                    abs(item[0][0] - predicate.token_end),
                ),
            )

        evidence: list[tuple[int, int]] = [
            actor_span,
            instrument_span,
            possessor_span,
        ]
        if permission_span is not None:
            evidence.append(permission_span)

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
                rule="P5",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else (
                        f"{actor_kind}_actor_instrument_perform"
                        if predicate.form.family is PredicateFamily.PERFORM
                        else f"{actor_kind}_actor_instrument_use"
                    )
                ),
            )
        )

    return output




_ES_FRAUD_NOUNS = frozenset({"fraude", "golpe"})
_PT_FRAUD_NOUNS = frozenset({"fraude", "golpe"})
_ES_FRAUD_ADJECTIVES = frozenset(
    {"fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"}
)
_PT_FRAUD_ADJECTIVES = frozenset(
    {"fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"}
)

_ES_ACTIVITY_FEMININE = frozenset(
    {"compra", "compras", "operacion", "operaciones", "transaccion", "transacciones",
     "transferencia", "transferencias"}
)
_PT_ACTIVITY_FEMININE = frozenset(
    {"cobranca", "cobrancas", "compra", "compras", "operacao", "operacoes",
     "transacao", "transacoes", "transferencia", "transferencias",
     "movimentacao", "movimentacoes", "ted"}
)

_ES_SPECIFIC_DETERMINERS = frozenset(
    {"este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
     "aquel", "aquella", "aquellos", "aquellas", "el", "la", "los", "las"}
)
_PT_SPECIFIC_DETERMINERS = frozenset(
    {"este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
     "aquele", "aquela", "aqueles", "aquelas", "o", "a", "os", "as"}
)

_ES_THIRD_POSSESSIVES = frozenset({"su", "sus"})
_PT_THIRD_POSSESSIVES = frozenset({"seu", "sua", "seus", "suas"})

_ES_EXPERIENCER_VERBS = frozenset({"tengo", "veo", "recibo", "recibi"})
_PT_EXPERIENCER_VERBS = frozenset({"tenho", "vejo", "recebo", "recebi"})
_ES_DATIVE_EXPERIENCER_VERBS = frozenset({"aparece", "aparecio", "salio"})
_PT_DATIVE_EXPERIENCER_VERBS = frozenset({"aparece", "apareceu", "saiu"})
_ES_ACTIVITY_EXISTENTIALS = frozenset({"hay"})
_PT_ACTIVITY_EXISTENTIALS = frozenset({"ha", "existe"})
_ES_INSTRUMENT_LOCATIVES = frozenset({"en"})
_PT_INSTRUMENT_LOCATIVES = frozenset({"em", "no", "na", "nos", "nas"})

_ES_PREPOSITIONAL_ACTIVITY = frozenset({"de", "del", "sobre", "para", "por", "con", "en"})
_PT_PREPOSITIONAL_ACTIVITY = frozenset({"de", "do", "da", "sobre", "para", "por", "com", "em", "no", "na"})

_ES_NON_ACTIVITY_FRAUD_HEADS = frozenset(
    {"correo", "email", "mensaje", "sms", "enlace", "link", "sitio", "pagina",
     "llamada", "comercio", "establecimiento", "descriptor", "nombre"}
)
_PT_NON_ACTIVITY_FRAUD_HEADS = frozenset(
    {"email", "mensagem", "sms", "link", "site", "pagina", "ligacao",
     "comercio", "estabelecimento", "descritor", "nome"}
)


def _activity_number(word: str) -> str:
    return "plural" if word.endswith("s") and word not in {"pix"} else "singular"


def _activity_gender(word: str, language: str) -> str:
    feminine = _ES_ACTIVITY_FEMININE if language == "es" else _PT_ACTIVITY_FEMININE
    return "feminine" if word in feminine else "masculine"


def _fraud_adjective_agrees(activity_word: str, fraud_word: str, language: str) -> bool:
    number = _activity_number(activity_word)
    gender = _activity_gender(activity_word, language)

    expected = {
        ("masculine", "singular"): "fraudulento",
        ("feminine", "singular"): "fraudulenta",
        ("masculine", "plural"): "fraudulentos",
        ("feminine", "plural"): "fraudulentas",
    }[(gender, number)]
    return fraud_word == expected


def _third_person_relational_phrase_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    relational_nouns = (
        _ES_RELATIONAL_NOUNS
        if language == "es"
        else _PT_RELATIONAL_NOUNS
    )
    if language == "es":
        prepositions = {"de", "del", "a", "para"}
        possessives = {"mi", "mis", "su", "sus"}
    else:
        prepositions = {"de", "do", "da", "dos", "das", "a", "ao", "aos", "para", "pra"}
        possessives = {"meu", "minha", "meus", "minhas", "seu", "sua", "seus", "suas"}

    spans: list[tuple[int, int]] = []
    for index in range(clause.token_start, clause.token_end - 2):
        if words[index] not in prepositions:
            continue
        if words[index + 1] not in possessives:
            continue
        if (
            language == "es"
            and words[index + 1] == "mi"
            and analysis.tokens[index + 1].had_acute
        ):
            continue
        if words[index + 2] not in relational_nouns:
            continue
        spans.append((index, index + 3))
    return tuple(spans)


def _explicit_third_person_activity_possession(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    words = [token.normalized for token in analysis.tokens]
    index = activity_span[0]
    third_possessives = (
        _ES_THIRD_POSSESSIVES if language == "es" else _PT_THIRD_POSSESSIVES
    )
    if index > clause.token_start and words[index - 1] in third_possessives:
        return True

    if language == "es":
        third_patterns = {
            ("de", "ella"),
            ("de", "ellos"),
            ("de", "ellas"),
            ("de", "otra"),
        }
    else:
        third_patterns = {
            ("de", "outra"),
            ("da", "outra"),
        }

    for start in range(index + 1, min(clause.token_end - 1, index + 4)):
        if (words[start], words[start + 1]) in third_patterns:
            return True
        if language == "pt" and words[start] in {"dela", "dele", "delas", "deles"}:
            return True

    if any(
        min(abs(span[0] - index), abs(span[1] - index)) <= 8
        for span in _third_person_relational_phrase_spans(
            analysis,
            clause,
            language,
        )
    ):
        return True

    return False


def _customer_anchored_activity(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    if _explicit_third_person_activity_possession(
        analysis, clause, activity_span, language
    ):
        return False

    index = activity_span[0]
    token = analysis.tokens[index]
    words = [item.normalized for item in analysis.tokens]
    if token.is_txid:
        return True

    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    if any(
        span[1] <= index and index - span[1] <= 1
        for span in possessors
    ):
        return True

    determiners = (
        _ES_SPECIFIC_DETERMINERS
        if language == "es"
        else _PT_SPECIFIC_DETERMINERS
    )
    if index > clause.token_start and words[index - 1] in determiners:
        return True

    modifier_cursor = index - 1
    while (
        modifier_cursor >= clause.token_start
        and _is_closed_prenominal_modifier(
            words[modifier_cursor],
            language,
        )
    ):
        modifier_cursor -= 1
    if (
        modifier_cursor >= clause.token_start
        and words[modifier_cursor] in determiners
    ):
        return True

    if index > clause.token_start:
        previous = analysis.tokens[index - 1]
        if previous.normalized.isdigit() or previous.is_txid:
            return True

    experiencer_verbs = (
        _ES_EXPERIENCER_VERBS if language == "es" else _PT_EXPERIENCER_VERBS
    )
    for verb_index in range(max(clause.token_start, index - 5), index):
        if words[verb_index] in experiencer_verbs:
            return True

    dative_verbs = (
        _ES_DATIVE_EXPERIENCER_VERBS
        if language == "es"
        else _PT_DATIVE_EXPERIENCER_VERBS
    )
    dative_spans = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.DATIVE}),
    )
    if dative_spans:
        for verb_index in range(max(clause.token_start, index - 5), index):
            if words[verb_index] in dative_verbs:
                return True

    existentials = (
        _ES_ACTIVITY_EXISTENTIALS
        if language == "es"
        else _PT_ACTIVITY_EXISTENTIALS
    )
    if any(
        words[frame_index] in existentials
        for frame_index in range(max(clause.token_start, index - 5), index)
    ):
        return True

    locatives = (
        _ES_INSTRUMENT_LOCATIVES
        if language == "es"
        else _PT_INSTRUMENT_LOCATIVES
    )
    for instrument_span, possessor_span in _customer_instrument_spans(
        analysis,
        clause,
    ):
        left = min(instrument_span[0], possessor_span[0])
        if left <= clause.token_start:
            continue
        if words[left - 1] in locatives:
            return True

    return False




_ES_EXCEEDED_AMOUNT_MARKERS = (
    ("mas", "de", "lo", "que"),
)
_PT_EXCEEDED_AMOUNT_MARKERS = (
    ("mais", "do", "que"),
    ("alem", "do", "que"),
)
_ES_EXCEEDED_PARTICIPIAL_PREFIXES = (
    ("mas", "de", "lo"),
)
_PT_EXCEEDED_PARTICIPIAL_PREFIXES = (
    ("mais", "do", "que", "o"),
    ("alem", "do"),
)
_ES_GRANT_DATIVE_WORDS = frozenset({"le", "les"})
_PT_GRANT_DATIVE_WORDS = frozenset({"lhe", "lhes"})

# These forms are deliberately local to the limited-purpose-grant rule. They are
# not added to GIVE_PERMISSION or AUTHORIZE, so they cannot create ordinary P4.
_ES_LIMITED_GRANT_FIRST_PERSON_PAST = frozenset({"preste", "pase", "deje"})
_PT_LIMITED_GRANT_FIRST_PERSON_PAST = frozenset({"emprestei", "deixei"})


def _phrase_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    phrases: tuple[tuple[str, ...], ...],
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    spans: list[tuple[int, int]] = []
    for phrase in phrases:
        width = len(phrase)
        for index in range(clause.token_start, clause.token_end - width + 1):
            if tuple(words[index : index + width]) == phrase:
                spans.append((index, index + width))
    return tuple(spans)


def _nearest_known_actor_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    predicate: PredicateMatch,
) -> tuple[int, int] | None:
    actors = tuple(
        span
        for span in _known_actor_spans(analysis, clause, language)
        if span[0] < predicate.token_start
    )
    if not actors:
        return None
    return min(
        actors,
        key=lambda span: predicate.token_start - span[0],
    )


def _first_person_authorization_after_marker(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    marker_span: tuple[int, int],
) -> PredicateMatch | None:
    candidates = tuple(
        predicate
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, clause)
        and predicate.form.family is PredicateFamily.AUTHORIZE
        and predicate.form.person == 1
        and predicate.token_start >= marker_span[1]
        and predicate.token_start - marker_span[1] <= 5
        and _source_accent_selects_predicate(analysis, predicate)
    )
    if not candidates:
        return None
    return min(candidates, key=lambda predicate: predicate.token_start)


def _is_exceeded_authorization_participle(
    word: str,
    language: str,
) -> bool:
    if any(
        form.family is PredicateFamily.AUTHORIZE
        and form.tense_aspect == "participle"
        for form in PARADIGMS[language].get(word, ())
    ):
        return True

    # F-20 audit evidence uses the idiomatic PT ceiling "além do combinado".
    return language == "pt" and word == "combinado"


def _participial_exceeded_amount_candidates(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
    prefixes = (
        _ES_EXCEEDED_PARTICIPIAL_PREFIXES
        if language == "es"
        else _PT_EXCEEDED_PARTICIPIAL_PREFIXES
    )
    output: list[tuple[tuple[int, int], tuple[int, int]]] = []

    for marker_span in _phrase_spans(analysis, clause, prefixes):
        participle_index = marker_span[1]
        if participle_index >= clause.token_end:
            continue
        if not _is_exceeded_authorization_participle(
            analysis.tokens[participle_index].normalized,
            language,
        ):
            continue
        output.append(
            (marker_span, (participle_index, participle_index + 1))
        )

    return tuple(output)


def _exceeded_amount_authorization(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    markers = (
        _ES_EXCEEDED_AMOUNT_MARKERS
        if language == "es"
        else _PT_EXCEEDED_AMOUNT_MARKERS
    )
    candidates: list[
        tuple[tuple[int, int], tuple[int, int]]
    ] = []

    for marker_span in _phrase_spans(analysis, clause, markers):
        authorization = _first_person_authorization_after_marker(
            analysis,
            clause,
            marker_span,
        )
        if authorization is None:
            continue
        candidates.append(
            (
                marker_span,
                (authorization.token_start, authorization.token_end),
            )
        )

    candidates.extend(
        _participial_exceeded_amount_candidates(
            analysis,
            clause,
            language,
        )
    )
    if not candidates:
        return []

    output: list[PositiveProposition] = []
    for marker_span, authorization_span in candidates:
        actions = tuple(
            predicate
            for predicate in analysis.predicates
            if _in_clause(predicate.token_start, predicate.token_end, clause)
            and predicate.form.family in {
                PredicateFamily.PERFORM,
                PredicateFamily.USE_ACCESS,
            }
            and predicate.token_end <= marker_span[0]
            and marker_span[0] - predicate.token_end <= 6
            and _source_accent_selects_predicate(analysis, predicate)
        )
        if not actions:
            continue
        action = max(actions, key=lambda predicate: predicate.token_start)
        if not _third_party_action_allowed(action):
            continue
        if _predicate_has_denial(analysis, clause, action, language):
            continue

        actor_span = _nearest_known_actor_before_predicate(
            analysis,
            clause,
            language,
            action,
        )
        if actor_span is None:
            continue

        activity_span = _nearest_activity_span(analysis, clause, action)
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
                rule="P5-exceeded-authorization-amount",
                language=language,
                evidence_spans=(
                    actor_span,
                    marker_span,
                    (action.token_start, action.token_end),
                    authorization_span,
                ),
                activity_span=activity_span,
                predicate=action,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "known_actor_exceeded_authorized_amount"
                ),
            )
        )
    return output


def _limited_grant_surface_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    """Return closed first-person past grant forms used only by A4 purpose scope."""

    forms = (
        _ES_LIMITED_GRANT_FIRST_PERSON_PAST
        if language == "es"
        else _PT_LIMITED_GRANT_FIRST_PERSON_PAST
    )
    spans: list[tuple[int, int]] = []
    for index in range(clause.token_start, clause.token_end):
        token = analysis.tokens[index]
        if token.normalized not in forms:
            continue
        if language == "es" and not token.had_acute:
            continue
        spans.append((index, index + 1))
    return tuple(spans)


def _limited_grant_candidate_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = list(
        _limited_grant_surface_spans(analysis, clause, language)
    )
    spans.extend(
        (predicate.token_start, predicate.token_end)
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, clause)
        and predicate.form.family is PredicateFamily.GIVE_PERMISSION
        and predicate.form.person == 1
        and _source_accent_selects_predicate(analysis, predicate)
    )
    return tuple(sorted(dict.fromkeys(spans)))


def _limited_grant_recipient(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    action: PredicateMatch,
) -> tuple[int, int] | None:
    words = [token.normalized for token in analysis.tokens]
    dative_words = (
        _ES_GRANT_DATIVE_WORDS
        if language == "es"
        else _PT_GRANT_DATIVE_WORDS
    )

    grant_clauses = [clause]
    if clause.index > 0:
        grant_clauses.append(analysis.clauses[clause.index - 1])

    for grant_clause in grant_clauses:
        same_clause = grant_clause.index == clause.index
        scope_end = action.token_start if same_clause else grant_clause.token_end
        grant_spans = tuple(
            span
            for span in _limited_grant_candidate_spans(
                analysis,
                grant_clause,
                language,
            )
            if span[1] < scope_end
            and (
                (same_clause and action.token_start - span[1] <= 14)
                or (
                    not same_clause
                    and grant_clause.token_end - span[1] <= 18
                )
            )
        )

        for grant_span in reversed(grant_spans):
            instrument_span = next(
                (
                    (index, index + 1)
                    for index in range(grant_span[1], scope_end)
                    if LexicalTag.INSTRUMENT in analysis.tags[index]
                ),
                None,
            )
            if instrument_span is None:
                continue

            purpose_index = next(
                (
                    index
                    for index in range(instrument_span[1], scope_end)
                    if words[index] == "para"
                ),
                None,
            )
            if purpose_index is None:
                continue

            dative_span = next(
                (
                    (index, index + 1)
                    for index in range(
                        max(grant_clause.token_start, grant_span[0] - 2),
                        min(scope_end, grant_span[1] + 3),
                    )
                    if words[index] in dative_words
                ),
                None,
            )
            if dative_span is not None:
                return dative_span

            known_actor = next(
                (
                    span
                    for span in _known_actor_spans(
                        analysis,
                        grant_clause,
                        language,
                    )
                    if grant_span[0] <= span[0] < scope_end
                ),
                None,
            )
            if known_actor is not None:
                return known_actor

    return None

def _exceeded_purpose_authorization(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    permission_spans = _permission_absence_spans(
        analysis,
        clause,
        language,
    )
    if not permission_spans:
        return []

    output: list[PositiveProposition] = []
    for action in analysis.predicates:
        if not _in_clause(action.token_start, action.token_end, clause):
            continue
        if action.form.family is not PredicateFamily.PERFORM:
            continue
        if not _third_party_action_allowed(action):
            continue
        if not _source_accent_selects_predicate(analysis, action):
            continue
        if _predicate_has_denial(analysis, clause, action, language):
            continue

        later_permission = tuple(
            span
            for span in permission_spans
            if span[0] >= action.token_end
            and span[0] - action.token_end <= 6
        )
        if not later_permission:
            continue
        permission_span = min(later_permission, key=lambda span: span[0])

        grant_recipient = _limited_grant_recipient(
            analysis,
            clause,
            language,
            action,
        )
        if grant_recipient is None:
            continue

        actor_span = _nearest_known_actor_before_predicate(
            analysis,
            clause,
            language,
            action,
        )
        if actor_span is None:
            actor_span = grant_recipient

        activity_span = _nearest_activity_span(analysis, clause, action)
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
                rule="P5-exceeded-authorization-purpose",
                language=language,
                evidence_spans=(
                    actor_span,
                    permission_span,
                    (action.token_start, action.token_end),
                ),
                activity_span=activity_span,
                predicate=action,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "known_actor_exceeded_authorized_purpose"
                ),
            )
        )
    return output


def _exceeded_authorization_propositions(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    return [
        *_exceeded_amount_authorization(analysis, clause, language),
        *_exceeded_purpose_authorization(analysis, clause, language),
    ]


def _self_predicate_governs_activity(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    """Bound SELF PERFORM/AUTHORIZE evidence to one explicit activity argument."""

    words = [token.normalized for token in analysis.tokens]
    activity_index = activity_span[0]
    barriers = {
        ",", ";", "?", "¿", "!", "¡", ":",
        *(_ES_CONTRAST if language == "es" else _PT_CONTRAST),
    }
    coordinator = "y" if language == "es" else "e"

    # Direct post-verbal activity object: predicate + bounded NP.
    if activity_index >= predicate.token_end:
        between = range(predicate.token_end, activity_index)
        if any(words[index] in barriers | {coordinator} for index in between):
            return False

        object_start = activity_index
        while (
            object_start > predicate.token_end
            and _is_closed_prenominal_modifier(
                words[object_start - 1],
                language,
            )
        ):
            object_start -= 1

        determiners = (
            _ES_NOMINAL_DETERMINERS
            if language == "es"
            else _PT_NOMINAL_DETERMINERS
        )
        if (
            object_start > predicate.token_end
            and words[object_start - 1] in determiners
        ):
            object_start -= 1

        return object_start == predicate.token_end

    if activity_span[1] > predicate.token_start:
        return False

    between_start = activity_span[1]
    between_end = predicate.token_start
    if any(
        words[index] in barriers | {coordinator}
        for index in range(between_start, between_end)
    ):
        return False

    intervening_predicate = any(
        other.token_start >= between_start
        and other.token_start < predicate.token_start
        and not (
            other.token_start == predicate.token_start
            and other.token_end == predicate.token_end
        )
        for other in analysis.predicates
        if _in_clause(other.token_start, other.token_end, clause)
    )
    if intervening_predicate:
        return False

    clitics = (
        {"lo", "la", "los", "las"}
        if language == "es"
        else {"o", "a", "os", "as"}
    )
    subject_words = (
        {"yo", "nosotros", "nosotras"}
        if language == "es"
        else {"eu", "nos"}
    )
    emphatics = (
        {"mismo", "misma", "mismos", "mismas"}
        if language == "es"
        else {"mesmo", "mesma", "mesmos", "mesmas"}
    )

    # Relative-clause head: activity NP + que + bounded SELF/clitic material + predicate.
    relative_index = activity_span[1]
    if relative_index < predicate.token_start:
        activity_word = words[activity_index]
        fraud_adjectives = (
            _ES_FRAUD_ADJECTIVES
            if language == "es"
            else _PT_FRAUD_ADJECTIVES
        )
        if (
            words[relative_index] in fraud_adjectives
            and _fraud_adjective_agrees(
                activity_word,
                words[relative_index],
                language,
            )
        ):
            relative_index += 1
        elif analysis.tokens[relative_index].is_txid:
            relative_index += 1

        if (
            relative_index < predicate.token_start
            and words[relative_index] == "que"
        ):
            relative_material = words[
                relative_index + 1 : predicate.token_start
            ]
            if all(
                word in subject_words | emphatics | clitics
                for word in relative_material
            ):
                return True

    # Same-segment resumptive clitic: activity + [SELF/emphasis] + clitic + predicate.
    resumptive_material = words[activity_span[1] : predicate.token_start]
    if resumptive_material and resumptive_material[-1] in clitics:
        prefix = resumptive_material[:-1]
        if all(word in subject_words | emphatics for word in prefix):
            return True

    return False

def _affirmative_self_fraud_counter_evidence(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> tuple[EvidenceAtom, ...]:
    output: list[EvidenceAtom] = []

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family not in {
            PredicateFamily.PERFORM,
            PredicateFamily.AUTHORIZE,
        }:
            continue
        if predicate.form.mood != "indicative":
            continue
        if predicate.form.tense_aspect in {"future", "conditional"}:
            continue
        if not _source_accent_selects_predicate(analysis, predicate):
            continue
        if _predicate_has_denial(analysis, clause, predicate, language):
            continue

        self_evidence = _bound_self_evidence(
            analysis,
            clause,
            predicate,
            frozenset({SelfRole.SUBJECT, SelfRole.AGENT}),
        )
        if self_evidence is None:
            continue

        if not _self_predicate_governs_activity(
            analysis,
            clause,
            predicate,
            activity_span,
            language,
        ):
            continue

        output.append(
            EvidenceAtom(
                kind=(
                    EvidenceAtomKind.SELF_PERFORMED
                    if predicate.form.family is PredicateFamily.PERFORM
                    else EvidenceAtomKind.SELF_AUTHORIZED
                ),
                activity_token_span=activity_span,
                predicate_token_span=(
                    predicate.token_start,
                    predicate.token_end,
                ),
                self_token_span=(
                    self_evidence.token_start,
                    self_evidence.token_end,
                ),
            )
        )

    unique: dict[
        tuple[
            EvidenceAtomKind,
            tuple[int, int],
            tuple[int, int],
            tuple[int, int],
        ],
        EvidenceAtom,
    ] = {}
    for atom in output:
        unique[
            (
                atom.kind,
                atom.activity_token_span,
                atom.predicate_token_span,
                atom.self_token_span,
            )
        ] = atom
    return tuple(unique.values())


def _fraud_marker_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    nouns = _ES_FRAUD_NOUNS if language == "es" else _PT_FRAUD_NOUNS
    adjectives = (
        _ES_FRAUD_ADJECTIVES if language == "es" else _PT_FRAUD_ADJECTIVES
    )
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if analysis.tokens[index].normalized in nouns | adjectives
    )


def _fraud_attributive_propositions(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    adjectives = (
        _ES_FRAUD_ADJECTIVES if language == "es" else _PT_FRAUD_ADJECTIVES
    )
    output: list[PositiveProposition] = []

    for activity_span in _activity_spans(analysis, clause):
        if not _customer_anchored_activity(analysis, clause, activity_span, language):
            continue
        marker_index = activity_span[1]
        if marker_index >= clause.token_end:
            continue
        marker_word = analysis.tokens[marker_index].normalized
        if marker_word not in adjectives:
            continue
        if _span_has_bound_denial(
            analysis,
            clause,
            marker_index,
            marker_index + 1,
            language,
        ):
            continue
        activity_word = analysis.tokens[activity_span[0]].normalized
        if not _fraud_adjective_agrees(activity_word, marker_word, language):
            continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.FRAUD_CHARACTERIZATION,
                rule="P6-attributive",
                language=language,
                evidence_spans=(activity_span, (marker_index, marker_index + 1)),
                activity_span=activity_span,
                predicate=None,
                counter_evidence=_affirmative_self_fraud_counter_evidence(
                    analysis,
                    clause,
                    activity_span,
                    language,
                ),
            )
        )
    return output


_ES_P6_EMBEDDING_MARKERS = frozenset({"que", "cuando", "mientras"})
_PT_P6_EMBEDDING_MARKERS = frozenset({"que", "quando", "enquanto"})

_ES_P6_ATTACHED_ADVERBIAL_PHRASES = (
    ("cuando",),
    ("mientras",),
    ("aunque",),
    ("porque",),
    ("si",),
    ("apenas",),
    ("donde",),
    ("en", "cuanto"),
    ("tan", "pronto", "como"),
    ("despues", "de", "que"),
    ("antes", "de", "que"),
    ("desde", "que"),
    ("ya", "que"),
    ("una", "vez", "que"),
)
_PT_P6_ATTACHED_ADVERBIAL_PHRASES = (
    ("quando",),
    ("enquanto",),
    ("embora",),
    ("porque",),
    ("se",),
    ("onde",),
    ("depois", "que"),
    ("antes", "que"),
    ("assim", "que"),
    ("desde", "que"),
    ("ja", "que"),
    ("logo", "que"),
)
_ES_P6_NESTED_PP_PREPOSITIONS = _ES_PREPOSITIONAL_ACTIVITY | frozenset(
    {
        "a",
        "ante",
        "bajo",
        "contra",
        "desde",
        "durante",
        "entre",
        "hacia",
        "hasta",
        "mediante",
        "segun",
        "sin",
        "tras",
    }
)
_PT_P6_NESTED_PP_PREPOSITIONS = _PT_PREPOSITIONAL_ACTIVITY | frozenset(
    {
        "a",
        "ante",
        "ate",
        "contra",
        "desde",
        "durante",
        "entre",
        "mediante",
        "perante",
        "segundo",
        "sem",
        "sob",
        "apos",
        "ao",
        "aos",
        "do",
        "dos",
        "da",
        "das",
        "no",
        "nos",
        "na",
        "nas",
        "pelo",
        "pelos",
        "pela",
        "pelas",
        "num",
        "nuns",
        "numa",
        "numas",
    }
)
_ES_P6_HEAD_DETERMINERS = _ES_NOMINAL_DETERMINERS | frozenset(
    {
        "nuestro",
        "nuestra",
        "nuestros",
        "nuestras",
    }
)
_PT_P6_HEAD_DETERMINERS = _PT_NOMINAL_DETERMINERS | frozenset(
    {
        "nosso",
        "nossa",
        "nossos",
        "nossas",
    }
)
_PT_P6_ARTICLES = frozenset({"o", "a", "os", "as"})
_PT_P6_POSSESSIVES = frozenset(
    {
        "meu",
        "minha",
        "meus",
        "minhas",
        "seu",
        "sua",
        "seus",
        "suas",
        "nosso",
        "nossa",
        "nossos",
        "nossas",
    }
)
_PT_P6_FUSED_PREPOSITION_DETERMINERS = frozenset(
    {
        "ao",
        "aos",
        "do",
        "dos",
        "da",
        "das",
        "no",
        "nos",
        "na",
        "nas",
        "pelo",
        "pelos",
        "pela",
        "pelas",
        "num",
        "nuns",
        "numa",
        "numas",
    }
)
_ES_P6_RELATIVE_QUAL = frozenset({"cual", "cuales"})
_PT_P6_RELATIVE_QUAL = frozenset({"qual", "quais"})


def _p6_activity_heads_que_relative(
    analysis: FoundationAnalysis,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
) -> bool:
    words = [token.normalized for token in analysis.tokens]
    fraud_adjectives = (
        _ES_FRAUD_ADJECTIVES if language == "es" else _PT_FRAUD_ADJECTIVES
    )

    index = activity_span[1]
    if index >= copula_index:
        return False

    if (
        words[index] in fraud_adjectives
        and _fraud_adjective_agrees(
            words[activity_span[0]],
            words[index],
            language,
        )
    ):
        index += 1
    elif analysis.tokens[index].is_txid:
        index += 1

    return index < copula_index and words[index] == "que"


def _p6_activity_is_frame_object(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    marker_index: int,
    language: str,
) -> bool:
    """Recognize the bounded activity object of a finite predicate inside a P6 frame."""

    words = [token.normalized for token in analysis.tokens]
    object_start = activity_span[0]

    while (
        object_start > marker_index + 1
        and _is_closed_prenominal_modifier(
            words[object_start - 1],
            language,
        )
    ):
        object_start -= 1

    determiners = (
        _ES_NOMINAL_DETERMINERS
        if language == "es"
        else _PT_NOMINAL_DETERMINERS
    )
    if (
        object_start > marker_index + 1
        and words[object_start - 1] in determiners
    ):
        object_start -= 1

    return any(
        predicate.form.person is not None
        and not predicate.accent_ambiguous
        and predicate.token_start > marker_index
        and predicate.token_end == object_start
        and _in_clause(
            predicate.token_start,
            predicate.token_end,
            clause,
        )
        for predicate in analysis.predicates
    )


def _p6_distant_self_activity_is_embedded(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
) -> bool:
    """Recognize SELF-bearing activity inside a distant attached adverbial frame."""

    if not _affirmative_self_fraud_counter_evidence(
        analysis,
        clause,
        activity_span,
        language,
    ):
        return False

    words = [token.normalized for token in analysis.tokens]
    adverbial_markers = (
        {"cuando", "mientras"}
        if language == "es"
        else {"quando", "enquanto"}
    )
    coordinators = (
        {"y", "e", "pero"}
        if language == "es"
        else {"e", "mas", "porem"}
    )
    activity_spans = _activity_spans(analysis, clause)
    distant_start = activity_span[0] - 9

    for marker_index in range(
        distant_start,
        clause.token_start - 1,
        -1,
    ):
        if words[marker_index] not in adverbial_markers:
            continue

        has_relative_attachment_head = any(
            span[1] <= marker_index
            and _p6_activity_heads_que_relative(
                analysis,
                span,
                copula_index,
                language,
            )
            and not any(
                words[index] in coordinators
                and not (
                    words[index] == "e"
                    and analysis.tokens[index].had_acute
                )
                for index in range(span[1], marker_index)
            )
            for span in activity_spans
        )
        if not has_relative_attachment_head:
            continue

        finite_between = any(
            predicate.form.person is not None
            and not predicate.accent_ambiguous
            and predicate.token_start > marker_index
            and predicate.token_end <= activity_span[0]
            and _in_clause(
                predicate.token_start,
                predicate.token_end,
                clause,
            )
            for predicate in analysis.predicates
        )
        if finite_between:
            return True

    return False


def _p6_left_activity_is_embedded(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
) -> bool:
    words = [token.normalized for token in analysis.tokens]

    # Preserve the already-supported clause-initial topicalization frames so
    # they can reach the authoritative positive-license gate below P6.
    topicalizers = (
        (("respecto", "a"), ("en", "cuanto", "a"))
        if language == "es"
        else (("quanto", "a"),)
    )
    activity_spans = _activity_spans(analysis, clause)
    first_activity = activity_spans[0] if activity_spans else None
    for phrase in topicalizers:
        phrase_end = clause.token_start + len(phrase)
        if (
            tuple(words[clause.token_start:phrase_end]) == phrase
            and first_activity == activity_span
            and activity_span[0] >= phrase_end
            and activity_span[0] - phrase_end <= 2
        ):
            return False
    markers = (
        _ES_P6_EMBEDDING_MARKERS
        if language == "es"
        else _PT_P6_EMBEDDING_MARKERS
    )
    activity_spans = _activity_spans(analysis, clause)
    heads_que_relative = _p6_activity_heads_que_relative(
        analysis,
        activity_span,
        copula_index,
        language,
    )
    lower_bound = max(clause.token_start, activity_span[0] - 8)

    for marker_index in range(activity_span[0] - 1, lower_bound - 1, -1):
        marker = words[marker_index]
        if marker not in markers:
            continue

        coordinators = (
            {"y", "e", "pero"}
            if language == "es"
            else {"e", "mas", "porem"}
        )
        has_attachment_head = any(
            span[1] <= marker_index
            and not any(
                words[index] in coordinators
                and not (
                    words[index] == "e"
                    and analysis.tokens[index].had_acute
                )
                and (
                    (
                        index + 1 == marker_index
                        and not heads_que_relative
                        and not _p6_activity_is_frame_object(
                            analysis,
                            clause,
                            activity_span,
                            marker_index,
                            language,
                        )
                    )
                    or "que" not in words[span[1]:index]
                )
                for index in range(span[1], marker_index)
            )
            for span in activity_spans
        )
        if not has_attachment_head:
            continue

        if marker == "que" and heads_que_relative:
            continue

        if marker != "que" and heads_que_relative:
            candidate_has_coordinator = any(
                words[index] in coordinators
                and not (
                    words[index] == "e"
                    and analysis.tokens[index].had_acute
                )
                for index in range(marker_index + 1, activity_span[0])
            )
            relative_attachment_head = any(
                span[1] <= marker_index
                and _p6_activity_heads_que_relative(
                    analysis,
                    span,
                    copula_index,
                    language,
                )
                and not any(
                    words[index] in coordinators
                    and not (
                        words[index] == "e"
                        and analysis.tokens[index].had_acute
                    )
                    for index in range(span[1], marker_index)
                )
                for span in activity_spans
            )
            if (
                not candidate_has_coordinator
                and relative_attachment_head
                and _affirmative_self_fraud_counter_evidence(
                    analysis,
                    clause,
                    activity_span,
                    language,
                )
            ):
                return True

        finite_between = any(
            predicate.form.person is not None
            and not predicate.accent_ambiguous
            and predicate.token_start > marker_index
            and predicate.token_end <= activity_span[0]
            and _in_clause(
                predicate.token_start,
                predicate.token_end,
                clause,
            )
            for predicate in analysis.predicates
        )
        if finite_between:
            return True

    return _p6_distant_self_activity_is_embedded(
        analysis,
        clause,
        activity_span,
        copula_index,
        language,
    )


def _p6_has_left_attachment_material(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    marker_start: int,
    language: str,
) -> bool:
    """Recognize lexical material to the left of an attached adverbial frame."""

    del language
    return any(
        analysis.tokens[index].normalized.isalnum()
        for index in range(clause.token_start, marker_start)
    )


def _p6_pt_token_is_fused_preposition_determiner(
    analysis: FoundationAnalysis,
    index: int,
) -> bool:
    """Recognize bounded BR-PT fused preposition+determiner forms."""

    token = analysis.tokens[index]
    word = token.normalized
    if word in _PT_P6_FUSED_PREPOSITION_DETERMINERS:
        return True

    # The tokenizer's accent bit intentionally tracks acute accents only.
    # Portuguese crase uses a grave accent, so preserve this distinction
    # locally from the source surface instead of widening tokenizer semantics.
    return token.surface.casefold() in {
        "à",
        "às",
        "àquele",
        "àquela",
        "àqueles",
        "àquelas",
    }


def _p6_has_earlier_nominal_head(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    boundary_index: int,
    language: str,
) -> bool:
    """Recognize an earlier bounded nominal head before a nested PP."""

    words = [token.normalized for token in analysis.tokens]
    determiners = (
        _ES_P6_HEAD_DETERMINERS
        if language == "es"
        else _PT_P6_HEAD_DETERMINERS
    )
    prepositions = (
        _ES_P6_NESTED_PP_PREPOSITIONS
        if language == "es"
        else _PT_P6_NESTED_PP_PREPOSITIONS
    )
    non_activity_heads = (
        _ES_NON_ACTIVITY_FRAUD_HEADS
        if language == "es"
        else _PT_NON_ACTIVITY_FRAUD_HEADS
    )

    if any(
        span[1] <= boundary_index
        for span in _activity_spans(analysis, clause)
    ):
        return True

    for index in range(clause.token_start, boundary_index):
        word = words[index]
        if word in non_activity_heads:
            return True
        if (
            index > clause.token_start
            and words[index - 1] in determiners
            and word.isalpha()
            and word not in determiners
            and word not in prepositions
        ):
            return True

    return False


def _p6_self_activity_is_nested_pp(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    """Reject SELF-bearing activity nested in an earlier nominal head's bounded PP."""

    words = [token.normalized for token in analysis.tokens]
    determiners = (
        _ES_P6_HEAD_DETERMINERS
        if language == "es"
        else _PT_P6_HEAD_DETERMINERS
    )
    prepositions = (
        _ES_P6_NESTED_PP_PREPOSITIONS
        if language == "es"
        else _PT_P6_NESTED_PP_PREPOSITIONS
    )

    nominal_start = activity_span[0]
    while (
        nominal_start > clause.token_start
        and _is_closed_prenominal_modifier(
            words[nominal_start - 1],
            language,
        )
    ):
        nominal_start -= 1

    determiner_index = nominal_start - 1
    if determiner_index <= clause.token_start:
        return False

    preposition_index: int
    if (
        language == "pt"
        and _p6_pt_token_is_fused_preposition_determiner(
            analysis,
            determiner_index,
        )
    ):
        preposition_index = determiner_index
    else:
        if words[determiner_index] not in determiners:
            return False

        preposition_index = determiner_index - 1
        if (
            language == "pt"
            and words[determiner_index] in _PT_P6_POSSESSIVES
            and preposition_index > clause.token_start
            and words[preposition_index] in _PT_P6_ARTICLES
        ):
            preposition_index -= 1

        if preposition_index <= clause.token_start:
            return False
        if (
            words[preposition_index] not in prepositions
            and not (
                language == "pt"
                and _p6_pt_token_is_fused_preposition_determiner(
                    analysis,
                    preposition_index,
                )
            )
        ):
            return False

    return _p6_has_earlier_nominal_head(
        analysis,
        clause,
        preposition_index,
        language,
    )


def _p6_activity_relative_marker_span(
    analysis: FoundationAnalysis,
    head_span: tuple[int, int],
    activity_start: int,
    copula_index: int,
    language: str,
) -> tuple[int, int] | None:
    """Find a bounded relative marker following an earlier activity head."""

    words = [token.normalized for token in analysis.tokens]
    coordinators = (
        {"y", "e", "pero"}
        if language == "es"
        else {"e", "mas", "porem"}
    )
    qual_words = (
        _ES_P6_RELATIVE_QUAL
        if language == "es"
        else _PT_P6_RELATIVE_QUAL
    )
    lower = head_span[1]
    upper = min(activity_start, copula_index, lower + 8)

    for index in range(lower, upper):
        word = words[index]
        if word in _NOMINAL_ACTIVITY_BOUNDARIES:
            return None
        if (
            word in coordinators
            and not (
                word == "e"
                and analysis.tokens[index].had_acute
            )
        ):
            return None
        if word == "que":
            return index, index + 1
        if word in qual_words:
            return index, index + 1

    return None


def _p6_relative_coordinator_starts_nominal_conjunct(
    analysis: FoundationAnalysis,
    coordinator_index: int,
    activity_start: int,
    language: str,
) -> bool:
    """Distinguish a bounded nominal conjunct from coordinated relative VP material."""

    next_index = coordinator_index + 1
    if next_index >= activity_start:
        return False

    word = analysis.tokens[next_index].normalized
    determiners = (
        _ES_P6_HEAD_DETERMINERS
        if language == "es"
        else _PT_P6_HEAD_DETERMINERS
    )
    activity = _ES_ACTIVITY if language == "es" else _PT_ACTIVITY
    non_activity_heads = (
        _ES_NON_ACTIVITY_FRAUD_HEADS
        if language == "es"
        else _PT_NON_ACTIVITY_FRAUD_HEADS
    )
    return word in determiners | activity | non_activity_heads


def _p6_self_activity_is_nested_in_activity_relative(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
) -> bool:
    """Reject SELF-bearing activity nested inside an earlier bounded relative."""

    words = [token.normalized for token in analysis.tokens]
    coordinators = (
        {"y", "e", "pero"}
        if language == "es"
        else {"e", "mas", "porem"}
    )

    for head_span in _activity_spans(analysis, clause):
        if head_span[1] > activity_span[0]:
            continue

        marker_span = _p6_activity_relative_marker_span(
            analysis,
            head_span,
            activity_span[0],
            copula_index,
            language,
        )
        if marker_span is None:
            continue
        marker_start, marker_end = marker_span
        if marker_start >= activity_span[0]:
            continue

        nominal_conjunct = False
        for index in range(marker_end, activity_span[0]):
            if (
                words[index] not in coordinators
                or (
                    words[index] == "e"
                    and analysis.tokens[index].had_acute
                )
            ):
                continue
            if _p6_relative_coordinator_starts_nominal_conjunct(
                analysis,
                index,
                activity_span[0],
                language,
            ):
                nominal_conjunct = True
                break

        if nominal_conjunct:
            continue

        return True

    return False

def _p6_self_activity_is_inside_attached_adverbial(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    """Recognize SELF-bearing activity inside a bounded attached adverbial frame."""

    phrases = (
        _ES_P6_ATTACHED_ADVERBIAL_PHRASES
        if language == "es"
        else _PT_P6_ATTACHED_ADVERBIAL_PHRASES
    )
    for marker_start, marker_end in _phrase_spans(
        analysis,
        clause,
        phrases,
    ):
        if marker_start <= clause.token_start:
            continue
        if marker_end > activity_span[0]:
            continue
        if _p6_has_left_attachment_material(
            analysis,
            clause,
            marker_start,
            language,
        ):
            return True
    return False


def _p6_self_activity_has_prior_nominal_head(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    """Reject later SELF activity after an earlier nominal head, except a noun conjunct."""

    words = [token.normalized for token in analysis.tokens]
    nominal_start = activity_span[0]
    while (
        nominal_start > clause.token_start
        and _is_closed_prenominal_modifier(
            words[nominal_start - 1],
            language,
        )
    ):
        nominal_start -= 1

    boundary_index = nominal_start - 1
    if boundary_index <= clause.token_start:
        return False

    coordinators = (
        {"y", "e", "o", "u", "ni"}
        if language == "es"
        else {"e", "ou", "nem"}
    )
    if words[boundary_index] in coordinators:
        return False
    if (
        boundary_index > clause.token_start
        and words[boundary_index - 1] in coordinators
    ):
        return False

    return _p6_has_earlier_nominal_head(
        analysis,
        clause,
        boundary_index,
        language,
    )


def _p6_activity_nominal_start(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> int:
    """Return the bounded start of an activity NP used for P6 licensing."""

    words = [token.normalized for token in analysis.tokens]
    start = activity_span[0]
    while (
        start > clause.token_start
        and _is_closed_prenominal_modifier(words[start - 1], language)
    ):
        start -= 1

    determiners = (
        _ES_P6_HEAD_DETERMINERS
        if language == "es"
        else _PT_P6_HEAD_DETERMINERS
    )
    while start > clause.token_start and words[start - 1] in determiners:
        start -= 1
    return start


def _p6_self_activity_is_licensed_nominal_conjunct(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    """License a bounded same-level nominal conjunction, never a nested modifier."""

    words = [token.normalized for token in analysis.tokens]
    nominal_start = _p6_activity_nominal_start(
        analysis,
        clause,
        activity_span,
        language,
    )
    coordinator_index = nominal_start - 1
    if coordinator_index < clause.token_start:
        return False

    coordinators = (
        {"y", "e", "o", "u"}
        if language == "es"
        else {"e", "ou"}
    )
    if words[coordinator_index] not in coordinators:
        return False

    prepositions = (
        _ES_P6_NESTED_PP_PREPOSITIONS
        if language == "es"
        else _PT_P6_NESTED_PP_PREPOSITIONS
    )
    earlier_activities = tuple(
        span
        for span in _activity_spans(analysis, clause)
        if span[1] <= coordinator_index
    )
    if earlier_activities:
        nearest = max(earlier_activities, key=lambda span: span[1])
        return not any(
            words[index] in prepositions
            or (
                language == "pt"
                and _p6_pt_token_is_fused_preposition_determiner(
                    analysis,
                    index,
                )
            )
            for index in range(nearest[1], coordinator_index)
        )

    # Simple top-level nominal conjunction with an ordinary earlier head.
    # Require the coordinator to follow a determiner+noun NP directly and
    # reject any finite predicate before the coordinator.
    determiners = (
        _ES_P6_HEAD_DETERMINERS
        if language == "es"
        else _PT_P6_HEAD_DETERMINERS
    )
    prior_index = coordinator_index - 1
    if (
        prior_index > clause.token_start
        and words[prior_index].isalpha()
        and words[prior_index - 1] in determiners
        and not any(
            predicate.token_start < coordinator_index
            and _in_clause(
                predicate.token_start,
                predicate.token_end,
                clause,
            )
            for predicate in analysis.predicates
        )
    ):
        return True

    non_activity_heads = (
        _ES_NON_ACTIVITY_FRAUD_HEADS
        if language == "es"
        else _PT_NON_ACTIVITY_FRAUD_HEADS
    )
    head_indices = tuple(
        index
        for index in range(clause.token_start, coordinator_index)
        if words[index] in non_activity_heads
    )
    if not head_indices:
        return False
    head_index = max(head_indices)

    return not any(
        words[index] in prepositions
        or (
            language == "pt"
            and _p6_pt_token_is_fused_preposition_determiner(
                analysis,
                index,
            )
        )
        for index in range(head_index + 1, coordinator_index)
    )


def _p6_self_atom_is_positively_licensed(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
    atom: EvidenceAtom,
) -> bool:
    """License only explicitly supported SELF placements for copular P6."""

    words = [token.normalized for token in analysis.tokens]
    nominal_start = _p6_activity_nominal_start(
        analysis,
        clause,
        activity_span,
        language,
    )

    # The SELF-bearing activity must remain the nearest transaction candidate
    # before the fraud copula. A later transaction makes this referent unsafe.
    if any(
        span[0] >= activity_span[1] and span[0] < copula_index
        for span in _activity_spans(analysis, clause)
    ):
        return False

    # Activity NP is the clause-level subject.
    if nominal_start == clause.token_start:
        return True

    # Explicit bounded clause-initial topic frames. License only when the
    # selected activity is the first transaction immediately after the topic
    # phrase; the nearest-to-copula invariant above still applies.
    topicalizers = (
        (("respecto", "a"), ("en", "cuanto", "a"))
        if language == "es"
        else (("quanto", "a"),)
    )
    activity_spans = _activity_spans(analysis, clause)
    first_activity = activity_spans[0] if activity_spans else None
    for phrase in topicalizers:
        width = len(phrase)
        phrase_end = clause.token_start + width
        if (
            tuple(words[clause.token_start:phrase_end]) == phrase
            and first_activity == activity_span
            and activity_span[0] >= phrase_end
            and activity_span[0] - phrase_end <= 2
        ):
            return True

    # A complementizer-led activity subject with no earlier transaction.
    if (
        nominal_start > clause.token_start
        and words[nominal_start - 1] == "que"
        and not any(
            span[1] <= nominal_start - 1
            for span in _activity_spans(analysis, clause)
        )
        and nominal_start - 1 > clause.token_start
    ):
        return True

    if _p6_self_activity_is_licensed_nominal_conjunct(
        analysis,
        clause,
        activity_span,
        language,
    ):
        return True

    predicate_start, predicate_end = atom.predicate_token_span
    if predicate_end > activity_span[0]:
        return False

    subject_words = (
        {"yo", "nosotros", "nosotras"}
        if language == "es"
        else {"eu", "nos"}
    )
    emphatics = (
        {"mismo", "misma", "mismos", "mismas"}
        if language == "es"
        else {"mesmo", "mesma", "mesmos", "mesmas"}
    )

    # Clause-initial SELF predicate with a direct activity object.
    if all(
        word in subject_words | emphatics
        for word in words[clause.token_start:predicate_start]
    ):
        return True

    # Explicit bounded subjectless temporal frame.
    if (
        words[clause.token_start]
        == ("cuando" if language == "es" else "quando")
        and all(
            word in subject_words | emphatics
            for word in words[clause.token_start + 1:predicate_start]
        )
    ):
        return True

    return False


def _p6_self_counter_evidence_is_positively_licensed(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
    counter_evidence: tuple[EvidenceAtom, ...],
) -> bool:
    """Require every retained SELF atom to occupy an explicitly licensed shape."""

    return bool(counter_evidence) and all(
        _p6_self_atom_is_positively_licensed(
            analysis,
            clause,
            activity_span,
            copula_index,
            language,
            atom,
        )
        for atom in counter_evidence
    )


def _p6_self_counter_evidence_is_unsafe(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    copula_index: int,
    language: str,
    counter_evidence: tuple[EvidenceAtom, ...],
) -> bool:
    """Disable copular P6 SELF under the final B2 scope-reduction contract."""

    # B2R-T showed that every positive-license category can still attach SELF
    # to the customer's legitimate transaction when the disputed referent is
    # implicit/headless.  The safe hackathon contract therefore suppresses the
    # entire P6-copular proposition whenever SELF evidence would be attached.
    del analysis, clause, activity_span, copula_index, language
    return bool(counter_evidence)

def _fraud_copular_propositions(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    words = [token.normalized for token in analysis.tokens]
    copulas = _ES_COPULA if language == "es" else _PT_COPULA
    fraud_nouns = _ES_FRAUD_NOUNS if language == "es" else _PT_FRAUD_NOUNS
    fraud_adjectives = (
        _ES_FRAUD_ADJECTIVES if language == "es" else _PT_FRAUD_ADJECTIVES
    )
    non_activity_heads = (
        _ES_NON_ACTIVITY_FRAUD_HEADS
        if language == "es"
        else _PT_NON_ACTIVITY_FRAUD_HEADS
    )
    prepositions = (
        _ES_PREPOSITIONAL_ACTIVITY
        if language == "es"
        else _PT_PREPOSITIONAL_ACTIVITY
    )
    output: list[PositiveProposition] = []

    for copula_index in range(clause.token_start, clause.token_end):
        token = analysis.tokens[copula_index]
        if token.normalized not in copulas:
            continue
        if _span_has_bound_denial(
            analysis,
            clause,
            copula_index,
            copula_index + 1,
            language,
        ):
            continue

        marker_index = next(
            (
                index
                for index in range(copula_index + 1, min(clause.token_end, copula_index + 7))
                if words[index] in fraud_nouns | fraud_adjectives
            ),
            None,
        )
        if marker_index is None:
            continue

        candidate_activities = [
            span
            for span in _activity_spans(analysis, clause)
            if span[0] < copula_index
            and copula_index - span[0] <= 8
            and not _p6_left_activity_is_embedded(
                analysis,
                clause,
                span,
                copula_index,
                language,
            )
        ]
        if not candidate_activities:
            continue

        activity_span = max(candidate_activities, key=lambda span: span[0])
        if not _customer_anchored_activity(
            analysis,
            clause,
            activity_span,
            language,
        ):
            continue
        activity_index = activity_span[0]
        if (
            activity_index > clause.token_start
            and words[activity_index - 1] in prepositions
        ):
            continue

        if language == "pt" and token.normalized == "e" and not token.had_acute:
            immediate_fraud_adjective = (
                marker_index == copula_index + 1
                and words[marker_index] in fraud_adjectives
            )
            article_fraud_noun = (
                marker_index == copula_index + 2
                and words[copula_index + 1] in {"um", "uma"}
                and words[marker_index] in fraud_nouns
            )
            intervening_predicate = any(
                predicate.token_start >= activity_span[1]
                and predicate.token_end <= copula_index
                for predicate in analysis.predicates
                if _in_clause(predicate.token_start, predicate.token_end, clause)
            )
            if (
                intervening_predicate
                or not (immediate_fraud_adjective or article_fraud_noun)
            ):
                continue

        head_between = any(
            words[index] in non_activity_heads
            for index in range(activity_span[1], copula_index)
        )
        if head_between:
            continue

        predicate_path_blocked = any(
            words[index] in non_activity_heads
            or LexicalTag.ACTIVITY in analysis.tags[index]
            or (
                words[index] in copulas
                and not (
                    language == "pt"
                    and words[index] == "e"
                    and not analysis.tokens[index].had_acute
                )
            )
            for index in range(copula_index + 1, marker_index)
        )
        if predicate_path_blocked:
            continue

        marker_word = words[marker_index]
        if marker_word in fraud_adjectives:
            activity_word = words[activity_index]
            if not _fraud_adjective_agrees(activity_word, marker_word, language):
                continue

        counter_evidence = _affirmative_self_fraud_counter_evidence(
            analysis,
            clause,
            activity_span,
            language,
        )
        if _p6_self_counter_evidence_is_unsafe(
            analysis,
            clause,
            activity_span,
            copula_index,
            language,
            counter_evidence,
        ):
            continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.FRAUD_CHARACTERIZATION,
                rule="P6-copular",
                language=language,
                evidence_spans=(
                    activity_span,
                    (copula_index, copula_index + 1),
                    (marker_index, marker_index + 1),
                ),
                activity_span=activity_span,
                predicate=None,
                counter_evidence=counter_evidence,
            )
        )

    return output


def _subjectless_spanish_fraud_compatibility(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    """Preserve the frozen Spanish declarative `Es un fraude.` polarity."""

    if language != "es" or clause.token_start >= clause.token_end:
        return []

    tokens = analysis.tokens
    words = [token.normalized for token in tokens]

    # Interrogative forms remain outside this compatibility construction.
    if words[clause.token_start] == "¿":
        return []
    if (
        clause.token_end < len(tokens)
        and tokens[clause.token_end].normalized == "?"
    ):
        return []

    copula_index = clause.token_start
    if words[copula_index] != "es":
        return []

    marker_index = copula_index + 1
    if marker_index >= clause.token_end:
        return []
    if words[marker_index] == "un":
        marker_index += 1
    if marker_index >= clause.token_end or words[marker_index] != "fraude":
        return []

    tail_start = marker_index + 1
    txid_span: tuple[int, int] | None = None
    for index in range(tail_start, clause.token_end):
        word = words[index]
        if tokens[index].is_txid:
            if txid_span is not None:
                return []
            txid_span = (index, index + 1)
            continue
        if word != ":":
            return []

    evidence: list[tuple[int, int]] = [
        (copula_index, copula_index + 1),
        (marker_index, marker_index + 1),
    ]
    activity_ref = "topic_transaction"
    if txid_span is not None:
        evidence.append(txid_span)
        activity_ref = "linked_same_clause_txid"

    return [
        _make_proposition(
            analysis,
            clause,
            family=PropositionFamily.FRAUD_CHARACTERIZATION,
            rule="P6-subjectless-es-compat",
            language=language,
            evidence_spans=evidence,
            activity_span=txid_span,
            predicate=None,
            activity_ref=activity_ref,
        )
    ]


def _fraud_characterizations(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    return [
        *_fraud_attributive_propositions(analysis, clause, language),
        *_fraud_copular_propositions(analysis, clause, language),
        *_subjectless_spanish_fraud_compatibility(
            analysis,
            clause,
            language,
        ),
    ]




_ES_ACTIVITY_ANAPHORS = frozenset(
    {"lo", "la", "los", "las", "esto", "eso", "aquello", "este", "esta", "ese", "esa"}
)
_PT_ACTIVITY_ANAPHORS = frozenset(
    {"isso", "isto", "aquilo", "este", "esta", "esse", "essa", "o", "a"}
)

_ES_P7_OBJECT_DETERMINERS = frozenset(
    {
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
        "aquel", "aquella", "aquellos", "aquellas",
    }
)
_PT_P7_OBJECT_DETERMINERS = frozenset(
    {
        "o", "a", "os", "as", "um", "uma", "uns", "umas",
        "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
        "aquele", "aquela", "aqueles", "aquelas",
    }
)
_ES_P7_NEUTRAL_DEMONSTRATIVES = frozenset({"esto", "eso", "aquello"})
_PT_P7_NEUTRAL_DEMONSTRATIVES = frozenset({"isto", "isso", "aquilo"})


def _p7_classify_object_head(
    analysis: FoundationAnalysis,
    index: int,
) -> tuple[str, tuple[int, int]]:
    if analysis.tokens[index].is_txid or LexicalTag.ACTIVITY in analysis.tags[index]:
        return "activity", (index, index + 1)
    if LexicalTag.DESCRIPTOR_NOUN in analysis.tags[index]:
        return "descriptor", (index, index + 1)
    return "non_activity", (index, index + 1)


def _p7_overt_object_after_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> tuple[str, tuple[int, int] | None]:
    if predicate.token_end >= clause.token_end:
        return "none", None

    words = [token.normalized for token in analysis.tokens]
    determiners = (
        _ES_P7_OBJECT_DETERMINERS
        if language == "es"
        else _PT_P7_OBJECT_DETERMINERS
    )
    neutral_demonstratives = (
        _ES_P7_NEUTRAL_DEMONSTRATIVES
        if language == "es"
        else _PT_P7_NEUTRAL_DEMONSTRATIVES
    )
    index = predicate.token_end
    word = words[index]

    if word in neutral_demonstratives:
        return "none", None

    if analysis.tokens[index].is_txid:
        return "activity", (index, index + 1)

    if LexicalTag.ACTIVITY in analysis.tags[index]:
        return "activity", (index, index + 1)

    if LexicalTag.DESCRIPTOR_NOUN in analysis.tags[index]:
        return "descriptor", (index, index + 1)

    if word in determiners:
        head = _closed_nominal_head_index(
            analysis,
            index + 1,
            clause.token_end,
            language,
        )
        if head is not None:
            return _p7_classify_object_head(analysis, head)
        return "none", None

    if word in {"a", "ao", "aos"}:
        article = index + 1
        if article < clause.token_end and words[article] in determiners:
            head = _closed_nominal_head_index(
                analysis,
                article + 1,
                clause.token_end,
                language,
            )
            if head is not None:
                return _p7_classify_object_head(analysis, head)

    return "none", None


def _p7_preposed_overt_object(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> tuple[str, tuple[int, int] | None]:
    words = [token.normalized for token in analysis.tokens]
    determiners = (
        _ES_P7_OBJECT_DETERMINERS
        if language == "es"
        else _PT_P7_OBJECT_DETERMINERS
    )
    candidates: list[int] = []

    for index in range(clause.token_start, predicate.token_start - 1):
        if words[index] not in determiners:
            continue
        head = _closed_nominal_head_index(
            analysis,
            index + 1,
            predicate.token_start,
            language,
        )
        if head is None:
            continue
        if any(
            other.token_start == head
            for other in analysis.predicates
            if _in_clause(other.token_start, other.token_end, clause)
        ):
            continue
        candidates.append(head)

    if not candidates:
        return "none", None

    return _p7_classify_object_head(analysis, max(candidates))


def _p7_nominal_target(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> tuple[str, tuple[int, int] | None]:
    after_kind, after_span = _p7_overt_object_after_predicate(
        analysis,
        clause,
        predicate,
        language,
    )
    if after_kind != "none":
        return after_kind, after_span

    before_kind, before_span = _p7_preposed_overt_object(
        analysis,
        clause,
        predicate,
        language,
    )
    if before_kind != "none":
        return before_kind, before_span

    return "none", None


def _p7_has_activity_anaphor(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> tuple[int, int] | None:
    anaphors = _ES_ACTIVITY_ANAPHORS if language == "es" else _PT_ACTIVITY_ANAPHORS
    article_anaphors = (
        {"la", "los", "las"}
        if language == "es"
        else {"o", "a"}
    )
    words = [token.normalized for token in analysis.tokens]

    candidates: list[int] = []
    for index in range(
        max(clause.token_start, predicate.token_start - 3),
        min(clause.token_end, predicate.token_end + 4),
    ):
        if words[index] not in anaphors:
            continue

        if words[index] in article_anaphors and index + 1 < clause.token_end:
            head = _closed_nominal_head_index(
                analysis,
                index + 1,
                clause.token_end,
                language,
            )
            if head is not None:
                head_is_predicate = any(
                    other.token_start == head
                    for other in analysis.predicates
                    if _in_clause(other.token_start, other.token_end, clause)
                )
                if (
                    not head_is_predicate
                    and analysis.tokens[head].normalized
                    not in _NOMINAL_ACTIVITY_BOUNDARIES
                    and LexicalTag.ACTIVITY not in analysis.tags[head]
                ):
                    continue

        candidates.append(index)

    if not candidates:
        return None

    index = min(
        candidates,
        key=lambda item: min(
            abs(item - predicate.token_start),
            abs(item - predicate.token_end),
        ),
    )
    return (index, index + 1)


def _nearest_preceding_activity_or_txid(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], str] | None:
    prior_clauses = [
        prior for prior in analysis.clauses
        if prior.index < clause.index
    ]
    for prior in reversed(prior_clauses):
        for index in range(prior.token_end - 1, prior.token_start - 1, -1):
            if analysis.tokens[index].is_txid:
                return (index, index + 1), "linked_prior_txid"
            if LexicalTag.ACTIVITY not in analysis.tags[index]:
                continue
            activity_span = (index, index + 1)
            if _customer_anchored_activity(
                analysis,
                prior,
                activity_span,
                language,
            ):
                return activity_span, "linked_prior_activity"
    return None


def _d2_anaphoric_prior_activity(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> tuple[tuple[int, int], tuple[int, int], str] | None:
    anaphor_span = _p7_has_activity_anaphor(
        analysis,
        clause,
        predicate,
        language,
    )
    if anaphor_span is None:
        return None

    prior = _nearest_preceding_activity_or_txid(
        analysis,
        clause,
        language,
    )
    if prior is None:
        return None

    activity_span, activity_ref = prior
    return anaphor_span, activity_span, activity_ref


def _nearest_preceding_activity_or_txid_for_self_exculpation(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], str] | None:
    linked = _nearest_preceding_activity_or_txid(
        analysis,
        clause,
        language,
    )
    if linked is not None:
        return linked

    if clause.index <= 0:
        return None

    prior = analysis.clauses[clause.index - 1]
    for index in range(prior.token_end - 1, prior.token_start - 1, -1):
        if analysis.tokens[index].is_txid:
            return (index, index + 1), "linked_prior_txid"
        if LexicalTag.ACTIVITY in analysis.tags[index]:
            return (index, index + 1), "linked_prior_activity"
    return None


def _closed_self_exculpation_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[int, int] | None:
    words = [token.normalized for token in analysis.tokens]
    start = clause.token_start

    if language == "es":
        forms = {
            ("no", "fui", "yo"),
            ("no", "fuimos", "nosotros"),
            ("no", "fuimos", "nosotras"),
        }
        cleft_words = {"quien", "que"}
    else:
        forms = {
            ("nao", "fui", "eu"),
            ("nao", "fomos", "nos"),
        }
        cleft_words = {"quem", "que"}

    if start + 3 > clause.token_end:
        return None

    triple = tuple(words[start : start + 3])
    if triple not in forms:
        return None

    if (
        language == "pt"
        and triple[-1] == "nos"
        and not analysis.tokens[start + 2].had_acute
    ):
        return None

    end = start + 3
    if end == clause.token_end:
        return (start, end)

    if words[end] not in cleft_words:
        return None

    perform = next(
        (
            predicate
            for predicate in analysis.predicates
            if _in_clause(predicate.token_start, predicate.token_end, clause)
            and predicate.form.family is PredicateFamily.PERFORM
            and predicate.token_start >= end + 1
            and predicate.token_start - end <= 2
        ),
        None,
    )
    if perform is None:
        return None

    return (start, perform.token_end)


def _argumentless_self_exculpation(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    exculpation_span = _closed_self_exculpation_span(
        analysis,
        clause,
        language,
    )
    if exculpation_span is None:
        return []

    prior = _nearest_preceding_activity_or_txid_for_self_exculpation(
        analysis,
        clause,
        language,
    )
    activity_span: tuple[int, int] | None = None
    activity_ref = "topic_transaction"
    evidence: list[tuple[int, int]] = [exculpation_span]

    if prior is not None:
        activity_span, activity_ref = prior
        evidence.append(activity_span)

    return [
        _make_proposition(
            analysis,
            clause,
            family=PropositionFamily.PERFORMANCE_DENIAL,
            rule="P2-R3-self-exculpation",
            language=language,
            evidence_spans=evidence,
            activity_span=activity_span,
            predicate=None,
            activity_ref=activity_ref,
        )
    ]


def _activity_nonrecognition(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family is not PredicateFamily.RECOGNIZE:
            continue
        if not _predicate_has_denial(analysis, clause, predicate, language):
            continue

        self_evidence = _bound_self_evidence(
            analysis,
            clause,
            predicate,
            frozenset({SelfRole.SUBJECT, SelfRole.AGENT}),
        )
        if self_evidence is None:
            continue

        target_kind, target_span = _p7_nominal_target(
            analysis,
            clause,
            predicate,
            language,
        )
        if target_kind in {"descriptor", "non_activity"}:
            continue

        denial_index = _bound_denial_index(
            analysis,
            clause,
            predicate,
            language,
        )
        if denial_index is None:
            continue
        denial_span = (denial_index, denial_index + 1)
        nearest_self = (
            self_evidence.token_start,
            self_evidence.token_end,
        )
        evidence: list[tuple[int, int]] = [denial_span, nearest_self]
        activity_span: tuple[int, int] | None = None
        activity_ref = "topic_transaction"
        rule = "P7"

        if target_kind == "activity" and target_span is not None:
            if not _customer_anchored_activity(
                analysis,
                clause,
                target_span,
                language,
            ):
                continue
            activity_span = target_span
            activity_ref = "explicit_activity"
            evidence.append(target_span)
        else:
            anaphor_span = _p7_has_activity_anaphor(
                analysis,
                clause,
                predicate,
                language,
            )
            if anaphor_span is not None:
                evidence.append(anaphor_span)

            prior = _nearest_preceding_activity_or_txid(
                analysis,
                clause,
                language,
            )
            if prior is not None:
                activity_span, activity_ref = prior
                evidence.append(activity_span)
                rule = "P7-R3-activity-anaphora"
            elif anaphor_span is not None or predicate.form.person == 1:
                activity_ref = "topic_transaction"
                rule = "P7-R3-topic-default"
            else:
                continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.ACTIVITY_NONRECOGNITION,
                rule=rule,
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=activity_ref,
            )
        )

    return output




_ES_COMPROMISE_PARTICIPLES = frozenset(
    {
        "robado", "robada", "robados", "robadas",
        "clonado", "clonada", "clonados", "clonadas",
        "hackeado", "hackeada", "hackeados", "hackeadas",
    }
)
_PT_COMPROMISE_PARTICIPLES = frozenset(
    {
        "roubado", "roubada", "roubados", "roubadas",
        "furtado", "furtada", "furtados", "furtadas",
        "clonado", "clonada", "clonados", "clonadas",
        "hackeado", "hackeada", "hackeados", "hackeadas",
        "invadido", "invadida", "invadidos", "invadidas",
    }
)


def _instrument_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.INSTRUMENT in analysis.tags[index]
    )


def _self_dative_near_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    span: tuple[int, int],
    *,
    max_before_gap: int,
) -> tuple[int, int] | None:
    datives = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.DATIVE}),
    )
    preceding = tuple(
        item
        for item in datives
        if item[1] <= span[0]
        and span[0] - item[1] <= max_before_gap
        and not any(
            predicate.token_start >= item[1]
            and predicate.token_end <= span[0]
            and predicate.form.person is not None
            and not predicate.accent_ambiguous
            for predicate in analysis.predicates
            if _in_clause(predicate.token_start, predicate.token_end, clause)
        )
        and not any(
            analysis.tokens[index].normalized == "que"
            for index in range(item[1], span[0])
        )
    )
    if not preceding:
        return None
    return min(preceding, key=lambda item: span[0] - item[1])


def _nearest_eligible_compromise_instrument(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    anchor_span: tuple[int, int],
) -> tuple[tuple[int, int], tuple[int, int] | None] | None:
    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    explicit_customer: dict[tuple[int, int], tuple[int, int]] = {}
    for instrument in _instrument_spans(analysis, clause):
        direct_possessor = next(
            (
                possessor
                for possessor in possessors
                if possessor[1] == instrument[0]
                or possessor[0] == instrument[1]
            ),
            None,
        )
        if direct_possessor is not None:
            explicit_customer[instrument] = direct_possessor

    candidates: list[
        tuple[tuple[int, int], tuple[int, int] | None]
    ] = []
    for instrument in _instrument_spans(analysis, clause):
        if _explicit_third_person_activity_possession(
            analysis,
            clause,
            instrument,
            language,
        ):
            continue
        if instrument in explicit_customer:
            candidates.append((instrument, explicit_customer[instrument]))
            continue

        dative = _self_dative_near_span(
            analysis,
            clause,
            anchor_span,
            max_before_gap=2,
        )
        if dative is not None:
            candidates.append((instrument, dative))

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda item: min(
            abs(item[0][0] - anchor_span[0]),
            abs(item[0][0] - anchor_span[1]),
        ),
    )


def _source_accent_selects_predicate(
    analysis: FoundationAnalysis,
    predicate: PredicateMatch,
) -> bool:
    if predicate.token_end - predicate.token_start != 1:
        return True

    token = analysis.tokens[predicate.token_start]
    if not token.had_acute:
        return True

    same_span_family = tuple(
        candidate
        for candidate in analysis.predicates
        if candidate.token_start == predicate.token_start
        and candidate.token_end == predicate.token_end
        and candidate.form.family is predicate.form.family
    )
    if not any(candidate.form.accent_required for candidate in same_span_family):
        return True

    return predicate.form.accent_required


def _first_person_compromise(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    activity_span = _nearest_activity_span(analysis, clause, None)

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family is not PredicateFamily.COMPROMISE:
            continue
        if not _source_accent_selects_predicate(analysis, predicate):
            continue
        if _predicate_has_denial(analysis, clause, predicate, language):
            continue

        # P8 models the customer as affected owner/experiencer, not actor.
        if predicate.form.person == 1:
            continue

        predicate_span = (predicate.token_start, predicate.token_end)
        instrument_evidence = _nearest_eligible_compromise_instrument(
            analysis,
            clause,
            language,
            predicate_span,
        )
        if instrument_evidence is None:
            continue

        instrument_span, customer_span = instrument_evidence
        evidence: list[tuple[int, int]] = [instrument_span]
        if customer_span is not None:
            evidence.append(customer_span)

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.COMPROMISE_LINKED_ACTIVITY,
                rule="P8-first-person-compromise",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "customer_instrument_compromise"
                ),
            )
        )

    participles = (
        _ES_COMPROMISE_PARTICIPLES
        if language == "es"
        else _PT_COMPROMISE_PARTICIPLES
    )
    for index in range(clause.token_start, clause.token_end):
        if analysis.tokens[index].normalized not in participles:
            continue

        participle_span = (index, index + 1)
        directly_negated = _span_has_bound_denial(
            analysis,
            clause,
            index,
            index + 1,
            language,
        )
        copulas = _ES_COPULA if language == "es" else _PT_COPULA
        negated_auxiliary = any(
            analysis.tokens[aux].normalized in copulas
            and _span_has_bound_denial(
                analysis,
                clause,
                aux,
                aux + 1,
                language,
            )
            for aux in range(max(clause.token_start, index - 3), index)
        )
        if directly_negated or negated_auxiliary:
            continue

        instrument_evidence = _nearest_eligible_compromise_instrument(
            analysis,
            clause,
            language,
            participle_span,
        )
        if instrument_evidence is None:
            continue

        instrument_span, customer_span = instrument_evidence
        evidence: list[tuple[int, int]] = [instrument_span, participle_span]
        if customer_span is not None:
            evidence.append(customer_span)

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.COMPROMISE_LINKED_ACTIVITY,
                rule="P8-first-person-compromise-participle",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=None,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "customer_instrument_compromise"
                ),
            )
        )

    return output




_D1_INHERITABLE_FAMILIES: dict[
    PredicateFamily,
    PropositionFamily,
] = {
    PredicateFamily.PERFORM: PropositionFamily.PERFORMANCE_DENIAL,
    PredicateFamily.ORIGINATE: PropositionFamily.ORIGINATION_DENIAL,
    PredicateFamily.AUTHORIZE: PropositionFamily.AUTHORIZATION_DENIAL,
    PredicateFamily.RECOGNIZE: PropositionFamily.ACTIVITY_NONRECOGNITION,
}


def _d1_is_whitespace_dash(text: str, token: Token) -> bool:
    if token.surface not in {"-", "–", "—"}:
        return False
    before_ok = token.start == 0 or text[token.start - 1].isspace()
    after_ok = token.end == len(text) or text[token.end].isspace()
    return before_ok and after_ok


def _d1_separator_indices(
    analysis: FoundationAnalysis,
    text: str,
) -> tuple[int, ...]:
    output: list[int] = []
    for index, token in enumerate(analysis.tokens):
        if token.surface == ",":
            if not _is_numeric_punctuation(text, token):
                output.append(index)
            continue
        if token.surface == ";":
            output.append(index)
            continue
        if _d1_is_whitespace_dash(text, token):
            output.append(index)
    return tuple(output)


def _d1_segment_bounds(
    analysis: FoundationAnalysis,
    text: str,
    separator_index: int,
) -> tuple[ClauseSegment, ClauseSegment] | None:
    prefix_start = 0
    for index in range(separator_index - 1, -1, -1):
        if _is_primary_boundary(text, analysis.tokens[index]):
            prefix_start = index + 1
            break

    suffix_end = len(analysis.tokens)
    for index in range(separator_index + 1, len(analysis.tokens)):
        if _is_primary_boundary(text, analysis.tokens[index]):
            suffix_end = index
            break

    if prefix_start >= separator_index or separator_index + 1 >= suffix_end:
        return None

    prefix = ClauseSegment(
        index=-1,
        token_start=prefix_start,
        token_end=separator_index,
        source_start=analysis.tokens[prefix_start].start,
        source_end=analysis.tokens[separator_index - 1].end,
    )
    suffix = ClauseSegment(
        index=-1,
        token_start=separator_index + 1,
        token_end=suffix_end,
        source_start=analysis.tokens[separator_index + 1].start,
        source_end=analysis.tokens[suffix_end - 1].end,
    )
    return prefix, suffix


def _d1_closed_continuation(
    analysis: FoundationAnalysis,
    suffix: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    finite_predicate = any(
        _in_clause(predicate.token_start, predicate.token_end, suffix)
        and predicate.form.person is not None
        for predicate in analysis.predicates
    )
    if finite_predicate:
        return None

    words = [
        analysis.tokens[index].normalized
        for index in range(suffix.token_start, suffix.token_end)
        if analysis.tokens[index].surface != ","
    ]
    if not words:
        return None

    if language == "es":
        starts_closed = (
            len(words) >= 2 and words[0] == "ni" and words[1] in {"yo", "nosotros", "nosotras"}
        ) or (
            len(words) >= 2 and words[0] in {"yo", "nosotros", "nosotras"} and words[1] == "tampoco"
        )
    else:
        starts_closed = (
            len(words) >= 2 and words[0] == "nem" and words[1] in {"eu", "nos"}
        ) or (
            len(words) >= 2
            and words[0] in {"eu", "nos"}
            and (
                words[1] == "tampouco"
                or (
                    len(words) >= 3
                    and words[1] == "tambem"
                    and words[2] == "nao"
                )
            )
        )
    if not starts_closed:
        return None

    self_spans = _role_spans(
        analysis,
        suffix,
        frozenset({SelfRole.SUBJECT}),
    )
    if not self_spans:
        return None

    coord_word = "ni" if language == "es" else "nem"
    marker_index = next(
        (
            index
            for index in range(suffix.token_start, suffix.token_end)
            if analysis.tokens[index].normalized in {
                coord_word,
                "tampoco",
                "tampouco",
                "tambem",
                "nao",
            }
        ),
        None,
    )
    if marker_index is None:
        return None

    return self_spans[0], (marker_index, marker_index + 1)


def _d1_prior_frame(
    analysis: FoundationAnalysis,
    prefix: ClauseSegment,
    language: str,
) -> tuple[PredicateMatch, tuple[int, int] | None, tuple[int, int], PropositionFamily] | None:
    candidates = [
        predicate
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, prefix)
        and predicate.form.family in _D1_INHERITABLE_FAMILIES
        and predicate.form.person is not None
        and _predicate_has_denial(analysis, prefix, predicate, language)
    ]
    if not candidates:
        return None

    predicate = max(candidates, key=lambda item: item.token_start)
    denial_index = _bound_denial_index(
        analysis,
        prefix,
        predicate,
        language,
    )
    if denial_index is None:
        return None

    denial_span = (denial_index, denial_index + 1)
    activity_span = _nearest_activity_span(analysis, prefix, predicate)
    family = _D1_INHERITABLE_FAMILIES[predicate.form.family]
    return predicate, activity_span, denial_span, family


def _elliptical_continuations(
    analysis: FoundationAnalysis,
    text: str,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []

    for separator_index in _d1_separator_indices(analysis, text):
        bounds = _d1_segment_bounds(analysis, text, separator_index)
        if bounds is None:
            continue
        prefix, suffix = bounds

        continuation = _d1_closed_continuation(
            analysis,
            suffix,
            language,
        )
        if continuation is None:
            continue
        self_span, continuation_marker = continuation

        frame = _d1_prior_frame(
            analysis,
            prefix,
            language,
        )
        if frame is None:
            continue
        predicate, activity_span, denial_span, family = frame

        if family is PropositionFamily.ACTIVITY_NONRECOGNITION:
            if activity_span is None:
                activity_ref = "topic_transaction"
            elif not _customer_anchored_activity(
                analysis,
                prefix,
                activity_span,
                language,
            ):
                continue
            else:
                activity_ref = "linked_prior_activity"
        else:
            activity_ref = (
                "linked_prior_activity"
                if activity_span is not None
                else "topic_transaction"
            )

        evidence = [
            denial_span,
            self_span,
            continuation_marker,
            (predicate.token_start, predicate.token_end),
        ]
        if activity_span is not None:
            evidence.append(activity_span)

        containing_clause = next(
            (
                clause
                for clause in analysis.clauses
                if _in_clause(self_span[0], self_span[1], clause)
            ),
            suffix,
        )

        output.append(
            _make_proposition(
                analysis,
                containing_clause,
                family=family,
                rule="R3-D1-elliptical-continuation",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=activity_ref,
            )
        )

    return output


def build_positive_propositions(
    text: str,
    language: str,
) -> tuple[PositiveProposition, ...]:
    """Construct unresolved RF1H-B2 positive propositions.

    This API is intentionally internal to the grammar engine. It does not apply
    B3 scope/exclusion or message-level retraction and is not wired into the
    production boolean classifier.
    """

    analysis = analyze_foundation(text, language)
    propositions: list[PositiveProposition] = []

    for clause in analysis.clauses:
        propositions.extend(_ownership_denials(analysis, clause, language))
        propositions.extend(_alienation_denials(analysis, clause, language))
        propositions.extend(
            _predicate_denials(
                analysis,
                clause,
                language,
                predicate_family=PredicateFamily.PERFORM,
                proposition_family=PropositionFamily.PERFORMANCE_DENIAL,
                rule="P2",
                self_roles=frozenset({SelfRole.SUBJECT, SelfRole.AGENT}),
            )
        )
        propositions.extend(
            _argumentless_self_exculpation(
                analysis,
                clause,
                language,
            )
        )
        propositions.extend(
            _predicate_denials(
                analysis,
                clause,
                language,
                predicate_family=PredicateFamily.ORIGINATE,
                proposition_family=PropositionFamily.ORIGINATION_DENIAL,
                rule="P3",
                self_roles=frozenset({SelfRole.SOURCE}),
            )
        )
        propositions.extend(_authorization_denials(analysis, clause, language))
        propositions.extend(
            _possessive_authorization_absence(analysis, clause, language)
        )
        propositions.extend(
            _unauthorized_participle_denials(analysis, clause, language)
        )
        propositions.extend(
            _third_party_unauthorized_use(analysis, clause, language)
        )
        propositions.extend(
            _exceeded_authorization_propositions(
                analysis,
                clause,
                language,
            )
        )
        propositions.extend(
            _fraud_characterizations(analysis, clause, language)
        )
        propositions.extend(
            _activity_nonrecognition(analysis, clause, language)
        )
        propositions.extend(
            _first_person_compromise(analysis, clause, language)
        )

    propositions.extend(
        _elliptical_continuations(analysis, text, language)
    )

    unique: dict[
        tuple[str, str, int, int, int, str, tuple[int, int] | None],
        PositiveProposition,
    ] = {}
    for proposition in propositions:
        key = (
            proposition.family.value,
            proposition.rule,
            proposition.clause_index,
            proposition.token_start,
            proposition.token_end,
            proposition.activity_ref,
            proposition.predicate_token_span,
        )
        unique[key] = proposition
    return tuple(unique.values())


_B3_MODE_PRECEDENCE = {
    PropositionMode.REPORTED_PRIOR_BELIEF: 0,
    PropositionMode.AUTHORIZED_THIRD_PARTY: 1,
    PropositionMode.HYPOTHETICAL: 2,
    PropositionMode.UNCERTAIN: 3,
    PropositionMode.INFORMATION_REQUEST: 4,
    PropositionMode.QUESTIONED: 5,
    PropositionMode.ASSERTIVE: 99,
}


def _b3_scope_barrier(
    analysis: FoundationAnalysis,
    index: int,
) -> bool:
    token = analysis.tokens[index]
    return (
        token.normalized in {",", ";", ":"}
        or LexicalTag.CONTRAST in analysis.tags[index]
    )


def _b3_domain_end(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    operator_index: int,
) -> int:
    for index in range(operator_index + 1, clause.token_end):
        if _b3_scope_barrier(analysis, index):
            return index
    return clause.token_end


def _b3_question_domain(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> ScopeDomain | None:
    opener = next(
        (
            index
            for index in range(clause.token_start, clause.token_end)
            if LexicalTag.QUESTION_OPEN in analysis.tags[index]
        ),
        None,
    )
    if opener is not None:
        return ScopeDomain(
            mode=PropositionMode.QUESTIONED,
            token_start=opener + 1,
            token_end=clause.token_end,
            provenance="M8:explicit_question",
        )

    boundary_index = clause.token_end
    if (
        boundary_index < len(analysis.tokens)
        and analysis.tokens[boundary_index].normalized == "?"
    ):
        return ScopeDomain(
            mode=PropositionMode.QUESTIONED,
            token_start=clause.token_start,
            token_end=clause.token_end,
            provenance="M8:question_boundary",
        )
    return None


def _b3_information_request_domain(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    question: ScopeDomain | None,
) -> ScopeDomain | None:
    """Recognize the bounded M4 security/prevention question subset."""

    if question is None:
        return None

    has_security_term = any(
        LexicalTag.SECURITY_INFO in analysis.tags[index]
        for index in range(question.token_start, question.token_end)
    )
    if not has_security_term:
        return None

    return ScopeDomain(
        mode=PropositionMode.INFORMATION_REQUEST,
        token_start=question.token_start,
        token_end=question.token_end,
        provenance="M4:security_information_request",
    )


def _b3_domain_contains_index(
    domain: ScopeDomain,
    index: int,
) -> bool:
    return domain.token_start <= index < domain.token_end


def _b3_authorization_domain_end(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    grant_end: int,
    language: str,
) -> int:
    """Bound M6 to the local grant/purpose surface, never a later activity."""

    coordinator = "y" if language == "es" else "e"
    for index in range(grant_end, clause.token_end):
        if _b3_scope_barrier(analysis, index):
            return index
        if analysis.tokens[index].normalized == coordinator:
            return index
    return clause.token_end


def _b3_authorized_third_party_domains(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    prior_domains: tuple[ScopeDomain, ...],
) -> tuple[ScopeDomain, ...]:
    """Recognize bounded affirmative M6 grants to a known third party.

    This is deliberately narrower than general authorization semantics. A grant
    must be first-person, affirmative, non-irrealis, and locally linked to a
    known actor. The domain stops before a comma/contrast/coordinator so it
    cannot suppress a subsequent exceeded-authorization proposition.
    """

    actor_spans = _known_actor_spans(analysis, clause, language)
    if not actor_spans:
        return ()

    candidates: list[tuple[int, int, str]] = []

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family not in {
            PredicateFamily.AUTHORIZE,
            PredicateFamily.GIVE_PERMISSION,
        }:
            continue
        if predicate.form.person != 1:
            continue
        if predicate.form.mood != "indicative":
            continue
        if predicate.form.tense_aspect in {"future", "conditional"}:
            continue
        if not _source_accent_selects_predicate(analysis, predicate):
            continue
        if _predicate_has_denial(analysis, clause, predicate, language):
            continue
        if any(
            domain.mode in {
                PropositionMode.HYPOTHETICAL,
                PropositionMode.UNCERTAIN,
                PropositionMode.INFORMATION_REQUEST,
                PropositionMode.QUESTIONED,
            }
            and _b3_domain_contains_index(domain, predicate.token_start)
            for domain in prior_domains
        ):
            continue

        end = _b3_authorization_domain_end(
            analysis,
            clause,
            predicate.token_end,
            language,
        )
        if predicate.form.family is PredicateFamily.GIVE_PERMISSION:
            has_auth_noun = any(
                LexicalTag.AUTH_NOUN in analysis.tags[index]
                for index in range(predicate.token_end, end)
            )
            if not has_auth_noun:
                continue

        candidates.append(
            (
                predicate.token_start,
                end,
                "authorize"
                if predicate.form.family is PredicateFamily.AUTHORIZE
                else "give_permission",
            )
        )

    for start, end in _limited_grant_surface_spans(
        analysis,
        clause,
        language,
    ):
        if any(
            domain.mode in {
                PropositionMode.HYPOTHETICAL,
                PropositionMode.UNCERTAIN,
                PropositionMode.INFORMATION_REQUEST,
                PropositionMode.QUESTIONED,
            }
            and _b3_domain_contains_index(domain, start)
            for domain in prior_domains
        ):
            continue
        candidates.append(
            (
                start,
                _b3_authorization_domain_end(
                    analysis,
                    clause,
                    end,
                    language,
                ),
                "limited_grant",
            )
        )

    domains: list[ScopeDomain] = []
    for start, end, source in candidates:
        if end <= start:
            continue
        has_local_actor = any(
            start <= actor_start < end
            for actor_start, _ in actor_spans
        )
        if not has_local_actor:
            continue
        domains.append(
            ScopeDomain(
                mode=PropositionMode.AUTHORIZED_THIRD_PARTY,
                token_start=start,
                token_end=end,
                provenance=f"M6:authorized_third_party:{source}",
            )
        )

    return tuple(domains)


_ES_REPORTED_PRIOR_BELIEF_FRAMES = (
    ("pense", "que"),
    ("crei", "que"),
)
_PT_REPORTED_PRIOR_BELIEF_FRAMES = (
    ("achei", "que"),
    ("pensei", "que"),
    ("ia", "dizer", "que"),
)

_ES_RETRACTION_DISTINGUISHERS = frozenset(
    {
        "otro", "otra", "otros", "otras",
        "anterior", "ayer",
        "primero", "primera", "primeros", "primeras",
        "segundo", "segunda", "segundos", "segundas",
    }
)
_PT_RETRACTION_DISTINGUISHERS = frozenset(
    {
        "outro", "outra", "outros", "outras",
        "anterior", "ontem",
        "primeiro", "primeira", "primeiros", "primeiras",
        "segundo", "segunda", "segundos", "segundas",
    }
)
_ES_OWNERSHIP_AFFIRM = frozenset({"mio", "mia", "mios", "mias"})
_PT_OWNERSHIP_AFFIRM = frozenset({"meu", "minha", "meus", "minhas"})
_ES_SELF_CORRECTION_COPULA = frozenset({"soy", "fui", "era"})
_PT_SELF_CORRECTION_COPULA = frozenset({"sou", "fui", "era"})


@dataclass(frozen=True)
class _B3RetractionCorrection:
    axis: str
    clause_index: int
    token_start: int
    token_end: int
    activity_token_span: tuple[int, int] | None
    has_activity_anaphor: bool
    has_distinguishing_referent: bool
    provenance: str


def _b3_reported_prior_belief_domains(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[ScopeDomain, ...]:
    """Recognize the frozen R7 past-belief frames as local nonassertive scope."""

    frames = (
        _ES_REPORTED_PRIOR_BELIEF_FRAMES
        if language == "es"
        else _PT_REPORTED_PRIOR_BELIEF_FRAMES
    )
    domains: list[ScopeDomain] = []
    words = [token.normalized for token in analysis.tokens]

    for index in range(clause.token_start, clause.token_end):
        for frame in frames:
            end = index + len(frame)
            if end > clause.token_end:
                continue
            if tuple(words[index:end]) != frame:
                continue
            if (
                language == "es"
                and frame[0] in {"pense", "crei"}
                and not analysis.tokens[index].had_acute
            ):
                continue
            domains.append(
                ScopeDomain(
                    mode=PropositionMode.REPORTED_PRIOR_BELIEF,
                    token_start=index,
                    token_end=_b3_domain_end(analysis, clause, index),
                    provenance=(
                        "R7:reported_prior_belief:"
                        + "_".join(frame)
                    ),
                )
            )
    return tuple(domains)


def _b3_proposition_axis(
    proposition: PositiveProposition,
) -> str | None:
    if proposition.family is PropositionFamily.OWNERSHIP_DENIAL:
        return "own"
    if proposition.family in {
        PropositionFamily.PERFORMANCE_DENIAL,
        PropositionFamily.ORIGINATION_DENIAL,
    }:
        return "perform"
    if proposition.family is PropositionFamily.AUTHORIZATION_DENIAL:
        return "authorize"
    if (
        proposition.family is PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE
        and "exceeded-authorization" not in proposition.rule
    ):
        return "authorize"
    return None


def _b3_region_has_denial(
    analysis: FoundationAnalysis,
    start: int,
    end: int,
) -> bool:
    return any(
        analysis.tags[index]
        & {
            LexicalTag.NEGATOR,
            LexicalTag.NEG_QUANTIFIER,
            LexicalTag.COORD_NEGATION,
        }
        for index in range(start, end)
    )


def _b3_correction_activity_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    start: int,
    end: int,
) -> tuple[int, int] | None:
    return next(
        (
            span
            for span in _activity_spans(analysis, clause)
            if start <= span[0] < end
        ),
        None,
    )


def _b3_retraction_corrections(
    analysis: FoundationAnalysis,
    language: str,
) -> tuple[_B3RetractionCorrection, ...]:
    """Return bounded affirmative corrections following an explicit contrast."""

    anaphors = (
        _ES_ACTIVITY_ANAPHORS
        if language == "es"
        else _PT_ACTIVITY_ANAPHORS
    )
    distinguishers = (
        _ES_RETRACTION_DISTINGUISHERS
        if language == "es"
        else _PT_RETRACTION_DISTINGUISHERS
    )
    ownership_words = (
        _ES_OWNERSHIP_AFFIRM
        if language == "es"
        else _PT_OWNERSHIP_AFFIRM
    )
    self_copulas = (
        _ES_SELF_CORRECTION_COPULA
        if language == "es"
        else _PT_SELF_CORRECTION_COPULA
    )
    self_pronoun = "yo" if language == "es" else "eu"
    words = [token.normalized for token in analysis.tokens]
    output: list[_B3RetractionCorrection] = []

    for clause in analysis.clauses:
        boundaries = [
            index
            for index in range(clause.token_start, clause.token_end)
            if LexicalTag.CONTRAST in analysis.tags[index]
        ]
        for boundary in boundaries:
            region_start = boundary + 1
            region_end = _b3_domain_end(analysis, clause, boundary)
            if region_start >= region_end:
                continue

            activity_span = _b3_correction_activity_span(
                analysis,
                clause,
                region_start,
                region_end,
            )
            has_anaphor = any(
                words[index] in anaphors
                for index in range(region_start, region_end)
                if activity_span is None or index != activity_span[0]
            )
            has_distinguishing = any(
                words[index] in distinguishers
                for index in range(region_start, region_end)
            )

            for predicate in analysis.predicates:
                if not (
                    region_start
                    <= predicate.token_start
                    < predicate.token_end
                    <= region_end
                ):
                    continue
                if predicate.form.person != 1:
                    continue
                if predicate.form.mood != "indicative":
                    continue
                if predicate.form.tense_aspect in {"future", "conditional"}:
                    continue
                if not _source_accent_selects_predicate(analysis, predicate):
                    continue
                if _b3_region_has_denial(
                    analysis,
                    region_start,
                    predicate.token_end,
                ):
                    continue

                axis: str | None = None
                if predicate.form.family in {
                    PredicateFamily.PERFORM,
                    PredicateFamily.ORIGINATE,
                }:
                    axis = "perform"
                elif predicate.form.family is PredicateFamily.AUTHORIZE:
                    axis = "authorize"
                elif predicate.form.family is PredicateFamily.GIVE_PERMISSION:
                    if any(
                        LexicalTag.AUTH_NOUN in analysis.tags[index]
                        for index in range(
                            predicate.token_end,
                            region_end,
                        )
                    ):
                        axis = "authorize"

                if axis is None:
                    continue
                output.append(
                    _B3RetractionCorrection(
                        axis=axis,
                        clause_index=clause.index,
                        token_start=region_start,
                        token_end=region_end,
                        activity_token_span=activity_span,
                        has_activity_anaphor=has_anaphor,
                        has_distinguishing_referent=has_distinguishing,
                        provenance=(
                            f"M7:retraction:{axis}:"
                            f"{analysis.tokens[boundary].normalized}"
                        ),
                    )
                )

            for copula_index in range(region_start, region_end):
                if words[copula_index] not in (
                    _ES_COPULA if language == "es" else _PT_COPULA
                ):
                    continue
                ownership_index = next(
                    (
                        index
                        for index in range(
                            copula_index + 1,
                            min(region_end, copula_index + 4),
                        )
                        if words[index] in ownership_words
                    ),
                    None,
                )
                if ownership_index is None:
                    continue
                if _b3_region_has_denial(
                    analysis,
                    region_start,
                    ownership_index + 1,
                ):
                    continue
                output.append(
                    _B3RetractionCorrection(
                        axis="own",
                        clause_index=clause.index,
                        token_start=region_start,
                        token_end=region_end,
                        activity_token_span=activity_span,
                        has_activity_anaphor=has_anaphor,
                        has_distinguishing_referent=has_distinguishing,
                        provenance=(
                            "M7:retraction:own:"
                            f"{analysis.tokens[boundary].normalized}"
                        ),
                    )
                )
                break

            for copula_index in range(region_start, region_end):
                if words[copula_index] not in self_copulas:
                    continue
                window_start = max(region_start, copula_index - 2)
                window_end = min(region_end, copula_index + 3)
                if not any(
                    words[index] == self_pronoun
                    for index in range(window_start, window_end)
                ):
                    continue
                if _b3_region_has_denial(
                    analysis,
                    region_start,
                    window_end,
                ):
                    continue
                output.append(
                    _B3RetractionCorrection(
                        axis="perform",
                        clause_index=clause.index,
                        token_start=region_start,
                        token_end=region_end,
                        activity_token_span=activity_span,
                        has_activity_anaphor=has_anaphor,
                        has_distinguishing_referent=has_distinguishing,
                        provenance=(
                            "M7:retraction:perform:"
                            f"{analysis.tokens[boundary].normalized}"
                        ),
                    )
                )
                break

    unique: dict[
        tuple[str, int, int, int, tuple[int, int] | None],
        _B3RetractionCorrection,
    ] = {}
    for correction in output:
        key = (
            correction.axis,
            correction.clause_index,
            correction.token_start,
            correction.token_end,
            correction.activity_token_span,
        )
        unique[key] = correction
    return tuple(unique.values())


def _b3_txid_key(
    analysis: FoundationAnalysis,
    span: tuple[int, int] | None,
) -> tuple[str | None, str | None] | None:
    if span is None:
        return None
    token = analysis.tokens[span[0]]
    if not token.is_txid:
        return None
    return token.txid_language, token.txid_digits


def _b3_retraction_referent_matches(
    analysis: FoundationAnalysis,
    proposition: PositiveProposition,
    correction: _B3RetractionCorrection,
) -> bool:
    if correction.has_distinguishing_referent:
        return False

    prior_span = proposition.activity_token_span
    correction_span = correction.activity_token_span
    prior_txid = _b3_txid_key(analysis, prior_span)
    correction_txid = _b3_txid_key(analysis, correction_span)

    if correction_txid is not None:
        return prior_txid == correction_txid

    if correction_span is not None:
        if prior_span is None:
            return False
        if prior_txid is not None:
            return False
        return (
            analysis.tokens[prior_span[0]].normalized
            == analysis.tokens[correction_span[0]].normalized
        )

    if correction.has_activity_anaphor:
        return prior_span is not None or proposition.activity_ref == "topic_transaction"

    return False


def _b3_apply_retractions(
    analysis: FoundationAnalysis,
    propositions: tuple[PositiveProposition, ...],
    language: str,
) -> tuple[PositiveProposition, ...]:
    """Apply M7 only to the latest prior assertive proposition with same identity."""

    resolved = list(propositions)
    for correction in _b3_retraction_corrections(analysis, language):
        candidate_indices = [
            index
            for index, proposition in enumerate(resolved)
            if proposition.mode == PropositionMode.ASSERTIVE.value
            and proposition.token_end <= correction.token_start
            and 0
            <= correction.clause_index - proposition.clause_index
            <= 1
            and _b3_proposition_axis(proposition) == correction.axis
        ]
        if not candidate_indices:
            continue

        matched_indices = [
            index
            for index in candidate_indices
            if _b3_retraction_referent_matches(
                analysis,
                resolved[index],
                correction,
            )
        ]

        if (
            not matched_indices
            and correction.activity_token_span is None
            and not correction.has_activity_anaphor
            and not correction.has_distinguishing_referent
            and len(candidate_indices) == 1
        ):
            matched_indices = candidate_indices

        if not matched_indices:
            continue

        selected_index = max(
            matched_indices,
            key=lambda index: resolved[index].token_end,
        )
        selected = resolved[selected_index]
        resolved[selected_index] = replace(
            selected,
            mode=PropositionMode.RETRACTED.value,
            retraction_provenance=(correction.provenance,),
        )

    return tuple(resolved)


def _b3_operator_domains_for_clause(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[ScopeDomain, ...]:
    domains: list[ScopeDomain] = []

    for index in range(clause.token_start, clause.token_end):
        tags = analysis.tags[index]
        if LexicalTag.CONDITIONAL in tags:
            domains.append(
                ScopeDomain(
                    mode=PropositionMode.HYPOTHETICAL,
                    token_start=index,
                    token_end=_b3_domain_end(analysis, clause, index),
                    provenance=f"M2:conditional:{analysis.tokens[index].normalized}",
                )
            )
        if LexicalTag.UNCERTAINTY in tags:
            domains.append(
                ScopeDomain(
                    mode=PropositionMode.UNCERTAIN,
                    token_start=index,
                    token_end=_b3_domain_end(analysis, clause, index),
                    provenance=f"M3:uncertainty:{analysis.tokens[index].normalized}",
                )
            )

    domains.extend(
        _b3_reported_prior_belief_domains(
            analysis,
            clause,
            language,
        )
    )

    question = _b3_question_domain(analysis, clause)
    if question is not None:
        domains.append(question)

    information_request = _b3_information_request_domain(
        analysis,
        clause,
        question,
    )
    if information_request is not None:
        domains.append(information_request)

    domains.extend(
        _b3_authorized_third_party_domains(
            analysis,
            clause,
            language,
            tuple(domains),
        )
    )

    return tuple(domains)


def _b3_domain_overlaps_proposition(
    domain: ScopeDomain,
    proposition: PositiveProposition,
) -> bool:
    return (
        proposition.token_start < domain.token_end
        and proposition.token_end > domain.token_start
    )


def _b3_recovered_nonassertive_third_party_fraud_candidates(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    domains: tuple[ScopeDomain, ...],
) -> tuple[PositiveProposition, ...]:
    """Recover audit-only attributive fraud candidates suppressed by B2 target typing.

    B2 intentionally refuses to assert an activity as customer-anchored when an
    explicit third-person relational phrase is attached to it. B3 still needs a
    proposition-shaped candidate to classify a bounded authorization grant or
    explicit question as nonassertive. This helper is therefore used only by the
    B3 audit/debug resolver; production B2 proposition generation is unchanged.
    """

    eligible_domains = tuple(
        domain
        for domain in domains
        if domain.mode in {
            PropositionMode.AUTHORIZED_THIRD_PARTY,
            PropositionMode.QUESTIONED,
        }
    )
    if not eligible_domains:
        return ()

    actor_spans = _known_actor_spans(analysis, clause, language)
    if not actor_spans:
        return ()

    authorization_predicates = tuple(
        predicate
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, clause)
        and predicate.form.family in {
            PredicateFamily.AUTHORIZE,
            PredicateFamily.GIVE_PERMISSION,
        }
        and predicate.form.person == 1
        and predicate.form.mood == "indicative"
        and predicate.form.tense_aspect not in {"future", "conditional"}
        and _source_accent_selects_predicate(analysis, predicate)
        and not _predicate_has_denial(
            analysis,
            clause,
            predicate,
            language,
        )
    )
    if not authorization_predicates:
        return ()

    fraud_adjectives = (
        _ES_FRAUD_ADJECTIVES
        if language == "es"
        else _PT_FRAUD_ADJECTIVES
    )
    output: list[PositiveProposition] = []

    for activity_span in _activity_spans(analysis, clause):
        marker_index = activity_span[1]
        if marker_index >= clause.token_end:
            continue
        marker_word = analysis.tokens[marker_index].normalized
        if marker_word not in fraud_adjectives:
            continue
        if _span_has_bound_denial(
            analysis,
            clause,
            marker_index,
            marker_index + 1,
            language,
        ):
            continue
        if not _fraud_adjective_agrees(
            analysis.tokens[activity_span[0]].normalized,
            marker_word,
            language,
        ):
            continue

        # Recover only the exact B2 target-typing exclusion that motivated M6:
        # an explicit third-person relational phrase near the activity.
        if not _explicit_third_person_activity_possession(
            analysis,
            clause,
            activity_span,
            language,
        ):
            continue
        if _customer_anchored_activity(
            analysis,
            clause,
            activity_span,
            language,
        ):
            continue

        for predicate in authorization_predicates:
            if predicate.token_end > activity_span[0]:
                continue
            if not any(
                predicate.token_end <= actor_start < activity_span[0]
                for actor_start, _ in actor_spans
            ):
                continue

            candidate = _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.FRAUD_CHARACTERIZATION,
                rule="P6-attributive",
                language=language,
                evidence_spans=(
                    activity_span,
                    (marker_index, marker_index + 1),
                ),
                activity_span=activity_span,
                predicate=None,
            )
            if not any(
                _b3_domain_overlaps_proposition(domain, candidate)
                for domain in eligible_domains
            ):
                continue

            output.append(candidate)
            break

    return tuple(output)


def resolve_positive_propositions(
    text: str,
    language: str,
) -> tuple[PositiveProposition, ...]:
    """Apply the first bounded RF1H-B3 local-mode scaffold.

    This audit/debug API currently implements explicit conditional,
    lexical-uncertainty, bounded security/prevention information-request,
    authorized-third-party, question, reported-prior-belief, and message-level
    same-proposition retraction handling. M5 remains pre-filtered by B2 target
    typing. Production boolean behavior is not switched by this function.
    """

    analysis = analyze_foundation(text, language)
    base_unresolved = build_positive_propositions(text, language)
    clause_by_index = {clause.index: clause for clause in analysis.clauses}
    domains_by_clause = {
        clause.index: _b3_operator_domains_for_clause(
            analysis,
            clause,
            language,
        )
        for clause in analysis.clauses
    }
    recovered = tuple(
        proposition
        for clause in analysis.clauses
        for proposition in _b3_recovered_nonassertive_third_party_fraud_candidates(
            analysis,
            clause,
            language,
            domains_by_clause.get(clause.index, ()),
        )
    )
    unresolved = (*base_unresolved, *recovered)

    resolved: list[PositiveProposition] = []
    for proposition in unresolved:
        clause = clause_by_index.get(proposition.clause_index)
        if clause is None:
            resolved.append(proposition)
            continue

        overlapping = tuple(
            domain
            for domain in domains_by_clause.get(clause.index, ())
            if _b3_domain_overlaps_proposition(domain, proposition)
        )
        if not overlapping:
            resolved.append(
                replace(
                    proposition,
                    mode=PropositionMode.ASSERTIVE.value,
                    exclusion_provenance=(),
                )
            )
            continue

        selected_mode = min(
            (domain.mode for domain in overlapping),
            key=lambda mode: _B3_MODE_PRECEDENCE.get(mode, 50),
        )
        provenance = tuple(
            domain.provenance
            for domain in overlapping
            if domain.mode is selected_mode
        )
        resolved.append(
            replace(
                proposition,
                mode=selected_mode.value,
                exclusion_provenance=provenance,
            )
        )

    return _b3_apply_retractions(
        analysis,
        tuple(resolved),
        language,
    )


def dump_resolved_propositions(
    text: str,
    language: str,
) -> tuple[dict[str, object], ...]:
    """Return a compact B3 audit view without changing production routing."""

    propositions = resolve_positive_propositions(text, language)
    return tuple(
        {
            "family": proposition.family.value,
            "rule": proposition.rule,
            "clause_index": proposition.clause_index,
            "activity_ref": proposition.activity_ref,
            "source": text[proposition.source_start : proposition.source_end],
            "mode": proposition.mode,
            "exclusion_provenance": proposition.exclusion_provenance,
            "retraction_provenance": proposition.retraction_provenance,
        }
        for proposition in propositions
    )


def dump_positive_propositions(
    text: str,
    language: str,
) -> tuple[dict[str, object], ...]:
    """Return a compact source-grounded debug view for proposition-level tests."""

    propositions = build_positive_propositions(text, language)
    return tuple(
        {
            "family": proposition.family.value,
            "rule": proposition.rule,
            "clause_index": proposition.clause_index,
            "activity_ref": proposition.activity_ref,
            "source": text[proposition.source_start : proposition.source_end],
            "counter_evidence": tuple(
                atom.kind.value for atom in proposition.counter_evidence
            ),
            "mode": proposition.mode,
        }
        for proposition in propositions
    )
