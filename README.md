Good — the marketing page is done. What comes next is **polishing the project for open-source contributors and researchers**. Below is a complete, production-grade `README.md` you can drop into the repo root, plus a few practical next steps.

---

### 1. `README.md` (drop in repo root)

```markdown
# Research to Jupyter

**Turn any research paper PDF into a runnable, reviewable Jupyter notebook — locally.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tauri v2](https://img.shields.io/badge/Tauri-v2-24C8DB)](https://tauri.app)
[![Rust](https://img.shields.io/badge/Rust-1.80%2B-orange)](https://rustup.rs)
[![Status](https://img.shields.io/badge/status-under%20active%20development-yellow)](#roadmap)

Research to Jupyter is a cross-platform desktop app (Windows / macOS / Linux) that reads a
research paper PDF, extracts its text and equations locally, removes citation noise to save
tokens, and asks your chosen AI model to generate a Jupyter notebook that reproduces the
paper's stated experiments — **nothing more, nothing less**.

The generated `.ipynb` is a *starting point for reproduction*, not a guarantee that the
published results were reproduced. Every cell should be reviewed and run by a human.

---

## ✨ Features

- **Math-aware local extraction** — Python + PyMuPDF / PyMuPDF4LLM, with optional Docling OCR.
- **Token optimization** — strips `[1]`, `(Smith et al., 2024)`, and everything from
  "References" onward. Shows raw vs. cleaned char/token counts.
- **Your keys, your machine** — OpenAI, Anthropic, Google Gemini, or fully offline via Ollama.
- **Exact-reproduction prompt** — forbids extra experiments, ablations, plots, or invented
  hyperparameters; missing values are flagged as `# unspecified in paper: chosen default`.
- **Clean file management** — `papers/<name>.pdf` + `notebooks/<name>.ipynb`, same stem,
  versioned on collision (`(2)`, `(3)` …).
- **Live text viewer** — raw and cleaned text shown in the dashboard before generation.
- **Cross-platform** — small native binary via Tauri v2 + Rust.

---

## 📦 Install

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Rust | 1.80+ | https://rustup.rs |
| Tauri CLI | 2.x | `cargo install tauri-cli --version "^2.0.0" --locked` |
| Node.js | 18+ | only for the CLI; app itself uses no npm deps |
| Python | 3.10+ | with `pymupdf`, `pymupdf4llm`, `pypdf` (optional: `docling`) |
| WebView2 | latest | Windows 10 only |

### Python setup (once)

```bash
python -m pip install --upgrade pip
python -m pip install pymupdf pymupdf4llm pypdf
# Optional, for scanned PDFs / better math:
python -m pip install docling
```

### Run in development

```bash
git clone https://github.com/YOUR_ORG/research-to-jupyter
cd research-to-jupyter
mkdir dist
move index.html dist\index.html   # Windows; on macOS/Linux use: mv index.html dist/
cargo tauri dev
```

### Build a release binary

```bash
cargo tauri build
```

Installers land in `src-tauri/target/release/bundle/`.

---

## 🚀 Usage

1. Launch the app.
2. **Choose a PDF** (or drag & drop). The text is extracted locally and shown in the
   *Raw text* / *Cleaned* tabs.
3. Pick a provider and model, paste your API key.
4. Click **Synthesize Notebook**.
5. Open the generated `.ipynb` in Jupyter Lab, VS Code, or Colab and run the cells.

Output folders (default: `~/Documents/ResearchToJupyter/`):

```
papers/       ← your PDF (copied here)
notebooks/    ← <same-name>.ipynb
```

### Using Google Gemini

Select **OpenAI** provider, model `gemini-2.5-flash`, your `AIza…` key, and base URL:

```
https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
```

A native "Google Gemini" dropdown is planned.

---

## 🏗️ Architecture

```
research-to-jupyter/
├── dist/index.html            # Frontend (Tauri IPC via window.__TAURI__)
├── scripts/extract_paper.py   # Local Python extractor (PyMuPDF / Docling)
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── capabilities/default.json
│   └── src/
│       ├── lib.rs             # Commands, cleaner, chunker, LLM engine, notebook compiler
│       └── main.rs
└── .github/workflows/release.yml
```

Key Rust modules (all in `lib.rs`):

| Function | Purpose |
|---|---|
| `extract_paper_text` | Spawns Python extractor, captures stdout |
| `clean_text` | Citation strip + bibliography cut + whitespace normalize |
| `generate_jupyter_notebook` | Orchestrates prepare → extract → clean → generate → package → write |
| `package_notebook` | Parses `<!-- CODE_CELL -->` / `<!-- MARKDOWN_CELL -->` into nbformat 4.5 |
| `reveal_path` | Cross-platform "reveal in folder" |

---

## 🧪 Testing

```bash
# Validate a generated notebook
python -c "import nbformat; nbformat.validate(nbformat.read('notebooks/paper.ipynb', as_version=4)); print('VALID')"
```

---

## 🗺️ Roadmap

