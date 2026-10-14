import pytest

torch = pytest.importorskip("torch")


def test_controller_has_pair_heads_and_case_heads_with_finite_missing_inputs():
    from research.models.fgrc import FGRC

    model = FGRC(vocab_size=64, dimension=16)
    outputs = model(torch.zeros((2, 3, 2, 8), dtype=torch.long))
    assert outputs["relevance_logits"].shape == (2, 3, 2)
    assert outputs["relation_logits"].shape == (2, 3, 2, 3)
    assert outputs["answerability_logits"].shape == (2, 3)
    assert all(torch.isfinite(value).all() for value in outputs.values())


def test_missing_labels_are_masked_not_negative():
    from research.models.fgrc import FGRC, multitask_loss

    model = FGRC(vocab_size=64, dimension=16)
    outputs = model(torch.ones((1, 2, 2, 8), dtype=torch.long))
    labels = {"relevance": torch.full((1, 2, 2), -1.0),
              "relation": torch.full((1, 2, 2), -1), "answerability": torch.tensor([-1])}
    loss = multitask_loss(outputs, labels)
    assert loss.item() == 0
    loss.backward()


def test_duplicate_source_passages_do_not_increase_facet_support():
    from research.models.fgrc import aggregate_support

    scores = torch.tensor([[[0.8, 0.8]]])
    result = aggregate_support(scores, torch.tensor([[[7, 7]]]))
    assert result.item() == pytest.approx(0.8)


def test_selective_objective_penalizes_rejecting_everything():
    from research.models.fgrc import selective_loss

    loss = selective_loss(torch.zeros(4), torch.ones(4), target_coverage=0.7, eta=2)
    assert loss.item() == pytest.approx(0.98)


@pytest.mark.parametrize("missing", [True, False])
def test_padding_or_ineligible_source_does_not_change_case_predictions(missing):
    from research.models.fgrc import FGRC

    model = FGRC(vocab_size=64, dimension=16)
    with torch.no_grad():
        model.relation.weight.zero_()
        model.relation.bias.copy_(torch.tensor([-10., 10., 0.]))
        model.relation.weight[0, 16] = 40
        model.relation.weight[1, 16] = -40
    tokens = torch.ones((1, 1, 1, 4), dtype=torch.long)
    metadata = torch.tensor([[[[1., 0., 0., 0.]]]])
    original = model(tokens, metadata=metadata)
    extra = torch.zeros_like(tokens) if missing else tokens
    changed = model(torch.cat([tokens, extra], dim=2),
                    source_groups=torch.tensor([[[0, 1 if missing else -1]]]),
                    metadata=torch.cat([metadata, torch.zeros_like(metadata)], dim=2))
    assert torch.allclose(original["answerability_logits"], changed["answerability_logits"])
    assert torch.allclose(original["acceptance_logits"], changed["acceptance_logits"])
