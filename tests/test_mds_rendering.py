import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.test_patient_rendering import render


def test_comparison_renderer_has_each_entity_and_gap_cell():
    result = {"claims": [{"text": "<img src=x onerror=alert(1)> literal source text"}], "comparison": {
        "entities": ["A", "B"], "scope": "Source-bound comparison", "rows": [],
        "axes": [{"label": "Histology", "cells": [{"claim_indices": [0]}, {"claim_indices": []}]}],
    }}
    body = render(result)
    output = json.dumps(body)
    assert "Histology" in output and "A" in output and "B" in output
    assert "Evidence missing" in output
    assert "<img src=x" in output
    assert not any(n["tag"] == "img" for n in body["children"])


def test_structured_sections_render_bound_content_and_missing_facet():
    output = json.dumps(render({"claims": [{"text": "A source paragraph"}], "structured_answer": {
        "sections": [{"heading": "Layers", "claim_indices": [0], "state": "supported"},
                     {"heading": "Functions", "claim_indices": [], "state": "missing"}],
    }}))
    assert "Layers" in output and "A source paragraph" in output
    assert "Functions" in output and "Evidence missing" in output


def test_multipart_comparison_also_displays_standalone_explanation():
    output = json.dumps(render({"claims": [{"text": "Mechanism source unit"}, {"text": "Histology source unit"}],
        "structured_answer": {"sections": [
            {"facet": "mechanism", "heading": "Mechanism", "claim_indices": [0], "state": "supported"},
            {"facet": "histopathology", "heading": "Histology", "claim_indices": [1], "state": "supported"}]},
        "comparison": {"entities": ["A", "B"], "scope": "Comparison", "axes": [{"facet": "histopathology", "label": "Histology", "cells": [{"claim_indices": [1]}, {"claim_indices": []}]}]}}))
    assert "Mechanism source unit" in output and "Histology source unit" in output


def test_first_viva_view_contains_one_question_without_reference_disclosure():
    output = json.dumps(render({"claims": [], "citations": [], "viva": {
        "stage": "await_answer", "question": "What is the concept?", "number": 1,
    }}))
    assert "What is the concept?" in output
    assert "rubric" not in output and "reference" not in output


def test_shared_source_paragraph_is_not_repeated_under_multiple_facets():
    result = {"claims": [{"text": "A shared source paragraph"}], "structured_answer": {
        "sections": [{"heading": "Definition", "claim_indices": [0]}, {"heading": "Structure", "claim_indices": [0]}],
    }}
    output = json.dumps(render(result))
    assert output.count("A shared source paragraph") == 1
    assert "paragraph 1 above" in output


def test_source_disclosure_binds_version_and_character_coordinates_as_safe_text():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed for the web renderer regression")
    script = r"""
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const make = (tag, cls, value) => ({tag, cls, value, children: [], append(...n) {this.children.push(...n);}});
const context = { el: make, text: (p,v,c) => p.append(make('p',c,v)), link: () => {},
disclosure: (p,label,fn) => {const n=make('details', '', label); fn(n); p.append(n);} };
vm.createContext(context); vm.runInContext(source.slice(source.indexOf('function sourceCards('), source.indexOf('function exportResponse(')), context);
const parent=make('div'); context.sourceCards(parent, JSON.parse(process.argv[2]));
process.stdout.write(JSON.stringify(parent));
"""
    result = {"citations": [{"chunk_id": "a", "section_id": "<script>literal</script>", "snapshot_id": "version-2", "excerpt": "Quoted source"}],
              "claim_evidence": [{"span": {"chunk_id": "a", "start": 4, "end": 12}}]}
    completed = subprocess.run([node, "-e", script, str(Path(__file__).resolve().parents[1] / "frontend/web/app.js"), json.dumps(result)], capture_output=True, text=True, check=True)
    output = completed.stdout
    assert "version-2" in output and "characters 4" in output and "12" in output
    assert "<script>literal</script>" in output
    assert '"tag":"script"' not in output
