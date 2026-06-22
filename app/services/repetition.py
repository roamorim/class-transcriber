import re
from collections import Counter
from dataclasses import dataclass

_WORD_RE = re.compile(r"\w+")


@dataclass
class RepetitionReport:
    fraction: float  # share of the text (in words) sitting inside repeated blocks
    top_count: int  # how many times the most repeated block occurs
    sample: str  # the most repeated block, for logging/diagnostics


def analyze_repetition(
    text: str, ngram_size: int = 12, min_repeats: int = 4, fraction_threshold: float = 0.15
) -> RepetitionReport | None:
    """Detect the kind of degenerate repetition loop seen in some Gemini transcriptions:
    the same multi-word block repeated dozens/hundreds of times in a row.

    Splits the text into non-overlapping word blocks and flags it when a sizeable
    share of the document is made of blocks that repeat at least `min_repeats` times.
    Short stock phrases ("¿cierto?", "¿sí?") are below `ngram_size` words and won't
    trigger this on their own.
    """
    words = _WORD_RE.findall(text.lower())
    if len(words) < ngram_size * min_repeats:
        return None

    shingles = [
        tuple(words[i : i + ngram_size]) for i in range(0, len(words) - ngram_size + 1, ngram_size)
    ]
    counts = Counter(shingles)
    repeated = {shingle: count for shingle, count in counts.items() if count >= min_repeats}
    if not repeated:
        return None

    words_in_repeats = sum(ngram_size * count for count in repeated.values())
    fraction = words_in_repeats / len(words)
    if fraction < fraction_threshold:
        return None

    top_shingle, top_count = counts.most_common(1)[0]
    return RepetitionReport(fraction=fraction, top_count=top_count, sample=" ".join(top_shingle))
