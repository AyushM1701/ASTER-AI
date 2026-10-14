"""Compact offline FGRC reference network and masked candidate objectives.

Untrained by default. Dataset-specific tokenization, grouped labels, calibration
and paired B6 evaluation are prerequisites for any research performance claim.
Safety and source permission decisions remain outside this module.
"""

import torch
from torch import nn
from torch.nn import functional as F


def aggregate_support(scores, source_groups):
    """Max within source group, then max across independent source groups.

This conservative aggregation makes no probabilistic independence claim.
Repeated copies never increase confidence; other aggregators are ablations.
"""
    if scores.shape != source_groups.shape:
        raise ValueError("source groups must match pair scores")
    output = []
    for case, groups in zip(scores, source_groups):
        facets = []
        for values, ids in zip(case, groups):
            independent = [values[ids == identity].max() for identity in ids.unique() if identity >= 0]
            facets.append(torch.stack(independent).max() if independent else values.sum() * 0)
        output.append(torch.stack(facets))
    return torch.stack(output)


class FGRC(nn.Module):
    def __init__(self, vocab_size=4096, dimension=64, metadata_size=4, max_tokens=512):
        super().__init__()
        self.max_tokens = max_tokens
        self.metadata_size = metadata_size
        self.embedding = nn.Embedding(vocab_size, dimension, padding_idx=0)
        self.position = nn.Embedding(max_tokens, dimension)
        layer = nn.TransformerEncoderLayer(dimension, 2, dimension * 2, dropout=0, batch_first=True)
        self.encoder = nn.TransformerEncoder(layer, 1, enable_nested_tensor=False)
        features = dimension + metadata_size
        self.relevance = nn.Linear(features, 1)
        self.relation = nn.Linear(features, 3)
        self.answerability = nn.Linear(4, 3)
        self.acceptance = nn.Linear(4, 1)

    def forward(self, token_ids, source_groups=None, essential_mask=None, metadata=None):
        if token_ids.ndim != 4 or token_ids.shape[-1] > self.max_tokens:
            raise ValueError("expected [case, facet, candidate, tokens] within token budget")
        batch, facets, candidates, length = token_ids.shape
        if min(batch, facets, candidates, length) < 1:
            raise ValueError("empty tensor dimensions are unsupported")
        flat = token_ids.reshape(-1, length)
        present = flat != 0
        attention_mask = ~present.clone()
        attention_mask[:, 0] = False  # all-padding fixtures must remain finite
        encoded = self.encoder(self.embedding(flat) + self.position(torch.arange(length, device=flat.device)),
                               src_key_padding_mask=attention_mask)
        pooled = (encoded * present.unsqueeze(-1)).sum(1) / present.sum(1).clamp_min(1).unsqueeze(-1)
        if metadata is None:
            metadata = torch.zeros(batch, facets, candidates, self.metadata_size, device=flat.device)
        if metadata.shape != (batch, facets, candidates, self.metadata_size) or not torch.isfinite(metadata).all():
            raise ValueError("bounded finite pair metadata required")
        features = torch.cat([pooled, metadata.reshape(-1, self.metadata_size)], dim=-1)
        relevance = self.relevance(features).reshape(batch, facets, candidates)
        relation = self.relation(features).reshape(batch, facets, candidates, 3)
        support = relevance.sigmoid() * relation.softmax(-1)[..., 0]
        support = support * present.any(-1).reshape(batch, facets, candidates)
        if source_groups is None:
            source_groups = torch.arange(candidates, device=flat.device).expand(batch, facets, candidates)
        coverage = aggregate_support(support, source_groups)
        if essential_mask is None:
            essential_mask = torch.ones(batch, facets, dtype=torch.bool, device=flat.device)
        if essential_mask.shape != (batch, facets) or not essential_mask.any(-1).all():
            raise ValueError("each case requires at least one essential facet")
        minimum = coverage.masked_fill(~essential_mask, 1).min(-1).values
        mean = (coverage * essential_mask).sum(-1) / essential_mask.sum(-1)
        missing = ((coverage == 0) & essential_mask).sum(-1) / essential_mask.sum(-1)
        eligible = present.any(-1).reshape(batch, facets, candidates) & (source_groups >= 0) & essential_mask.unsqueeze(-1)
        conflict = relation.softmax(-1)[..., 1].masked_fill(~eligible, 0).max(-1).values.max(-1).values
        case_features = torch.stack([minimum, mean, missing, conflict], dim=-1)
        return {"relevance_logits": relevance, "relation_logits": relation,
                "facet_support": coverage, "answerability_logits": self.answerability(case_features),
                "acceptance_logits": self.acceptance(case_features).squeeze(-1)}


def selective_loss(acceptance, error_loss, target_coverage=0.7, eta=1.0, epsilon=1e-8):
    if not 0 <= target_coverage <= 1 or acceptance.shape != error_loss.shape or acceptance.numel() == 0:
        raise ValueError("selection scores/errors and coverage target required")
    return (acceptance * error_loss).sum() / (acceptance.sum() + epsilon) + eta * F.relu(
        acceptance.new_tensor(target_coverage) - acceptance.mean()) ** 2


def multitask_loss(outputs, labels, weights=None):
    weights = weights or {"rel": 1, "nli": 1, "ans": 1, "rank": 0, "cal": 0, "sel": 0}
    total = sum(value.sum() for value in outputs.values()) * 0
    for name, head, term in [("relevance", "relevance_logits", "rel"),
                             ("relation", "relation_logits", "nli"),
                             ("answerability", "answerability_logits", "ans")]:
        if name not in labels:
            continue
        gold = labels[name]
        mask = gold >= 0
        if not mask.any():
            continue
        prediction = outputs[head][mask]
        loss = F.binary_cross_entropy_with_logits(prediction, gold[mask].float()) if name == "relevance" else F.cross_entropy(prediction, gold[mask].long())
        total = total + weights.get(term, 0) * loss
    # Calibration targets must be independently defined case-level events.
    if "accepted_correct" in labels:
        gold = labels["accepted_correct"]
        mask = gold >= 0
        if mask.any():
            probability = outputs["acceptance_logits"][mask].sigmoid()
            total = total + weights.get("cal", 0) * ((probability - gold[mask]) ** 2).mean()
            total = total + weights.get("sel", 0) * selective_loss(probability, 1 - gold[mask])
    # Pairs are explicitly annotated positive/negative flat candidate indices.
    if weights.get("rank", 0) and labels.get("audited_ranking_pairs") is not None:
        pairs = labels["audited_ranking_pairs"]
        if len(pairs):
            scores = outputs["relevance_logits"].reshape(-1)
            total = total + weights["rank"] * F.softplus(scores[pairs[:, 1]] - scores[pairs[:, 0]]).mean()
    return total
