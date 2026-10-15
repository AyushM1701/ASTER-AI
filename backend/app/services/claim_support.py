"""Sentence-level claim support verification for generated answers.

Not exact-string matching: each generated sentence is checked against windows
of its cited passages with an NLI cross-encoder (entailment vs contradiction),
plus deterministic gates that small models frequently fail:

* numbers/units/decimals in the sentence must occur in the supporting passage;
* negation must not be lost or invented relative to the best-matching window;
* sentences with medical content but no support are removed, not shown.

When the cited passage does not entail a sentence but another retrieved
passage does, the citation is corrected (re-attributed) and recorded.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

STOP = set("""a an and are as at be been being by can could do does for from had has have how i if in into is it its
may might more most must not of on or our over should so some such than that the their them then there these they
this those to under up was we were what when where which while who why will with within would you your also often
usually generally typically called known include includes including other one two both each many much very well""".split())
NEGATION = re.compile(r"\b(?:not|no|never|none|neither|nor|without|cannot|can't|doesn't|don't|isn't|aren't|absent|rarely)\b", re.I)
NUMBER = re.compile(r"(?<![A-Za-z])(\d+(?:[.,]\d+)?)(?:\s*(%|mg|mcg|µg|ml|mL|g|kg|mm|cm|mmol|iu|IU|units?|hours?|days?|weeks?|months?|years?))?")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[\"'])")


def content_terms(text):
    words = re.findall(r"[a-z][a-z0-9\-]+", text.casefold())
    return {stem(w) for w in words if w not in STOP and len(w) > 2}


def stem(word):
    for suffix in ("ations", "ation", "ments", "ment", "ness", "ities", "ity", "ings", "ing", "ies", "ied", "es", "ed", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


CODED_TERM = re.compile(r"\b[A-Za-z]{1,6}-?\d+[A-Za-z0-9]*\b")


def coded_terms(text):
    """Alphanumeric identifiers (Ki-67, p53, PTCH1, CD34, IgE) that must match exactly."""
    return {t.casefold().replace("-", "") for t in CODED_TERM.findall(text)}


def numbers(text):
    found = set()
    for value, unit in NUMBER.findall(text):
        value = value.replace(",", ".")
        if re.fullmatch(r"(19|20)\d\d", value) and not unit:
            found.add(value)  # years still need support
            continue
        found.add(value)
    return found


def windows(text, size=3, max_chars=900):
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]
    if len(sentences) <= size:
        return [text[:max_chars * 2]]
    out = []
    for start in range(0, len(sentences), max(1, size - 1)):
        chunk = " ".join(sentences[start:start + size])
        out.append(chunk[:max_chars * 2])
        if start + size >= len(sentences):
            break
    return out


@dataclass
class Support:
    status: str  # supported | reattributed | unsupported | contradicted | numeric_unsupported | connective
    citation_ids: list = field(default_factory=list)
    entailment: float = 0.0
    contradiction: float = 0.0
    lexical: float = 0.0
    method: str = "nli"
    note: str = ""


class NLIModel:
    """ONNX DeBERTa-v3 cross-encoder (labels: contradiction, entailment, neutral)."""

    def __init__(self, model_dir):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_dir = Path(model_dir)
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=384, strategy="only_first")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        self.session = ort.InferenceSession(str(model_dir / "onnx" / "model_quint8_avx2.onnx"), options,
                                            providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}

    def scores(self, pairs, batch=24):
        """Return array (n, 3) of probabilities [contradiction, entailment, neutral]."""
        out = []
        for start in range(0, len(pairs), batch):
            encoded = self.tokenizer.encode_batch(pairs[start:start + batch])
            length = max(len(e.ids) for e in encoded)
            ids = np.array([e.ids + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
            mask = np.array([e.attention_mask + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.array([e.type_ids + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
            logits = self.session.run(None, feed)[0]
            logits = logits - logits.max(axis=1, keepdims=True)
            probs = np.exp(logits)
            out.append(probs / probs.sum(axis=1, keepdims=True))
        return np.concatenate(out) if out else np.zeros((0, 3))


class ClaimVerifier:
    ENTAIL = 0.5
    CONTRADICT = 0.8

    def __init__(self, model_dir=None, nli=None, entities=()):
        self.nli = nli
        self.error = None
        self.set_entities(entities)
        if self.nli is None and model_dir:
            try:
                self.nli = NLIModel(model_dir)
            except Exception as exc:  # missing model degrades to lexical-only, which is stricter
                self.error = f"NLI unavailable: {type(exc).__name__}"

    def set_entities(self, entities):
        """Drug names for the substitution check (longest first so "insulin glargine" beats "insulin")."""
        self.entities = sorted({" ".join(e.casefold().split()) for e in entities if e and e.strip()}, key=len, reverse=True)

    def _lexical(self, sentence, passage):
        terms = content_terms(sentence)
        if not terms:
            return 1.0
        return len(terms & content_terms(passage)) / len(terms)

    def _mentions(self, text):
        found, folded = [], text.casefold()
        for name in self.entities:
            if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", folded) and not any(name in f for f in found):
                found.append(name)
        return found

    def substituted(self, sentence, window, entailment):
        """True when the evidence is not about the drug the claim names (entity substitution).

        NLI models tolerate swapped names: "Avoid ibuprofen in children with viral illness (Reye's)"
        scored 0.72 against a window saying this only of aspirin (ibuprofen appeared in an unrelated
        sentence). So (1) every drug the claim names must appear in the supporting window, (2) the
        claim must be entailed by a span starting at a sentence that names that drug (that sentence
        plus the next, so "It can cause…" still counts), and (3) when the window names other drugs,
        the claim re-tested with each swapped in must not entail as strongly."""
        if not self.entities:
            return False
        claimed = self._mentions(sentence)
        if not claimed:
            return False
        present = self._mentions(window)
        if any(not any(drug == p or drug in p for p in present) for drug in claimed):
            return True
        if self.nli is None:
            return False
        parts = [s.strip() for s in SENTENCE_SPLIT.split(window) if s.strip()]
        for drug in claimed:
            spans = [" ".join(parts[i:i + 2]) for i, part in enumerate(parts) if self._mentions(part).count(drug)
                     or any(drug in m for m in self._mentions(part))]
            if spans and float(self.nli.scores([(span, sentence) for span in spans[:6]])[:, 1].max()) < self.ENTAIL:
                return True
        others = [d for d in present if d not in claimed and not any(d in c or c in d for c in claimed)]
        if not others:
            return False
        swaps = []
        for drug in claimed:
            pattern = re.compile(r"(?<![\w-])" + re.escape(drug) + r"(?![\w-])", re.I)
            swaps += [pattern.sub(other, sentence) for other in others]
        scores = self.nli.scores([(window, swap) for swap in swaps[:6]])[:, 1]
        return bool(len(scores)) and float(scores.max()) >= entailment

    def verify(self, sentence, cited, others=()):
        """``cited``/``others`` are lists of (unit_id, text). Returns Support."""
        terms = content_terms(sentence)
        if len(terms) <= 2 and not numbers(sentence):
            return Support("connective", method="no_content")
        cited_ids = {u for u, _ in cited}
        # Uncited passages are only consulted when they share vocabulary with the
        # sentence (cheap prefilter keeps NLI calls bounded).
        ranked_others = sorted(((self._lexical(sentence, text), uid, text) for uid, text in others if uid not in cited_ids),
                               reverse=True)
        candidates = [("cited", uid, text) for uid, text in cited] + [
            ("other", uid, text) for score, uid, text in ranked_others[:3] if score >= 0.3]
        if not candidates:
            return Support("unsupported", note="no evidence")
        sentence_numbers = numbers(sentence)
        sentence_codes = coded_terms(sentence)
        texts = {uid: text for _, uid, text in candidates}
        pairs, owners = [], []
        for origin, uid, text in candidates:
            for window in windows(text):
                pairs.append((window, sentence))
                owners.append((origin, uid, window))
        if self.nli is not None:
            probs = self.nli.scores(pairs)
            entail, contra = probs[:, 1], probs[:, 0]
            method = "nli"
        else:
            # Lexical fallback: stricter thresholds, no contradiction detection.
            entail = np.array([1.0 if self._lexical(sentence, w) >= 0.8 else 0.0 for (w, _) in pairs])
            contra = np.zeros(len(pairs))
            method = "lexical_strict"
        order = np.argsort(-entail)
        best_any = None
        for index in order:
            origin, uid, window = owners[index]
            if entail[index] < self.ENTAIL:
                break
            if sentence_numbers and not sentence_numbers <= numbers(texts[uid]):
                continue
            if sentence_codes and not sentence_codes <= coded_terms(texts[uid]):
                continue
            if bool(NEGATION.search(sentence)) != bool(NEGATION.search(window)) and entail[index] < 0.9:
                continue
            if self.substituted(sentence, window, float(entail[index])):
                continue
            best_any = (origin, uid, float(entail[index]), float(contra[index]), window)
            break
        lexical = max((self._lexical(sentence, text) for _, _, text in candidates), default=0.0)
        if best_any:
            origin, uid, e, c, window = best_any
            status = "supported" if origin == "cited" else "reattributed"
            return Support(status, [uid], e, c, self._lexical(sentence, window), method)
        # Combination of two windows from cited passages (synthesis across sentences).
        if self.nli is not None and len(cited) >= 1:
            cited_pairs = [(i, owners[i][2]) for i in range(len(owners)) if owners[i][0] == "cited"]
            top = sorted(cited_pairs, key=lambda item: -entail[item[0]])[:2]
            if len(top) == 2:
                joined = top[0][1] + " " + top[1][1]
                p = self.nli.scores([(joined, sentence)])[0]
                if (p[1] >= self.ENTAIL and sentence_numbers <= numbers(joined)
                        and sentence_codes <= coded_terms(joined) and not self.substituted(sentence, joined, float(p[1]))):
                    ids = list(dict.fromkeys(owners[i][1] for i, _ in top))
                    return Support("supported", ids, float(p[1]), float(p[0]), self._lexical(sentence, joined), "nli_combined")
        max_contra = float(contra.max()) if len(contra) else 0.0
        if max_contra >= self.CONTRADICT:
            return Support("contradicted", entailment=float(entail.max()), contradiction=max_contra, lexical=lexical, method=method)
        if sentence_numbers and entail.max() >= self.ENTAIL:
            return Support("numeric_unsupported", entailment=float(entail.max()), lexical=lexical, method=method,
                           note="numbers not found in supporting passage")
        return Support("unsupported", entailment=float(entail.max()) if len(entail) else 0.0,
                       contradiction=max_contra, lexical=lexical, method=method)