- [ ] Native Google Gemini provider option
- [ ] Bundle Python runtime as a Tauri sidecar (zero-install for end users)
- [ ] Notebook execution + result capture (run cells, embed outputs)
- [ ] Per-paper settings (chunk size, model, temperature)
- [ ] Export to `.py` script / Colab link
- [ ] Unit tests for cleaner + chunker + parser
- [ ] Auto-update via Tauri updater plugin

---

## 🤝 Contributing

Contributions are very welcome — this is an early-stage open-source project.

1. Fork the repo and create a feature branch.
2. Keep commits small and focused.
3. Run `cargo tauri dev` and `cargo clippy` before opening a PR.
4. **Never commit API keys, `.env` files, or `target/`.**

Good first issues:
- Add a native Gemini provider option.
- Improve equation extraction quality.
- Add tests for `clean_details` and `split_chunks`.
- Polish the installer icons and bundle metadata.

---

## ⚠️ Limitations

- Generated code is **not executed** by the app. Review before running.
- OCR quality depends on the PDF and installed Python packages.
- LLM output may still contain hallucinated details despite the strict prompt.
- Large papers are split into chunks; cross-chunk context is limited.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

- [Tauri](https://tauri.app) · [Rust](https://rust-lang.org)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) · [PyMuPDF4LLM](https://github.com/pymupdf/pymupdf4llm) · [Docling](https://github.com/DS4SD/docling)
- Tailwind CSS · IBM Plex fonts
```

---

### 2. `CONTRIBUTING.md`

```markdown
# Contributing to Research to Jupyter

Thanks for helping improve this project. Please read this before opening a PR.

## Ground rules
- Be respectful and constructive.
- Open an issue first for large changes.
- Keep PRs focused — one feature or fix per PR.
- Never commit secrets, API keys, or `target/`, `node_modules/`, `.venv/`.

## Development setup
See the README "Install" section. You need Rust, Tauri CLI, Python 3.10+, and the
Python packages listed there.

## Running locally
```bash
cargo tauri dev
```

## Code style
- Rust: `cargo fmt` and `cargo clippy -- -D warnings` must pass.
- Python: PEP 8, type hints where helpful.
- Frontend: keep the single-file `index.html` approach; no build step.

## Commit messages
Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

## Reporting bugs
Include: OS, app version, Python version, provider/model, and the console log
from the app's "Console" tab. Redact API keys.

## Security
If you find a security issue, please email the maintainer privately instead of
opening a public issue.
```

---

### 3. `LICENSE` (MIT)

```
MIT License

Copyright (c) 2025 YOUR_NAME

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

### 4. `.gitignore` (replace existing)

```gitignore
# Rust / Tauri
target/
src-tauri/target/
src-tauri/gen/
src-tauri/WixTools/
*.pdb

# Frontend
dist/
node_modules/

# Python
.venv/
venv/
env/
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# OS
.DS_Store
Thumbs.db
desktop.ini

# Secrets
.env
.env.*
*.key

# Editor
.vscode/
.idea/
```

---

### 5. `src-tauri/Cargo.toml` — add a `dev` profile for faster iteration

Append to the end of `src-tauri/Cargo.toml`:

```toml
[profile.dev]
opt-level = 0
debug = true

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true
```

---

### 6. Recommended GitHub repo setup

1. **Topics** (Settings → About): `tauri`, `rust`, `jupyter`, `research`, `pdf`, `llm`, `open-source`, `desktop-app`.
2. **Description**: "Turn any research paper PDF into a runnable Jupyter notebook — locally, with your own AI key."
3. **Website**: your GitHub Pages URL.
4. **Issues templates** (`.github/ISSUE_TEMPLATE/bug_report.md`):

```markdown
---
name: Bug report
about: Report a problem
---
**OS:** 
**App version:** 
**Python version:** 
**Provider / model:** 

**Steps to reproduce:**
1. 
2. 

**Expected behavior:**

**Actual behavior:**

**Console log (from the app's Console tab, redact API keys):**
```
paste here
```
```

5. **PR template** (`.github/pull_request_template.md`):

```markdown
## What does this PR do?

## Checklist
- [ ] `cargo fmt` passes
- [ ] `cargo clippy -- -D warnings` passes
- [ ] `cargo tauri dev` runs without errors
- [ ] No secrets or API keys committed
- [ ] README updated if behavior changed
```

---

### 7. What to do next (in order)

1. **Run `cargo tauri dev`** and confirm the app opens and extracts a PDF in under ~10 seconds.
2. **Test the full pipeline** with one real paper using your Gemini key.
3. **Validate the notebook** with `nbformat.validate(...)` — fix any cell that fails.
4. **Run `cargo clippy -- -D warnings`** and fix all warnings.
5. **Create the GitHub repo**, push, and enable GitHub Pages from `website/`.
6. **Tag `v0.1.0`** to trigger the release workflow and produce the first installers.
7. **Open 3–5 "good first issue" tickets** so contributors can help.
8. **Write a short blog post / tweet / Reddit post** linking to the marketing page — researchers are the target audience; mention "local", "your own API key", and "exact reproduction".

---

### One honest note for the README (keep it)

> "Generated notebooks are AI drafts. They have not been executed or validated against the paper's reported results. Always review, run, and verify before citing."

This single line protects you legally and sets correct expectations — it's the most important sentence in the whole project.