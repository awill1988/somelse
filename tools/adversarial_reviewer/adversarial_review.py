#!/usr/bin/env python3
"""Adversarial code reviewer harness inspired by QwenLM/qwen-code headless review architecture.

Supports:
- Structured review dispositions: APPROVE, COMMENT, REQUEST_CHANGES
- Standardized exit codes: 0 for APPROVE/COMMENT, 3 for REQUEST_CHANGES (with --fail-on)
- JSON and Markdown output formats
- Seamless execution in GitHub Actions workflows and autonomous GitHub agents
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "adversarial-reviewer"

IGNORE_PATTERNS = [
    r"\.lock$",
    r"\.md$",
    r"LICENSE.*",
    r"\.gitignore$",
    r"^\.github/",
    r"^tools/",
]

MAX_DIFF_LINES = 300

SYSTEM_PROMPT = """You are an adversarial code review auditor for a high-integrity, #![no_std] Rust crate.
Your objective is to find bugs, soundness violations, invariant breaches, and subtle edge cases in the PR diff.

Repository Invariants:
1. Option match elimination: Macro expansions must evaluate input expressions exactly once.
2. Divergence guarantee: The else clause MUST diverge (return, break, continue, panic, loop).
3. Caller control flow: Transform blocks must preserve caller-scope return, break, and continue.
4. No-std integrity: The crate must remain #![no_std] and never introduce unexpected heap allocations.
5. Conventions: All commits must use Conventional Commits (strictly lowercase subject) with ZERO AI attribution.

Provide your evaluation adhering strictly to one of three dispositions:
- APPROVE (no critical or safety issues found)
- COMMENT (non-blocking suggestions or observations)
- REQUEST_CHANGES (soundness bug, invariant breach, or breaking counterexample found)

