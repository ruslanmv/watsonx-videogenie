import re
def split_sentences(text: str):
    """Split on punctuation followed by whitespace. Replace if you prefer spaCy."""
    return [s for s in re.split(r"(?<=[.!?]) +", text.strip()) if s]
