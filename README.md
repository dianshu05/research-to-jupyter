
# Research to Jupyter

Convert research paper PDFs into executable, exact-reproduction Jupyter notebooks.

**Status:** Under active development.  
**License:** MIT  
**Platforms:** Windows, macOS, Linux  

---

## What it does

1. **Extract** — A local Python engine reads the PDF and preserves equations, tables, and layout.
2. **Clean** — Rust removes citation brackets, author-year references, and clips everything from `References`/`Bibliography` onward. Shows raw vs cleaned char/token counts.
3. **Generate** — Your paper text is sent to the model you chose (OpenAI, Anthropic, Gemini, or local Ollama). The system prompt enforces exact-reproduction behavior: implement only what the paper describes, no extras, no invented details.
4. **Compile** — Model output is parsed into nbformat 4.5 cells (Markdown + Code) and written as `<paper>.ipynb`.

The PDF is copied into a `papers/` folder, the notebook is written to a `notebooks/` folder, and both share the same filename stem (versioned if a collision occurs).

---

## Why this exists

Researchers often want a runnable starting point for a paper's experiments, but copying equations, loss functions, training loops, and evaluation code by hand is slow and error-prone. This app gives you a **local-first, AI-assisted draft notebook** that follows the paper's stated experimental scope, so you can inspect, correct, and run it.

---

## Supported providers

| Provider | Endpoint style | Key format | Notes |
|---|---|---|---|
| OpenAI | `chat/completions` | `sk-...` | Model default: `gpt-4o` |
| Anthropic | `messages` | `sk-ant-...` | Model default: `claude-3-5-sonnet-latest` |
| Google Gemini | `generateContent` | `AIza...` | Model default: `gemini-2.5-flash` |
| Ollama | `api/chat` | none | Model default: `llama3.1:latest` |

API keys are used only in memory for the request. They are never written to disk or logged.

---

## Requirements

- Rust toolchain (stable)
- Tauri CLI v2
- Python 3 + one of the supported extractor packages:
  - `pymupdf` (always useful)
  - `pymupdf4llm` (recommended for Markdown + math)
  - `pypdf` (fallback)
  - `docling` (optional: OCR + layout for scanned PDFs)
- A working WebView2 runtime on Windows 10; Windows 11 and macOS include it by default.

---

## Quick start (end users)

1. Install Rust and Python.
2. Install extractor packages:  
   `python -m pip install pymupdf pymupdf4llm pypdf`
3. From the project root:  
   `cargo tauri dev`
4. Pick a PDF, enter your API key, choose a provider/model, and click **Synthesize Notebook**.
5. Open the resulting `.ipynb` in Jupyter, VS Code, or your preferred environment and review the code before running it.

---

## Development

### Project layout

```text
research-to-jupyter/
├── Cargo.toml                 # workspace root
├── dist/index.html            # Tauri frontend
├── scripts/
│   └── extract_paper.py       # local PDF extractor
└── src-tauri/
    ├── Cargo.toml
    ├── build.rs
    ├── tauri.conf.json
    ├── capabilities/
    │   └── default.json
    └── src/
        ├── lib.rs
        └── main.rs
```

### Running locally

```bash
cargo tauri dev
```

### Adding a new provider

1. Add the provider name to the allowed list in `lib.rs`.
2. Add a URL helper and a `call_llm` branch.
3. Add a response parser.
4. Update the frontend provider dropdown and default model list.

### Improving extraction

The extractor tries strategies in order. You can tune the order, add a new backend, or improve fallback heuristics in `scripts/extract_paper.py`. For scanned PDFs, `docling` is the most capable option.

### Improving notebook quality

The strongest lever is the system prompt and the cell-parsing layer in `lib.rs`. Contributions that make the prompt more faithful, reduce hallucinated code, or improve the `CODE_CELL`/`MARKDOWN_CELL` parser are very valuable.

---

## Project status

This project is under active development.

- The pipeline and file layout are stable.
- Extraction, cleaning, and notebook compilation work today.
- Model output quality depends on the selected model and the paper. For complex or ambiguous papers, review the notebook carefully.
- Some edge cases are still being improved: very long papers, heavily scanned PDFs, ambiguous math, and provider-specific rate limits.

**Disclaimer:** Generated notebooks are drafts. They are not validated against the paper's reported results and should be reviewed and executed before use.

---

## Contributing

Contributions are welcome from researchers and engineers.

- Bug reports with the exact PDF, provider, model, and error are especially useful.
- Prompt refinements, extraction improvements, and notebook-parser fixes are high-impact.
- If you are not a Rust developer, you can still help by testing notebooks, reporting missing experimental details, and improving documentation.

Please open an issue before large changes so we can align on scope.

---

## License

MIT. See `LICENSE`.

---

## Acknowledgments

- [Tauri](https://tauri.app/) for the desktop framework.
- The PyMuPDF and PDF extraction community for local extraction tooling.
- The open research community for the papers and experiments this tool helps reproduce.


