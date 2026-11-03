# Attendance Report System

A Python-based automated system for parsing, transforming, and generating attendance reports (supporting Type A and Type B formats) with a layered architecture, design patterns, and unit testing.

---

## How It Works

The input is a PDF attendance report. The system runs it through a four-step pipeline:

1. **Classify** – `DocumentClassifier` reads the PDF (via OCR) and decides whether it is **Type A** (HaNesher, detailed columns and a bottom summary) or **Type B** (Employee timesheet, top summary and employee card).
2. **Parse** – `ParserFactory` returns the right parser, which converts the raw text into an `AttendanceReport` object.
3. **Transform** – `TransformationService` selects the matching strategy (Strategy Pattern) and produces a new, immutable `AttendanceReport`. Generation parameters are read from `config.json`.
4. **Render** – the report is written as an **HTML** or **PDF** file.

```
PDF  ->  Classifier  ->  Parser  ->  Transformation  ->  Renderer  ->  HTML / PDF
```

---

## Project Structure

```
files/
├── domain/            Core data models and exceptions
├── parsers/           Classifier, OCR, parser factory, Type A / Type B parsers
├── transformation/    Transformation service and Type A / Type B strategies
├── generators/        HTML and PDF renderers
├── tests/             pytest test suite
├── input_pdfs/        Sample input PDFs
├── output/            Generated reports
├── main.py            Pipeline entry point (non-interactive)
├── cli.py             Command-line entry point (asks for the export format)
├── config.py          Loads and validates config.json
├── config.json        Settings for report generation
├── requirements.txt   Python dependencies
├── DECISIONS.md       Design decisions: options, choice and reasons
├── Dockerfile         Container definition
└── pytest.ini         pytest configuration
```

- **`domain/`** – `AttendanceReport`, `AttendanceRow`, `ReportSummary` and the custom exceptions.
- **`parsers/`** – `DocumentClassifier`, `ParserFactory`, `TypeAParser`, `TypeBParser`, and `ocr.py` (PDF to text).
- **`transformation/`** – `TransformationService` plus `TypeATransformationStrategy` and `TypeBTransformationStrategy`.
- **`generators/`** – `HtmlRenderer` and `PdfRenderer` (the PDF is produced from the HTML).

The `parsers`, `transformation` and `generators` packages depend only on `domain`, never on each other. `main.py` connects them.

---

## Entry Points

| File | Purpose |
|------|---------|
| `main.py` | Runs the full pipeline without asking questions. Exposes `build_report()` and `process_attendance_report()`. |
| `cli.py` | Interactive command line. Reuses `build_report()` from `main.py`, asks for the export format, and builds a descriptive file name. |

---

## Running Locally

### Prerequisites

- Python 3.12 or newer
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and available on your `PATH`
- [Poppler](https://poppler.freedesktop.org/) installed and available on your `PATH` (required by `pdf2image`)

### Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Usage

**Interactive CLI** (asks whether to export HTML or PDF):

```bash
python cli.py "input_pdfs/hanesher_february_2023.pdf"
python cli.py "input_pdfs/hanesher_february_2023.pdf" --output my_output
```

**Direct pipeline** (HTML output, no questions):

```bash
python main.py "input_pdfs/hanesher_february_2023.pdf"
```

Put the file path in quotes if it contains spaces or parentheses.

**Detailed output.** By default only short messages are shown. Add `--verbose` to see the full technical log and, when something fails, the full error details:

```bash
python cli.py "input_pdfs/hanesher_february_2023.pdf" --verbose
```

### Output file names

The CLI builds the file name from the report data:

```
<Company>_<Month>_<Year>_Card_<card number>.<html|pdf>
e.g. HaNesher_July_2023_Card_22_090.pdf
```

`main.py` names the output `<input file name>_transformed.<html|pdf>`.

---

## Configuration

`config.json` controls the generated data (section `synthetic_data`):

| Key | Meaning |
|-----|---------|
| `min_working_days` / `max_working_days` | Range of working days in a report |
| `start_tolerance_minutes` / `end_tolerance_minutes` | Allowed variation of clock-in / clock-out times |
| `duration_tolerance_minutes` | Allowed variation of the work duration |
| `break_tolerance_minutes` | Allowed variation of the break |
| `default_break_duration` | Default break, e.g. `"00:30"` |
| `year_range` | Range of years used for generated dates |

If the file is missing or invalid, built-in defaults are used.

---

## Running the Tests

```bash
pytest -v
```

The tests need no real PDFs and no Tesseract: the OCR text is replaced with sample text (`tests/sample_data.py`).

| File | What it covers |
|------|----------------|
| `tests/test_classifier.py` | `DocumentClassifier`: Type A, Type B, a file that is not a report (clear error), empty text, missing file |
| `tests/test_parsers.py` | `TypeAParser`, `TypeBParser` and `ParserFactory`: rows, summary, employee card, missing or unreadable summary values (errors), text without rows, missing file |
| `tests/test_attendance.py` | Both transformation strategies and `TransformationService`: standard flow, summary consistency, employee card, hourly rate rules, unusual inputs, errors, strategy selection and injection |

---

## Running the Project with Docker

Docker packages the project together with everything it needs (Python, the libraries, Tesseract and Poppler), so it runs the same way on any machine without manual installation.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running.

### Step-by-Step Instructions

1. **Open a terminal in the project root** (the folder containing the `Dockerfile` and `requirements.txt`).

2. **Build the image:**
   ```bash
   docker build -t attendance-system .
   ```

3. **Run the tests** (this is the default command of the image):
   ```bash
   docker run --rm attendance-system
   ```

4. **Process a PDF report.** Mount the input and output folders so the result is saved on your machine.

   *Windows PowerShell:*
   ```powershell
   docker run --rm -v "${PWD}/input_pdfs:/app/input_pdfs" -v "${PWD}/output:/app/output" attendance-system python main.py "input_pdfs/hanesher_february_2023.pdf"
   ```

   *macOS / Linux:*
   ```bash
   docker run --rm -v "$(pwd)/input_pdfs:/app/input_pdfs" -v "$(pwd)/output:/app/output" attendance-system python main.py "input_pdfs/hanesher_february_2023.pdf"
   ```

5. **Find the result** in the `output/` folder.

To use the interactive CLI inside the container, add `-it` and run `python cli.py` instead of `python main.py`:

```bash
docker run --rm -it -v "$(pwd)/input_pdfs:/app/input_pdfs" -v "$(pwd)/output:/app/output" attendance-system python cli.py "input_pdfs/hanesher_february_2023.pdf"
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `TesseractNotFoundError` | Install Tesseract and make sure it is on your `PATH`. |
| `PDFInfoNotInstalledError` | Install Poppler and make sure it is on your `PATH`. |
| An error message you do not understand | Run again with `--verbose` to see the full details. |
| `Input path is not an existing file` | Check the file name and wrap paths with spaces in quotes. |
| `ImportError: cannot import name 'build_report'` | Make sure `main.py` and `cli.py` are both the latest versions. |