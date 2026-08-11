import re

import nltk
from nltk.corpus import words

from src.research.ticker_extractor import extract_tickers

try:
    _ = words.words()
except LookupError:
    nltk.download('words', quiet=True)
ENGLISH_WORDS = set(words.words())
COMMON_FALSE_POSITIVES = {'A', 'I', 'ON', 'OR', 'IT', 'AM', 'PM', 'HE', 'SHE', 'WE', 'THE', 'AND', 'FOR', 'TO'}

def extract_tickers(text: str) -> list:  # noqa: F811 - redefinition of unused legacy function or duplicate import fallback
    if not text:
        return []
    matches = re.findall(r'\$?[A-Z]{2,5}', text)
    valid_tickers = []
    for match in matches:
        if match.startswith('$'):
            valid_tickers.append(match[1:])
            continue
        if match in COMMON_FALSE_POSITIVES or match.lower() in ENGLISH_WORDS:
            continue
        valid_tickers.append(match)
    return list(set(valid_tickers))
