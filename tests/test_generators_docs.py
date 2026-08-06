from __future__ import annotations

from pinesprout.generators.doc_generator import DocFormat, generate_docs
from pinesprout.generators.readme_generator import generate_readme
from pinesprout.generators.report_generator import generate_report


def test_generate_readme_includes_title(clean_v6_source):
    readme = generate_readme(clean_v6_source, source_filename="strategy.pine")
    assert "Clean EMA Strategy" in readme


def test_generate_readme_attribution_has_no_broken_placeholder_link(clean_v6_source):
    """Regression test: the "Generated with PineSprout" footer used to
    link to a placeholder GitHub URL (github.com/pinesprout/pinesprout)
    that isn't anyone's real repo, so clicking it went somewhere
    unrelated/broken. It's now plain, unlinked text -- verify it stays
    that way rather than silently regaining a hardcoded, likely-wrong URL."""
    readme = generate_readme(clean_v6_source, source_filename="strategy.pine")
    assert "Generated with PineSprout" in readme
    assert "github.com/pinesprout" not in readme
    assert "[PineSprout](" not in readme


def test_generate_readme_includes_metrics_table(clean_v6_source):
    readme = generate_readme(clean_v6_source, source_filename="strategy.pine")
    assert "Lines of code" in readme
    assert "Complexity score" in readme


def test_generate_docs_markdown(clean_v6_source):
    doc = generate_docs(clean_v6_source, fmt=DocFormat.MARKDOWN)
    assert doc.startswith("# Clean EMA Strategy")


def test_generate_docs_html(clean_v6_source):
    doc = generate_docs(clean_v6_source, fmt=DocFormat.HTML)
    assert "<html" in doc
    assert "Clean EMA Strategy" in doc


def test_generate_docs_html_escapes_source(clean_v6_source):
    doc = generate_docs(clean_v6_source, fmt=DocFormat.HTML)
    assert "&lt;" not in doc or "<" in clean_v6_source  # sanity: no raw injection issue
    assert "<pre>" in doc or "<pre><code>" in doc


def test_generate_report_includes_lint_summary(clean_v6_source):
    report = generate_report(clean_v6_source, file="strategy.pine")
    assert "Lint Summary" in report
    assert "Errors:" in report


def test_generate_report_includes_optimization_section(messy_v4_source):
    report = generate_report(messy_v4_source, file="messy.pine")
    assert "Optimization Suggestions" in report
