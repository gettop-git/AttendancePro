# Decision Log

This file records the main design decisions of the Attendance Report System: what the options were, what was chosen, and why. Each entry has the same four parts.

| # | Decision |
|---|----------|
| 1 | Layered package structure |
| 2 | The output is a new, generated report |
| 3 | Strategy pattern for transformation |
| 4 | Factory for choosing the parser |
| 5 | Keyword scoring to classify documents |
| 6 | `main.py` only orchestrates the pipeline |
| 7 | Objects are created in `main.py` and passed in |
| 8 | All rule numbers live in configuration |
| 9 | Fail with a clear error instead of guessing |
| 10 | Technical logs hidden unless `--verbose` |
| 11 | One CLI that reuses the pipeline |
| 12 | PDF is produced from the HTML |
| 13 | Tests use sample text, not real PDFs |
| 14 | Docker next to a local setup |
| 15 | Read the PDF's own text first, OCR only as a fallback |

---

## 1. Layered package structure

**Options**
- One large script that reads, transforms and writes.
- Separate packages by responsibility: `domain`, `parsers`, `transformation`, `generators`.

**Decision:** separate packages. `parsers`, `transformation` and `generators` depend only on `domain`, never on each other.

**Why:** each part can be understood, tested and replaced on its own. A change in the HTML layout cannot break the parsing.

**Trade-off:** more files, and a coordinating file (`main.py`) is needed to connect them.

---

## 2. The output is a new, generated report

**Options**
- Copy the source report and edit some of its values.
- Use the source only to learn its limits (working hours, break length, type) and generate a new report from them.

**Decision:** generate a new report. The source defines constraints; dates, shifts and the employee card are generated independently.

**Why:** the project is a simulator of employee reports in a changing format. A new report should be plausible and consistent, not a slightly altered copy of the original.

**Trade-off:** the result is random, so tests check properties (consistent totals, valid rows) and not exact values.

---

## 3. Strategy pattern for transformation

**Options**
- One function with `if report_type == ...` branches.
- One strategy class per report type, selected by `TransformationService`.

**Decision:** one strategy class per type (`TypeATransformationStrategy`, `TypeBTransformationStrategy`).

**Why:** the two types follow different rules (Type A has overtime columns and a bottom summary; Type B has an hourly rate and a top summary). Separate classes keep each rule set readable, and a new type means a new class, without editing the existing ones.

**Trade-off:** some similar code exists in both classes; shared logic lives in `BaseTransformationStrategy`.

---

## 4. Factory for choosing the parser

**Options**
- Create `TypeAParser` or `TypeBParser` directly with `if/else` where needed.
- A `ParserFactory` with a registry that maps a type name to a parser class.

**Decision:** `ParserFactory`.

**Why:** the choice of parser is in one place. Adding a type means adding one line to the registry. An unsupported type produces one clear error.

---

## 5. Keyword scoring to classify documents

**Options**
- Decide by the file name.
- Decide by the first line of the document.
- Count distinctive keywords of each type in the OCR text and compare the scores.

**Decision:** keyword scoring (for example `hanesher`, `manpower`, `100%` for Type A; `employee card:`, `hourly rate` for Type B).

**Why:** file names are unreliable, and a single line is fragile when OCR makes a mistake. Several independent signals are more robust.

**Related decision:** if **neither** type scores any point, the classifier raises an error and does not default to Type B. A file that is not an attendance report must be rejected, not guessed.

---

## 6. `main.py` only orchestrates the pipeline

**Options**
- Put all the steps inside one long function.
- Small named steps (`validate_input`, `classify`, `parse`, `transform`, rendering) and a short function that calls them in order.

**Decision:** small steps. `main.py` knows the order of the stations but contains none of their logic.

**Why:** the file reads like a table of contents of the system. `build_report()` can be reused by `cli.py`.

---

## 7. Objects are created in `main.py` and passed in

**Options**
- Each class creates the objects it needs (for example the service creates its own strategies).
- The caller creates them and passes them in (dependency injection).

**Decision:** `main.py` creates the strategies and the OCR extractor and passes them to `TransformationService` and `ParserFactory`. When nothing is passed, sensible defaults are used.

**Why:** the behavior can be changed from outside without editing the internals. In tests the OCR is replaced by fixed text, so Tesseract is not needed.

---

## 8. All rule numbers live in configuration

