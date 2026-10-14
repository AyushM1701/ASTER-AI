"""Execute the shipped answer-body renderer with a minimal DOM, without a server."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def render(result):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed for the web renderer regression")
    code = r"""
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const fragment = source.slice(source.indexOf('const patientHeadings ='), source.indexOf('function renderResult('));
const make = (tag, cls, value) => ({ tag, cls, value, children: [], append(...nodes) {this.children.push(...nodes);} });
const context = {el: make, text: (parent, value, cls) => parent.append(make('p', cls, value))};
vm.createContext(context); vm.runInContext(fragment, context);
const root = make('div'); context.renderAnswerBody(root, JSON.parse(process.argv[2]));
process.stdout.write(JSON.stringify(root));
"""
    completed = subprocess.run(
        [node, "-e", code, str(ROOT / "frontend/web/app.js"), json.dumps(result)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def test_patient_sections_do_not_become_postgraduate_layers():
    result = {
        "claims": [
            {"text": "Pain in a tooth."},
            {"text": "The cause is uncertain."},
            {"text": "Breathing trouble needs emergency help."},
        ],
        "patient_response": {
            "parts": [
                {"role": "meaning", "claim_index": 0},
                {"role": "uncertainty", "claim_index": 1},
                {"role": "warning_signs", "claim_index": 2},
            ]
        },
    }
    root = render(result)
    encoded = json.dumps(root)
    assert "Deeper explanation" not in encoded and "Simple explanation" not in encoded
    assert "When to get urgent help" in encoded
    assert root["children"][0]["children"][0]["value"] == "Pain in a tooth."


def test_student_layers_still_render_and_text_is_not_html():
    root = render(
        {
            "explanation_layers": {
                "simple": [{"text": "<script>test</script>"}],
                "deeper": [{"text": "Development mechanisms."}],
            }
        }
    )
    assert root["children"][0]["children"][0]["value"] == "Simple explanation"
    assert root["children"][1]["children"][0]["value"] == "Deeper explanation"
    assert root["children"][0]["children"][1]["value"] == "<script>test</script>"


def test_multipart_preserves_each_response_type():
    result = {
        "component_answers": [
            {
                "question": "Tooth pain?",
                "response": {
                    "patient_response": {"parts": [{"role": "meaning", "claim_index": 0}]},
                    "claims": [{"text": "Pain explanation."}],
                },
            },
            {
                "question": "Development?",
                "response": {
                    "explanation_layers": {"simple": [{"text": "Teeth develop."}], "deeper": []}
                },
            },
        ]
    }
    root = render(result)
    assert len(root["children"]) == 2
    assert "Pain explanation." in json.dumps(root) and "Simple explanation" in json.dumps(root)


def test_answer_scroll_uses_visible_geometry_without_offset_parent_assumptions():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node needed")
    source = ROOT / "frontend/web/app.js"
    code = r"""
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const fragment = source.slice(source.indexOf('function scrollToEntry('), source.indexOf('function selectedEvidence('));
const entry = {}, calls = [];
const region = {scrollTop:200, getBoundingClientRect:() => ({top:100}), scrollTo: options => calls.push(options)};
const element = {getBoundingClientRect:() => ({top:150})};
const context = {state:{entries:[entry]}, requestAnimationFrame:fn => fn(), scrollBehavior:() => 'instant', $:id => id==='scroll-region' ? region : element};
vm.createContext(context); vm.runInContext(fragment, context); context.scrollToEntry(entry);
process.stdout.write(JSON.stringify(calls));
"""
    completed = subprocess.run(
        [node, "-e", code, str(source)], capture_output=True, text=True, check=True
    )
    assert json.loads(completed.stdout) == [{"top": 238, "behavior": "instant"}]
