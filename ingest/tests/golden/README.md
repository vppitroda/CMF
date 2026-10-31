# Golden set for the hydraulic-circuit extractor

`circuits.json` holds the ground truth for 23 drawings (every distinct `Hyd.Ckt` PDF; the `- Copy.pdf` is an identical
duplicate): 365 spec fields, 177 port-table rows and 84 notes. It is generated from `build_golden.py`, where every value is
written out explicitly so it can be reviewed in a diff.

## How it was made (and why the number means something)

1. `tools/golden_crops.py` renders, for each drawing, a crop of the spec/termination tables and a crop of the notes block at a
   readable size. It uses the extractor only to *locate* the box; no extracted value appears in the crops.
2. Each drawing's values were read from those crops and written into `build_golden.py` **before** the extractor's output for that
   drawing was looked at.
3. `docsearch_ingest/golden.py` then scored the extractor against the file. Every disagreement was re-inspected at 5x zoom
   to decide who was wrong.

## Who read it: this is not a human sign-off

The transcription was done by Claude reading images, not by an engineer. That makes it independent of the extractor (pixels vs
the PDF text layer) but not infallible. Known weakness: **a reader tends to autocorrect typos**. The first pass disagreed with the
extractor on 11 fields and 6 port rows, and **all 17 turned out to be the reader's mistakes**, not the extractor's:

| what | I read | printed (confirmed at 5x zoom) |
|---|---|---|
| `working_fluid` on 10 drawings (PP60057-a..e, PP60058-a..e) | `Mineral ISO VG68` | `Minerial ISO VG68` (a typo in the drawings) |
| `customer_drawing_no` of HV11495-c | `400827-0603679` | `400827-0603644` |
| PP60058 port `A3,B3,A4,B4` tube/pipe, 6 drawings | `Ø16 x 2(t)` | `Ø16 X 2(t)` |

Please have an engineer spot-check the file (run `tools/golden_crops.py`, compare a few crops with `build_golden.py`),
especially any value where a typo or a look-alike character (O/0, I/1, x/X) would be easy to normalise by eye.

## Scoring rules

Defined in `docsearch_ingest/golden.py`: whitespace-insensitive exact match for fields and for all four columns of a port row;
an absent field must stay absent; notes match by number, and "right words plus junk appended" counts as wrong.

## Result (see `out/report.md` for the live numbers)

fields 365/365, port rows 177/177, notes 84/84, no invented fields or rows.

## Limits of that result

* **The notes were tuned on this set.** The first scoring found real extractor bugs in notes (the title block's dates and
  initials glued onto the last note; notes below the "Termination details" heading cut off - 5 notes on PP60058-c/d/e, 4 on the
  SMS drawings). They were fixed in `circuit.py` and the score rose from 36 % to 100 %. Fields and port rows needed **no**
  extractor change, so those two numbers are the cleaner evidence.
* **23 drawings are only six layouts.** They are revisions of PP60056/57/58 (ELECON) and HV11452, HV11495, PP02123 (SMS), so
  they are strongly correlated. 100 % here says nothing about a template the sample does not contain (scope open question 2).
* Only `hyd_circuit` has a golden set. BOMs, motor datasheets, JB covers and cylinder books are covered by unit tests and
  spot checks (e.g. the BOM bboxes are checked against pdfplumber), not by a measured accuracy.

## Extending it

Add a drawing: run `tools/golden_crops.py`, read the crops, add an `add(...)` call to `build_golden.py`, regenerate with
`python build_golden.py circuits.json`, then `python -m pytest tests/test_golden.py`.