**Options**
- Keep numbers (tolerances, intervals, retry counts, vacation days) inside the code, next to where they are used.
- Put them in `config.json`, read by `config.py`, with defaults in `config.py`.

**Decision:** configuration. The defaults are defined once, in `config.py`; `config.json` overrides them. If the file is missing or invalid, the defaults are used.

**Why:** a rule can be changed in one place without touching the logic, and the same number is never defined in several files.

**Note:** the old default hourly rate was removed (see decision 9).

---

## 9. Fail with a clear error instead of guessing

**Options**
- When a value is missing or unreadable, use a default (for example 0) and continue.
- Stop with a clear error that says what is missing.

**Decision:** stop with an error. This applies to summary values, the hourly rate, the employee card, the report month, and files that are not attendance reports.

**Why:** a silent default produces a report that looks valid but contains wrong data, and the user does not know. A clear message lets the user fix the input.

**How it is built:** a small hierarchy of exceptions (`AttendanceSystemError` as the base, with `InvalidReportDataError` and `TransformationStrategyError`), no bare `except`, and no empty `except` blocks. Where continuing is harmless (for example, the source month cannot be read, so it is simply not excluded), a warning is logged.

**Trade-off:** a slightly damaged PDF that used to produce a report now produces an error.

---

## 10. Technical logs hidden unless `--verbose`

**Options**
- Always show all log lines.
- Show only short messages and errors by default, with a flag for the full details.

**Decision:** short messages by default; `--verbose` shows the technical log and the full error details (traceback).

**Why:** a normal user needs a clear message, not 12 lines of traceback. A developer can still get everything with one flag.

**Detail:** logging is configured only when the program is run (`setup_logging()` inside the `__main__` guard or the CLI), not when a module is imported.

---

## 11. One CLI that reuses the pipeline

**Options**
- A CLI that has its own copy of the parsing and transformation steps.
- A CLI that calls `build_report()` from `main.py` and only adds what is specific to it.

**Decision:** reuse. `cli.py` handles the arguments (`argparse`), the question about the export format and the output file name, and nothing else.

**Why:** the pipeline exists in one place. A change to it cannot be forgotten in a second copy.

---

## 12. PDF is produced from the HTML

**Options**
- Draw the PDF separately with a PDF library.
- Render the HTML once and convert it to PDF.

**Decision:** convert the HTML to PDF.

**Why:** there is only one layout to maintain, and the two outputs always look the same.

**Trade-off:** the PDF depends on what the HTML converter supports.

---

## 13. Tests use sample text, not real PDFs

**Options**
- Test with real PDF files and a real OCR run.
- Replace the OCR with fixed sample text (`tests/sample_data.py`).

**Decision:** sample text.

**Why:** the tests are fast, run on any machine without Tesseract, and give the same result every time. They cover the classifier, the parsers and the transformation, including the error cases.

**In addition:** `test_sample_pdfs.py` runs the real PDFs from `input_pdfs/` through the pipeline, so the sample files are covered too.

**Trade-off:** the OCR step is tested only with fake page images. A scanned PDF should be checked manually.

---

## 14. Docker next to a local setup

**Options**
- Only a local installation, with instructions.
- A `Dockerfile` as an additional way to run the project.

**Decision:** both. The image installs Python, the libraries, Tesseract and Poppler.

**Why:** the project depends on two programs outside Python (Tesseract and Poppler). Docker lets anyone run it without installing them. `.dockerignore` and `.gitignore` keep local files (`.venv`, `.idea`) out of the image and the repository.

---

## 15. Read the PDF's own text first, OCR only as a fallback

**Options**
- OCR every PDF with Tesseract.
- Read the text stored inside the PDF, and use OCR only when there is none.

**Decision:** read the embedded text first (`pdftotext -layout`, part of Poppler), and fall back to OCR for PDFs with fewer than 20 words of embedded text.

**Why:** OCR on the real sample files misread the Type B summary: the white-on-blue column names were not recognized, and the currency sign hid the first digit of the hourly rate (`30.65` was read as `0.65`). A wrong number that looks valid is worse than an error. The embedded text is exact, and `-layout` keeps each table row on one line, which is what the parsers expect.

**Trade-off:** one more external program is used. Poppler is already required by `pdf2image`, so nothing new has to be installed. If `pdftotext` is missing, a warning is logged and OCR is used.

**Related:** the Type B parser reads the summary as a table (a header line with the four column names and one line with the four values), because that is the layout of the real files.