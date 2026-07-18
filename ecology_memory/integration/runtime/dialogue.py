"""Deterministic conversational routing shared by the Hermes bridge and its tests."""
import re


SITE_CHOICES = {
    "1": "What land cover class is at the EBTL restoration site?",
    "2": "What is in the documented EBTL wildlife inventory?",
    "3": "What is the historical fire exposure at Elephants by the Lake from 2020 to 2025?",
    "4": "How has restoration progressed over time at EBTL?",
}

TOPICS = (
    (re.compile(r"\b(?:fire|wildfire|burn(?:ing|ed)?|degradation risk)\b", re.I), SITE_CHOICES["3"]),
    (re.compile(r"\b(?:land[ -]?cover|vegetation(?: cover)?)\b", re.I), SITE_CHOICES["1"]),
    (re.compile(r"\b(?:restoration|recovery|greenness|ndvi)\b", re.I), SITE_CHOICES["4"]),
    (re.compile(r"\b(?:wildlife|fauna|animals?|animal sightings?)\b", re.I), SITE_CHOICES["2"]),
)


def canonical_site_topic(message):
    """Return a scoped site question for a stated menu topic, otherwise ``None``."""
    text = " ".join(str(message).split()).strip()
    if text in SITE_CHOICES:
        return SITE_CHOICES[text]
    for pattern, question in TOPICS:
        if pattern.search(text):
            return question
    return None


def is_broad_site_opening(message):
    """True only for a genuinely unscoped site opening.

    A phrase such as ``tell me about fire at the site`` is already scoped and must never be sent
    back through the generic four-way clarification.
    """
    text = " ".join(str(message).lower().split()).strip(" ?.!")
    if canonical_site_topic(text):
        return False
    site = r"(?:ebtl|elephants by the lake|the site|this site|our site|here)"
    return bool(re.fullmatch(
        rf"(?:(?:tell me about|describe|give me an overview of|overview of)\s+{site}|"
        rf"what(?:'s| is)\s+(?:at\s+)?{site})",
        text,
    ))
