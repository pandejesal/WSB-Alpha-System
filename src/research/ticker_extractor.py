import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag

# Common financial false positives requested in Phase 2
BLACKLIST = {
    'CEO', 'CFO', 'USA', 'AI', 'DD', 'FOMO', 'EDIT', 'ATH', 'USD', 'EST',
    'PM', 'AM', 'GDP', 'CPI', 'SEC', 'FED', 'RH', 'WSB', 'YOLO', 'FD',
    'LLM', 'GPT', 'PUT', 'CALL', 'OR', 'IT', 'IS', 'TO', 'BE', 'ON', 'IN', 'AT', 'BY', 'HE', 'SHE', 'WE', 'THEY', 'THE', 'A', 'AN'
}

def extract_tickers(text: str) -> list[str]:
    """
    Extract stock tickers from text using regex and NLTK POS-tagging.
    Enforces strict 2-to-5 uppercase character regex and rejects false positives.
    """
    if not isinstance(text, str):
        return []

    # Enforce strict 2-to-5 uppercase character regex
    # Added negative lookbehinds/lookaheads to prevent matching inside URLs or normal words
    raw_matches = set(re.findall(r'\b[A-Z]{2,5}\b', text))

    # Strip optional '$' prefix
    potential_tickers = {t.replace('$', '') for t in raw_matches}

    # Filter against blacklist
    potential_tickers = potential_tickers - BLACKLIST

    valid_tickers = []

    # Ensure NLTK resources are available (usually downloaded at startup, but just in case)
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger', quiet=True)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)

    # Use NLTK POS-tagging to filter out common dictionary words
    # PRON (PRP, PRP$), PREP (IN), CONJ (CC)
    tokens = word_tokenize(text)
    tagged_tokens = pos_tag(tokens)

    # Create a mapping of token to tags (a word can appear multiple times, we just want to know if it's ALWAYS a certain tag)
    tag_map = {}
    for word, tag in tagged_tokens:
        # Ignore case when matching tags since our tickers are uppercase but might be used normally
        # Actually our raw_matches are strictly uppercase.
        if word in tag_map:
            tag_map[word].add(tag)
        else:
            tag_map[word] = {tag}

    for ticker in potential_tickers:
        # Check if the ticker exists in the text as an uppercase word
        # If it's in the tag map, let's check its tags.
        tags = tag_map.get(ticker, set())

        # Reject if the word is ONLY tagged as Pronoun, Preposition, or Conjunction
        # IN: Preposition/subordinating conjunction
        # CC: Coordinating conjunction
        # PRP, PRP$: Pronouns
        reject_tags = {'IN', 'CC', 'PRP', 'PRP$'}

        if tags and tags.issubset(reject_tags):
            continue

        valid_tickers.append(ticker)

    return sorted(list(valid_tickers))
