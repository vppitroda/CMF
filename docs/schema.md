# Docsearch – schema spec (v0.1, POC)

Search flow: **Category → Property → Value (distinct values found) → text box (nearest match)**.
Values keep the unit as printed in the document. Customer names and dates are NOT fields.
Revisions fold to the latest by default (revision letter comes from the filename: `-0, -a, -b ...`).

## Categories (rule-based, from filename + page title)
| Category | Files in sample | Spec source |
|---|---|---|
| hyd_circuit | 24 | bottom-left spec box + termination (port) table  **<- implemented, verified** |
| bom_system (PP*) | 18 | BOM header + line rows |
| bom_cylinder (HA*/HAS*) | 10 | BOM title: `Ø<bore> x <rod> x <stroke> mm Stroke`, reuse list `(PPnnnnn / nn / nn)` |
| bom_spares (HQ*) | 7 | BOM rows |
| bom_valve_stand (HV*) | 3 | BOM rows |
| motor_datasheet | 11 | key/value sheet (kW, frame, V, rpm, poles, IE class, IP ...) |
| cylinder_ga_book | 5 | index page (part no., description with bore/rod/stroke, material code) |
| ga_drawing | 12 | varies; only some carry a materials/terminations block |
| jb_doc | 15 | cover page (enclosure size, supply/control voltage) |
| elec_load_list / io_list | 3 / 3 | tables |
| operation_writeup | 3 | free text |
| crs (xlsx) | 36 | comment/reply log; free text |
| cad_link_only | dwg/sldprt/easm/3D-pdf | linked to siblings by basename; not parsed |

## hyd_circuit properties (all verified on 24/24 drawings)
| Property | Type | Example | Coverage |
|---|---|---|---|
| customer_drawing_no | text | 400827-0603644 / NA | 24/24 |
| design_pressure | number list + unit | 250/300 Bar | 24/24 |
| working_pressure | number list + unit | 140/200/270 Bar | 24/24 |
| test_pressure | number + unit (+remark) | 315 Bar (By External Source) | 24/24 |
| working_fluid | text | Mineral ISO VG68 | 24/24 |
| main_pump_flow | number list + unit; sep `/` or `+` | 580/126/650 lpm, 215+215 lpm | 24/24 |
| rec_pump_flow | number + unit | ~108 lpm | 19/24 |
| open_loop_flow | number list + unit | 105+105 lpm | 5/24 (replaces rec_pump_flow on PP60057) |
| solenoid_voltage / instrumentation_voltage | number + unit V, AC/DC | 220 V AC, 24V DC | 24/24 |
| supply_voltage | number, unit V, AC/DC, frequency | 415 +/-10% V AC, 50Hz | 24/24 |
| tank_material | text | IS 2062 Gr.A | 21/24 (valve stands have no tank) |
| piping_material, fittings_flanges_material | text | Carbon Steel | 24/24 |
| pipe_dim_standard, pipe_material_standard, connection_type | text (2 lines joined) | DIN EN 10305-4 for Tubes ... | 24/24 |
| terminations[] | rows: name, size, connection, tube_pipe | P / 73 X 7.01 / SAE 2 1/2" / PIPE(Weldable) | 24/24 (186 rows) |
| notes[] | numbered free text | Electric motor is suitable to overloaded by 165% ... | 24/24 |

Each value stores page + bbox (PDF points, top-left origin) so the viewer can highlight it.
Port-table columns are read by header; their *meaning differs by template* (ELECON: size = tube OD x wall,
connection = SAE/G thread; SMS: size = thread/flange, connection = flange type, tube_pipe = Ø x wall).

## Extraction lessons (all baked into ingest/)
1. **Use pdfium (pypdfium2), not pdfminer/pdfplumber, for text.** pdfminer silently drops `/` and `%`
   ("250/300 Bar" -> "250300 Bar").
2. **Rotated pages:** 14/24 sheets are `/Rotate 270` (A0 stored portrait). Coordinates must be mapped to the
   displayed orientation or the spec box is not found.
3. **Overprinted bold:** text is drawn 2-3x; dedupe identical glyphs at the same position.
4. **Keep pdfium's reading order** (its space characters have bogus x); split into runs where position jumps.
   Runs ~= table cells.
5. **Scale thresholds with glyph height** (6.3 pt on A2 ... 13.1 pt on A0).
6. Revision-marker triangles inject lone lowercase letters; drop them. Mixed fractions lose their space
   (`21/2"` -> `2 1/2"`), repaired for sizes.
7. Match labels on space-stripped text (labels can be split across runs: "Control" + "Voltage for Solenoid").

## Verification so far
- 24/24 drawings parse; 15/17 fields at 100%, the other two explained (see coverage).
- Eyeballed against rendered drawings: PP60056-d, PP60057-d (ELECON), PP02123-d (SMS) - all fields and all
  ports matched.
- NOT yet done: a hand-verified ground-truth set (~20 drawings) for an objective accuracy number.

## Other categories (M5/M6) - deliberately coarse for the POC
| Category | Properties (filters) | Source |
|---|---|---|
| bom_cylinder | bore_mm, rod_mm, stroke_mm, application, options, make, reused_on | title block of the BOM; rows in `bom_lines` |
| bom_system | reservoir_litres | "Oil Reservoir : 2000 Ltrs" row |
| bom_spares | reused_on ("for systems") | title block `(PP60050 / 51 / 52)` |
| motor_datasheet | rated_output_kw, rated_speed_rpm, poles, frame, voltage_v, efficiency_class, protection_ip | label/value grid, page 1 |
| jb_doc | enclosure_size (W,H,D), supply_voltage, control_voltage | cover page; cylinder JBs have no enclosure |
| cylinder_ga_book | bore_mm (all bores in the book), projects | index page; each index row is a parts-list line |

Not filterable (no properties): ga_drawing, crs, cad, elec_load_list, io_list, operation_writeup, bom_valve_stand.
Those are `skipped` (never left `pending`) and wait for the M7 free-text search.

## GA drawings - investigation result (open question 4)
Of 12 GA PDFs: 2 are scanned images with no text layer (HAS90543, HAS90544); the 6 ELECON assembly GAs and HV11453/11455/11495
carry only a part list / weights; HV11452-b has a partial spec table with non-standard labels ("Working presure", no Design
pressure); only PP02123-b has the full block (design pressure, fluid, materials, user terminations, notes) and it has no
"Project Name" anchor. Supporting that would mean a second anchor and zone for one document, and the values duplicate the
circuit drawing of the same project. **Decision: GA drawings are link-only in the POC.** If needed later, reuse `circuit.py`
with a relaxed zone (it now stops at the bottom 40 % of the page) and an anchor on "Design Pressure".

## Known gaps / next
- title block (drawing no., description, format) - filename already gives project/type/rev.
- value canonicalisation for the filter list (e.g. "Minerial ISO VG68" typo vs "Mineral ISO VG46").
- GA drawings: spec block location is inconsistent; needs a closer look.
- BOM / cylinder / motor extractors, then Postgres load, API, UI.
