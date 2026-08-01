import re
import nltk
from nltk.corpus import words

# Ensure word list is downloaded
try:
    _ = words.words()
except LookupError:
    nltk.download('words', quiet=True)

ENGLISH_WORDS = set(words.words())
# Common abbreviations or short words that are also tickers
COMMON_FALSE_POSITIVES = {'A', 'I', 'ON', 'OR', 'IT', 'AM', 'PM', 'HE', 'SHE', 'WE', 'THE', 'AND', 'FOR', 'TO'}

def extract_tickers(text: str) -> list:
    """
    Extracts uppercase stock tickers from text (e.g., $AAPL or AAPL).
    Filters out common dictionary words unless prefixed with $.
    """
    if not text:
        return []

    # Match words like $AAPL or AAPL (2 to 5 uppercase letters)
    pattern = r'\$?[A-Z]{2,5}'
    matches = re.findall(pattern, text)

    valid_tickers = []
    for match in matches:
        # If it has a $ prefix, it's definitely a ticker intent
        if match.startswith('$'):
            valid_tickers.append(match[1:])
            continue

        # Otherwise, check if it's a false positive dictionary word
        if match in COMMON_FALSE_POSITIVES or match.lower() in ENGLISH_WORDS:
            continue

        valid_tickers.append(match)

    return list(set(valid_tickers))