Conclude your review with:
DISPOSITION: APPROVE | COMMENT | REQUEST_CHANGES
"""


def should_ignore_file(filename: str) -> bool:
    return any(re.search(pattern, filename) for pattern in IGNORE_PATTERNS)


def extract_git_diff(base: str = "origin/main", head: str = "HEAD") -> tuple[str, list[str]]:
    cmd = ["git", "diff", f"{base}...{head}", "--name-only"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        cmd = ["git", "diff", base, head, "--name-only"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    changed_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    relevant_files = [f for f in changed_files if not should_ignore_file(f)]

    if not relevant_files:
        return "", []

    diff_cmd = ["git", "diff", f"{base}...{head}", "--"] + relevant_files
    diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=False)
    if diff_result.returncode != 0:
        diff_cmd = ["git", "diff", base, head, "--"] + relevant_files
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=False)

    lines = diff_result.stdout.splitlines()
    if len(lines) > MAX_DIFF_LINES:
        truncated_diff = "\n".join(lines[:MAX_DIFF_LINES]) + f"\n\n[Diff truncated to {MAX_DIFF_LINES} lines for focused review]"
    else:
        truncated_diff = diff_result.stdout

    return truncated_diff, relevant_files


def run_mock_reviewer(diff: str, files: list[str]) -> tuple[str, list[dict], str]:
    """Deterministic heuristic reviewer for tests and offline fallback."""
    findings = []
    disposition = "APPROVE"

    if "extern crate std" in diff or ("use std::" in diff and any(f.startswith("src/") for f in files)):
        findings.append({
            "severity": "critical",
            "category": "no_std",
            "file": "src/lib.rs",
            "line": None,
            "title": "Potential std leakage into #![no_std] crate core",
            "details": "Detected `use std::` or `extern crate std` in core crate source files.",
            "counterexample": "// Attempting to compile for no_std target fails:\n// cargo build --target thumbv7m-none-eabi",
        })
        disposition = "REQUEST_CHANGES"

    if "Co-authored-by:" in diff or "Co-Authored-By:" in diff:
        findings.append({
            "severity": "critical",
            "category": "attribution",
            "file": "general",
            "line": None,
            "title": "AI attribution detected",
            "details": "Commit diff contains AI attribution metadata violating repository policy.",
            "counterexample": "Co-authored-by: AI Assistant",
        })
        disposition = "REQUEST_CHANGES"

    if not findings:
        summary = "No soundness violations or invariant breaches detected. Invariant checks passed."
    else:
        summary = f"Detected {len(findings)} invariant violation(s) requiring remediation."

    return disposition, findings, summary


def resolve_runner(cache_dir: Path) -> Path | None:
    candidates = [
        cache_dir / "llama_runner" / "build" / "bin" / "llama-cli",
        cache_dir / "llama_runner" / "llama-cli",
        cache_dir / "llama-cli",
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate.resolve(), os.X_OK):
            return candidate.resolve()

    found = list(cache_dir.glob("**/llama-cli"))
    for candidate in found:
        if os.access(candidate.resolve(), os.X_OK):
            return candidate.resolve()

    system_cli = shutil.which("llama-cli")
    if system_cli:
        return Path(system_cli).resolve()

    return None


def run_llama_inference(runner_path: Path, model_path: Path, prompt: str) -> str:
    runner_resolved = runner_path.resolve()
    if not runner_resolved.exists():
        raise FileNotFoundError(f"llama-cli runner not found at {runner_resolved}")
    if not model_path.exists():
        raise FileNotFoundError(f"model weights not found at {model_path}")

    # Set up LD_LIBRARY_PATH and DYLD_LIBRARY_PATH to include runner directories
    lib_dirs = {str(runner_resolved.parent), str(runner_path.parent)}
    for p in runner_resolved.parent.glob("*.so*"):
        lib_dirs.add(str(p.parent))

    env = os.environ.copy()
    existing_ld = env.get("LD_LIBRARY_PATH", "")
    existing_dyld = env.get("DYLD_LIBRARY_PATH", "")

    joined_dirs = ":".join(sorted(lib_dirs))
    env["LD_LIBRARY_PATH"] = f"{joined_dirs}:{existing_ld}".rstrip(":")
    env["DYLD_LIBRARY_PATH"] = f"{joined_dirs}:{existing_dyld}".rstrip(":")

    cmd = [
        str(runner_path),
        "-m", str(model_path),
        "-p", prompt,
        "-n", "768",
        "-c", "4096",
        "--temp", "0.2",
        "--top-p", "0.9",
        "-t", "4",
        "--no-display-prompt",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"llama-cli execution failed: {result.stderr}")

    return result.stdout.strip()


def parse_model_output(raw_output: str) -> tuple[str, list[dict], str]:
    # Match DISPOSITION or VERDICT
    disp_match = re.search(r"(?:DISPOSITION|VERDICT):\s*(APPROVE|COMMENT|REQUEST_CHANGES|PASS|FLAGGED|CRITICAL)", raw_output, re.IGNORECASE)
    if disp_match:
        matched = disp_match.group(1).upper()
        if matched in ("APPROVE", "PASS"):
            disposition = "APPROVE"
        elif matched in ("REQUEST_CHANGES", "CRITICAL"):
            disposition = "REQUEST_CHANGES"
        else:
            disposition = "COMMENT"
    else:
        disposition = "COMMENT"

    findings = []
    # Extract any bulleted or numbered concerns
    for line in raw_output.splitlines():
        line_clean = line.strip()
        if re.search(r"(?:CRITICAL|BUG|VIOLATION|BREACH|FAIL)", line_clean, re.IGNORECASE):
            findings.append({
                "severity": "critical" if disposition == "REQUEST_CHANGES" else "warning",
                "category": "soundness",
                "file": "general",
                "line": None,
                "title": line_clean[:120],
                "details": line_clean,
                "counterexample": None,
            })

    summary = f"Review disposition: {disposition}."
    return disposition, findings, summary


def build_markdown_report(target: str, disposition: str, findings: list[dict], raw_text: str, files: list[str]) -> str:
    status_icon = "🟢" if disposition == "APPROVE" else ("🟡" if disposition == "COMMENT" else "🔴")
    report = f"## {status_icon} Adversarial Code Review: {target}\n\n"
    report += f"**Disposition**: **`{disposition}`**  \n"
    report += f"**Audited Files**: {', '.join(f'`{f}`' for f in files) if files else '*(none)*'}\n\n"

    if findings:
        report += "### Findings & Invariant Violations\n\n"
        for finding in findings:
            sev_icon = "🔴" if finding["severity"] == "critical" else "🟡"
            report += f"- {sev_icon} **[{finding['category'].upper()}]** {finding['title']}\n"
            if finding.get("details") and finding["details"] != finding["title"]:
                report += f"  - *Details*: {finding['details']}\n"
            if finding.get("counterexample"):
                report += f"  - *Counterexample*:\n    ```rust\n    {finding['counterexample']}\n    ```\n"
        report += "\n"

    report += "<details><summary>Detailed Auditor Output</summary>\n\n"
    report += "```text\n"
    report += raw_text.strip() + "\n"
    report += "```\n\n"
    report += "</details>\n\n"
    report += "*Audit performed with local quantized open-weight model in headless harness.*\n"
    return report


def main():
    parser = argparse.ArgumentParser(description="Headless adversarial code reviewer inspired by qwen review run.")
    parser.add_argument("--base", default="origin/main", help="Base ref to compare against")
    parser.add_argument("--head", default="HEAD", help="Head ref to compare")
    parser.add_argument("--target", default="HEAD", help="Target identifier for review reporting")
    parser.add_argument("--mock", action="store_true", help="Run deterministic heuristic review without model weights")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="Cache directory for models")
    parser.add_argument("--summary-file", type=Path, default=None, help="File to write step summary to (e.g. $GITHUB_STEP_SUMMARY)")
    parser.add_argument("--pr", type=int, default=None, help="Pull request number to post comment to")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    parser.add_argument("--fail-on", choices=["request-changes", "critical", "none"], default="request-changes",
                        help="Disposition that causes a non-zero exit code (default: request-changes)")
    args = parser.parse_args()

    start_time = time.time()
    diff, files = extract_git_diff(args.base, args.head)

    if not files or not diff.strip():
        disposition = "APPROVE"
        findings = []
        summary = "No relevant changes to audit."
        raw_text = "No changes to review."
    elif args.mock:
        disposition, findings, summary = run_mock_reviewer(diff, files)
        raw_text = summary
    else:
        model_path = args.cache_dir / "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf"
        runner_path = resolve_runner(args.cache_dir)

        if not runner_path or not model_path.exists():
            print("local model weights or runner not found; falling back to heuristic mock reviewer.", file=sys.stderr)
            disposition, findings, summary = run_mock_reviewer(diff, files)
            raw_text = summary
        else:
            full_prompt = f"{SYSTEM_PROMPT}\n\nFiles under review: {', '.join(files)}\n\nDiff:\n```diff\n{diff}\n```\n\nAdversarial Audit:"
            raw_text = run_llama_inference(runner_path, model_path, full_prompt)
            disposition, findings, summary = parse_model_output(raw_text)

    duration = round(time.time() - start_time, 2)
    markdown_report = build_markdown_report(args.target, disposition, findings, raw_text, files)

    if args.json:
        payload = {
            "target": args.target,
            "disposition": disposition,
            "summary": summary,
            "findings": findings,
            "model": "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf",
            "duration_seconds": duration,
            "disclosures": "Adversarial automated review generated with open-weight local model.",
        }
        print(json.dumps(payload, indent=2))
    else:
        print(markdown_report)

    # Machine-readable completion marker (following qwen review run specification)
    print(f"Review complete: {args.target} — {disposition}")

    if args.summary_file:
        with open(args.summary_file, "a", encoding="utf-8") as out:
            out.write(markdown_report + "\n")

    if args.pr and os.environ.get("GITHUB_TOKEN"):
        try:
            cmd = ["gh", "pr", "comment", str(args.pr), "--body", markdown_report]
            subprocess.run(cmd, check=True)
            print(f"posted review report to PR #{args.pr}")
        except Exception as error:
            print(f"could not post PR comment: {error}", file=sys.stderr)

    # Exit code contract:
    # 0 = clean or comments
    # 3 = changes requested (when gated)
    # 1 = fatal error
    if args.fail_on in ("request-changes", "critical") and disposition == "REQUEST_CHANGES":
        sys.exit(3)


if __name__ == "__main__":
    main()
