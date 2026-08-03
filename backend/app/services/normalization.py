"""Deterministic normalization for names, addresses, dates and organizations.

All functions preserve the original value and return a structured, normalized
representation. These run without any network or LLM access so they work in the
deterministic (no OpenAI key) mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from datetime import datetime as _datetime

from dateutil import parser as date_parser

# --------------------------------------------------------------------------- #
# Names
# --------------------------------------------------------------------------- #

NAME_PREFIXES = {"mr", "mrs", "ms", "miss", "dr", "prof", "hon", "rev", "sir", "judge"}
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "phd", "md", "esq", "esquire"}


@dataclass
class NormalizedName:
    original: str
    normalized: str
    first: str | None = None
    middle: str | None = None
    last: str | None = None
    prefix: str | None = None
    suffix: str | None = None


def _clean_token(token: str) -> str:
    return re.sub(r"[.,]", "", token).strip()


def normalize_name(raw: str) -> NormalizedName:
    original = (raw or "").strip()
    if not original:
        return NormalizedName(original="", normalized="")

    working = original
    # Handle "Last, First Middle" ordering.
    if "," in working and len(working.split(",")) == 2:
        last_part, rest = working.split(",", 1)
        working = f"{rest.strip()} {last_part.strip()}"

    tokens = [_clean_token(t) for t in working.split() if _clean_token(t)]
    prefix = suffix = None
    if tokens and tokens[0].lower() in NAME_PREFIXES:
        prefix = tokens.pop(0)
    if tokens and tokens[-1].lower() in NAME_SUFFIXES:
        suffix = tokens.pop(-1)

    first = middle = last = None
    if len(tokens) == 1:
        last = tokens[0]
    elif len(tokens) == 2:
        first, last = tokens
    elif len(tokens) >= 3:
        first = tokens[0]
        last = tokens[-1]
        middle = " ".join(tokens[1:-1])

    core = " ".join(t for t in [first, middle, last] if t)
    normalized = re.sub(r"\s+", " ", core).strip().lower()
    return NormalizedName(
        original=original,
        normalized=normalized,
        first=(first or "").lower() or None,
        middle=(middle or "").lower() or None,
        last=(last or "").lower() or None,
        prefix=prefix,
        suffix=suffix,
    )


# --------------------------------------------------------------------------- #
# Addresses
# --------------------------------------------------------------------------- #

STREET_ABBREV = {
    "street": "st",
    "avenue": "ave",
    "boulevard": "blvd",
    "drive": "dr",
    "road": "rd",
    "lane": "ln",
    "court": "ct",
    "place": "pl",
    "terrace": "ter",
    "circle": "cir",
    "highway": "hwy",
    "parkway": "pkwy",
    "apartment": "apt",
    "suite": "ste",
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
}

STATE_ABBREV = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

_ZIP_RE = re.compile(r"\b(\d{5})(?:-(\d{4}))?\b")
_STATE_TOKEN_RE = re.compile(r"\b([A-Z]{2})\b")


@dataclass
class NormalizedAddress:
    original: str
    normalized: str
    street: str | None = None
    unit: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    components: dict = field(default_factory=dict)


def _normalize_state(token: str | None) -> str | None:
    if not token:
        return None
    t = token.strip()
    if len(t) == 2 and t.isalpha():
        return t.upper()
    return STATE_ABBREV.get(t.lower())


def normalize_address(raw: str) -> NormalizedAddress:
    original = (raw or "").strip()
    if not original:
        return NormalizedAddress(original="", normalized="")

    components: dict = {}
    # Try usaddress if available for richer parsing; fall back to regex.
    try:  # pragma: no cover - optional dependency
        import usaddress

        tagged, _ = usaddress.tag(original)
        components = dict(tagged)
    except Exception:
        components = {}

    zip_code = None
    zip_match = _ZIP_RE.search(original)
    if zip_match:
        zip_code = zip_match.group(1)
        if zip_match.group(2):
            zip_code = f"{zip_code}-{zip_match.group(2)}"

    state = _normalize_state(components.get("StateName"))
    if not state:
        # Look for a full state name or 2-letter code.
        low = original.lower()
        for name, abbr in STATE_ABBREV.items():
            if re.search(rf"\b{name}\b", low):
                state = abbr
                break
        if not state:
            for m in _STATE_TOKEN_RE.finditer(original):
                if m.group(1) in set(STATE_ABBREV.values()):
                    state = m.group(1)
                    break

    city = components.get("PlaceName")
    unit = components.get("OccupancyIdentifier")

    # Normalize the free-text form: lowercase, expand->abbreviate, squeeze space.
    words = re.split(r"[\s,]+", original.lower())
    norm_words = [STREET_ABBREV.get(re.sub(r"[.,]", "", w), re.sub(r"[.,]", "", w)) for w in words]
    normalized = re.sub(r"\s+", " ", " ".join(w for w in norm_words if w)).strip()

    street = components.get("AddressNumber", "")
    if street and components.get("StreetName"):
        street = f"{components.get('AddressNumber','')} {components.get('StreetName','')}".strip()
    else:
        street = None

    return NormalizedAddress(
        original=original,
        normalized=normalized,
        street=street,
        unit=unit,
        city=city.title() if city else None,
        state=state,
        zip_code=zip_code,
        components=components,
    )


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #

@dataclass
class NormalizedDate:
    original: str
    iso: str | None
    precision: str  # exact|partial|range|unknown
    date_value: date | None = None


def normalize_date(raw: str | None) -> NormalizedDate:
    original = (raw or "").strip()
    if not original:
        return NormalizedDate(original="", iso=None, precision="unknown")

    # Date range like "2020-2021" or "Jan 2020 - Mar 2020".
    if re.search(r"\bto\b|–|—|\s-\s", original):
        return NormalizedDate(original=original, iso=None, precision="range")

    # Year only.
    if re.fullmatch(r"(19|20)\d{2}", original):
        return NormalizedDate(original=original, iso=f"{original}-01-01", precision="partial")

    try:
        parsed = date_parser.parse(original, default=_datetime(2000, 1, 1))
        return NormalizedDate(
            original=original,
            iso=parsed.date().isoformat(),
            precision="exact",
            date_value=parsed.date(),
        )
    except (ValueError, OverflowError):
        return NormalizedDate(original=original, iso=None, precision="unknown")


# --------------------------------------------------------------------------- #
# Organizations
# --------------------------------------------------------------------------- #

ORG_SUFFIXES = {
    "incorporated": "inc", "corporation": "corp", "company": "co",
    "limited": "ltd", "llc": "llc", "l.l.c": "llc", "lp": "lp",
    "llp": "llp", "co": "co", "inc": "inc", "corp": "corp",
}


@dataclass
class NormalizedOrg:
    original: str
    normalized: str


def normalize_org(raw: str) -> NormalizedOrg:
    original = (raw or "").strip()
    if not original:
        return NormalizedOrg(original="", normalized="")
    low = re.sub(r"[.,]", "", original.lower())
    words = [ORG_SUFFIXES.get(w, w) for w in low.split()]
    normalized = re.sub(r"\s+", " ", " ".join(words)).strip()
    return NormalizedOrg(original=original, normalized=normalized)
