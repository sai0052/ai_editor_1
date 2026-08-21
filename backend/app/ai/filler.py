from __future__ import annotations

import re

from app.ai.base import FillerHit, FillerWordDetector, Transcript

# Standalone fillers — never remove content words that happen to contain these substrings.
FILLER_WORDS = {
    "um",
    "uh",
    "uhm",
    "hmm",
    "hm",
    "er",
    "ah",
    "eh",
    "mmm",
}

# Phrase fillers only when they appear as discourse markers (heuristic).
FILLER_PHRASES = {
    "you know",
    "i mean",
    "kind of",
    "sort of",
}


class HeuristicFillerDetector(FillerWordDetector):
    """
    Detect filler words from a transcript.
    Conservative: marks ambiguous cases (e.g. 'like', 'basically') as NOT safe_to_remove
    so the pipeline never blindly deletes meaning-bearing words.
    """

    AMBIGUOUS = {"like", "basically", "actually", "literally", "right", "so"}

    def detect(self, transcript: Transcript) -> list[FillerHit]:
        hits: list[FillerHit] = []
        for seg in transcript.segments:
            if seg.words:
                for w in seg.words:
                    token = re.sub(r"[^a-zA-Z']", "", w.word).lower()
                    if token in FILLER_WORDS:
                        hits.append(
                            FillerHit(word=w.word, start=w.start, end=w.end, safe_to_remove=True, reason="pure_filler")
                        )
                    elif token in self.AMBIGUOUS:
                        hits.append(
                            FillerHit(
                                word=w.word,
                                start=w.start,
                                end=w.end,
                                safe_to_remove=False,
                                reason="ambiguous_needs_review",
                            )
                        )
            else:
                # Fallback: sentence-level scan without precise cuts
                lower = seg.text.lower()
                for phrase in FILLER_PHRASES:
                    if phrase in lower:
                        hits.append(
                            FillerHit(
                                word=phrase,
                                start=seg.start,
                                end=seg.end,
                                safe_to_remove=False,
                                reason="phrase_without_word_timings",
                            )
                        )
        return hits
