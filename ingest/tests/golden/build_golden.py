"""Ground truth for the hydraulic-circuit spec box (tests/golden/circuits.json is generated from this file).

Every value was transcribed by eye from a rendered crop of the drawing (tools/golden_crops.py makes the crops), written
BEFORE comparing with the extractor's output for that drawing. To review or correct a value: edit it here, run
    python build_golden.py circuits.json
and re-run the accuracy report. See README.md in this folder for the method and its limits.
"""
import json, sys

GOLD = []


def add(file, size, f, ports, notes):
    """f: spec fields as printed (absent fields simply omitted); ports: 'name|size|connection|tube_pipe' strings in
    reading order (left table, then right table); notes: [(no, text)]."""
    GOLD.append({
        "file": file, "sheet": size, "specs": f,
        "terminations": [dict(zip(("name", "size", "connection", "tube_pipe"), p.split("|"))) for p in ports],
        "notes": [{"no": n, "text": t} for n, t in notes],
    })


FIELDS = ("customer_drawing_no", "design_pressure", "working_pressure", "test_pressure", "working_fluid", "main_pump_flow",
          "rec_pump_flow", "open_loop_flow", "solenoid_voltage", "instrumentation_voltage", "supply_voltage", "tank_material",
          "piping_material", "fittings_flanges_material", "pipe_dim_standard", "pipe_material_standard", "connection_type")


def S(*vals):
    """Positionally build the spec dict in FIELDS order; use None for a field that is not on the drawing."""
    assert len(vals) == len(FIELDS), len(vals)
    return {k: v for k, v in zip(FIELDS, vals) if v is not None}


PDS = "DIN EN 10305-4 for Tubes up to 42mm OD. ANSI B36.10M for Pipes Sizes above42mm OD."
PMS = "DIN EN 10305-4 for Tubes. ASTM A106 B for Pipes."
CT = "Fitting with Wall form for internal Piping to be done up to 42mm OD. Flanges Connection in case of Pipe size above 42mm OD."
SUP = "415 +/-10% V AC, 50Hz +/-5%"
TP = "315 Bar ( By External Source )"
N_U = "U port of each Close loop pump shall be connected externally to L-Leakage line to eliminate air trapped in pump housing."
PP56_PORTS = ['P|73 X 7.01|SAE 2 1/2"|PIPE(Weldable)', 'T|88.9 X 5.49|SAE 3"|PIPE(Weldable)', 'Y,C|42 X 3|G 1 1/2"|TUBE(Weldable)',
              'W1, W2|60.3 X 3.91|SAE 2"|PIPE(Weldable)', 'A1,B1|38 X 5|G 1 1/2"|TUBE (Weldable)',
              'A2,B2|10X1.5|G 3/8"|TUBE (Weldable)', 'A3,B3,|88.9 X 11.10|SAE 3"|PIPE']

# --- g01 PP60056-0 (A0) ---
add("ELECON/01-PP60056-0-Hyd.Ckt (WT+WC+WG).pdf", "A0",
    S("NA", "250/300 Bar", "140/200/270 Bar", TP, "Minerial ISO VG68", "580/126/650 lpm", "NA", None,
      "24V DC", "110V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP56_PORTS,
    [("1", "SMPS is used to convert 110V AC to 24VDC."),
     ("2", "Electric motor is suitable to overloaded by 60% for 15 second in every 144 sec. cycle."),
     ("4", N_U)])
# --- g02 PP60056-a (A1) ---
add("ELECON/01-PP60056-a-Hyd.Ckt (WT+WC+WG).pdf", "A1",
    S("NA", "250/300 Bar", "140/200/270 Bar", TP, "Minerial ISO VG68", "580/126/650 lpm", "NA", None,
      "220V AC", "220V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP56_PORTS,
    [("1", "Electric motor is suitable to overloaded by 60% for 15 second in every 144 sec. cycle."), ("2", N_U)])
# --- g03 PP60056-b (A1) ---
add("ELECON/01-PP60056-b-Hyd.Ckt (WT+WC+WG).pdf", "A1",
    S("NA", "250/300 Bar", "140/200/270 Bar", TP, "Minerial ISO VG68", "580/126/650 lpm", "NA", None,
      "220V AC", "220V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP56_PORTS,
    [("1", "Electric motor is suitable to overloaded by 165% for 20 seconds in every 144 sec. cycle."), ("2", N_U)])

PP56_PORTS_C = ['P|73 X 7.01|SAE 2 1/2"|PIPE(Weldable)', 'T|88.9 X 5.49|SAE 3"|PIPE(Weldable)', 'Y,C|42 X 3|G 1 1/2"|TUBE(Weldable)',
                'W1, W2|60.3 X 3.91|SAE 2"|PIPE(Weldable)', 'A1,B1|38 X 5|G 1 1/2"|TUBE (Weldable)',
                'A2,B2|16 X 2|G 1/2"|TUBE (Weldable)', 'A3,B3,|88.9 X 11.10|SAE 3"|PIPE', 'L|25 X 3|G 1"|TUBE (Weldable)']
N165 = "Electric motor is suitable to overloaded by 165% for 20 seconds in every 144 sec. cycle."
# --- g04 PP60056-c (A2) ---
add("ELECON/01-PP60056-c-Hyd.Ckt (WT+WC+WG).pdf", "A2",
    S("NA", "250/300 Bar", "140/200/270 Bar", TP, "Minerial ISO VG68", "580/126/650 lpm", "NA", None,
      "220V AC", "220V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP56_PORTS_C, [("1", N165), ("2", N_U)])
# --- g05 PP60056-d (A1) ---
add("ELECON/01-PP60056-d-Hyd.Ckt (WT+WC+WG).pdf", "A1",
    S("NA", "250/300 Bar", "140/200/270 Bar", TP, "Minerial ISO VG68", "580/126/650 lpm", "NA", None,
      "220V AC", "220V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP56_PORTS_C, [("1", N165), ("2", N_U)])
# --- g06 PP60056-e (A2) ---
add("ELECON/01-PP60056-e-Hyd.Ckt (WT+WC+WG).pdf", "A2",
    S("NA", "250/300 Bar", "140/200/270 Bar", TP, "Minerial ISO VG68", "580/126/650 lpm", "NA", None,
      "220V AC", "220V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP56_PORTS_C, [("1", N165), ("2", N_U)])

N_IC = "Interconnecting Piping between HPU & Actuators is not in HIPL scope of supply."
N_ET = "End Termination shall be suitable for weldable connection."
# --- g07 PP60057-0 (A0) ---
add("ELECON/01-PP60057-0-Hyd.Ckt (SAC).pdf", "A0",
    S("NA", "300 Bar", "270 Bar", TP, "Minerial ISO VG68", "215+215 lpm", "NA", None,
      "24 V DC", "24 V DC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    ['A6 to A9|38 X 5|G 1 1/2"|TUBE (Weldable)', 'A3,B3,A4,B4|10 X 1.5|G 1/4"|TUBE (Weldable)',
     'P1,L|28 X 3|G 1"|TUBE (Weldable)', 'W1, W2|60.3 X 3.91|SAE 2"|PIPE (Weldable)',
     'C|42 X 3|G 1 1/2"|TUBE (Weldable)', 'B6 to B9|38 X 5|G 1 1/2"|TUBE (Weldable)',
     'A5,B5|38 X 5|G 1 1/2"|TUBE(Weldable)'],
    [("1", "Electric motor is suitable to overloaded by 125% for 15 second in every 144 sec. cycle."),
     ("2", N_IC), ("3", N_ET), ("4", N_U)])

PP57_PORTS = ['A6 to A9|38 X 5|G 1 1/2"|TUBE (Weldable)', 'A3,B3,A4,B4|10 X 1.5|G 1/4"|TUBE (Weldable)',
              'P1,L|28 X 3|G 1"|TUBE (Weldable)', 'W1, W2|60.3 X 3.91|SAE 2"|PIPE (Weldable)',
              'C|42 X 3|G 1 1/2"|TUBE (Weldable)', 'B6 to B9|38 X 5|G 1 1/2"|TUBE (Weldable)',
              'A5,B5|38 X 5|G 1 1/2"|TUBE(Weldable)']
N125 = "Electric motor is suitable to overloaded by 125% for 15 second in every 144 sec. cycle."
N135 = "Electric motor is suitable to overloaded by 135% for 15 second in every 144 sec. cycle."
# --- g08 PP60057-a (A1) ---
add("ELECON/01-PP60057-a-Hyd.Ckt (SAC).pdf", "A1",
    S("NA", "300 Bar", "270 Bar", TP, "Minerial ISO VG68", "215+215 lpm", None, "105+105 lpm",
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP57_PORTS, [("1", N125), ("2", N_IC), ("3", N_ET), ("4", N_U)])
# --- g09 PP60057-b (A1) ---
add("ELECON/01-PP60057-b-Hyd.Ckt (SAC).pdf", "A1",
    S("NA", "300 Bar", "270 Bar", TP, "Minerial ISO VG68", "215+215 lpm", None, "105+105 lpm",
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP57_PORTS, [("1", N135), ("2", N_IC), ("3", N_ET), ("4", N_U)])

PP57_PORTS8 = PP57_PORTS + ['A1,B1,A2,B2|48.3 X 7.14|SAE 1 1/2",6000PSI|PIPE (Weldable)']
# --- g10 PP60057-c (A2) ---
add("ELECON/01-PP60057-c-Hyd.Ckt (SAC).pdf", "A2",
    S("NA", "300 Bar", "270 Bar", TP, "Minerial ISO VG68", "215+215 lpm", None, "105+105 lpm",
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP57_PORTS8, [("1", N135), ("2", N_IC), ("3", N_ET), ("4", N_U)])
# --- g11 PP60057-d (A2) ---
add("ELECON/01-PP60057-d-Hyd.Ckt (SAC).pdf", "A2",
    S("NA", "300 Bar", "280 Bar", TP, "Minerial ISO VG68", "215+215 lpm", None, "105+105 lpm",
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP57_PORTS8, [("1", N135), ("2", N_IC), ("3", N_ET), ("4", N_U)])
# --- g12 PP60057-e (A2) ---
add("ELECON/01-PP60057-e-Hyd.Ckt (SAC).pdf", "A2",
    S("NA", "300 Bar", "280 Bar", TP, "Minerial ISO VG68", "215+215 lpm", None, "105+105 lpm",
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP57_PORTS8, [("1", N135), ("2", N_IC), ("3", N_ET), ("4", N_U)])

PP58_PORTS = ['A1,B1|2 1/2"SAE6000|Split Flange with Stub|Ø73 x 9.52(t)', 'A2,B2|G 1 1/2"|P.M.S.C.|Ø38 x 5(t)',
              'A3,B3,A4,B4|G 1/2"|P.M.S.C.|Ø16 X 2(t)', 'W1, W2|2"SAE3000|Split Flange with Stub|Ø60.3 X 3.91(t)',
              'L4|G 1/2"|P.M.S.C.|Ø18 X 2(t)', 'L5|G 3/4"|P.M.S.C.|Ø22 X 2(t)',
              'C|G 1 1/2"|P.M.S.C.|Ø42 X 3(t)', 'P1, P2|G 1/4"|P.M.S.C.|Ø10 X 2(t)',
              'A5,B5,A6,B6|1 1/2"SAE6000|Split Flange with Stub|Ø48.3 X 7.14(t)']
N58_20 = "Electric motor is suitable for 135% overload capacity for 20 second in every 144 sec. cycle."
N58_15 = "Electric motor is suitable for 135% overload capacity for 15 second in every 144 sec. cycle."
# --- g13 PP60058-0 (A0) ---
add("ELECON/01-PP60058-0-Hyd.Ckt (E+T).pdf", "A0",
    S("NA", "300 Bar", "230/250 Bar", TP, "Minerial ISO VG68", "490/125 lpm", "90 lpm", None,
      "24 V DC", "24 V DC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP58_PORTS, [("1", N58_20), ("2", N_IC), ("3", N_ET), ("4", N_U)])
# --- g14 PP60058-a (A1) ---
add("ELECON/01-PP60058-a-Hyd.Ckt (E+T).pdf", "A1",
    S("NA", "300 Bar", "230/250 Bar", TP, "Minerial ISO VG68", "490/125 lpm", "94 lpm", None,
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP58_PORTS, [("1", N58_20), ("2", N_IC), ("3", N_ET), ("4", N_U)])
# --- g15 PP60058-b (A1) ---
add("ELECON/01-PP60058-b-Hyd.Ckt (E+T).pdf", "A1",
    S("NA", "300 Bar", "230/250 Bar", TP, "Minerial ISO VG68", "490/125 lpm", "87 lpm", None,
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP58_PORTS, [("1", N58_15), ("2", N_IC), ("3", N_ET), ("4", N_U)])

N58_5 = "Accumulator 044.01 to be precharged to 80 bar in case of use of external brake for traverser hydro motor."
NOTES58 = [("1", N58_15), ("2", N_IC), ("3", N_ET), ("4", N_U), ("5", N58_5)]
# --- g16 PP60058-c (A1) ---
add("ELECON/01-PP60058-c-Hyd.Ckt (E+T).pdf", "A1",
    S("NA", "300 Bar", "230/250 Bar", TP, "Minerial ISO VG68", "490/125 lpm", "87 lpm", None,
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP58_PORTS, NOTES58)
# --- g17 PP60058-d (A2) ---
add("ELECON/01-PP60058-d-Hyd.Ckt (E+T).pdf", "A2",
    S("NA", "300 Bar", "230/250 Bar", TP, "Minerial ISO VG68", "490/125 lpm", "87 lpm", None,
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP58_PORTS, NOTES58)
# --- g18 PP60058-e (A2) ---
add("ELECON/01-PP60058-e-Hyd.Ckt (E+T).pdf", "A2",
    S("NA", "300 Bar", "255/265 Bar", TP, "Minerial ISO VG68", "496/125 lpm", "87 lpm", None,
      "220 V AC", "220 V AC", SUP, "IS 2062 Gr.A", "Carbon Steel", "Carbon Steel", PDS, PMS, CT),
    PP58_PORTS, NOTES58)

# ---- SMS (JSW Bellary valve stands / GCP) ----
PDS_SMS = "DIN EN 10305-4 for Tubes up to 42mm OD. ASME B36.10M for Pipes Sizes Above 42mm OD."
PMS_SMS = "DIN EN 10305-4 for Tubes. ASTM A106 Gr B for Pipes."
N_SMS = [("1", "Manifold Material - GGG40."),
         ("2", "Cabling of Instrument to JB will be through metal conduit only. Cable from Instrument to metal duct and JB to metal duct will be through flexible metal conduit."),
         ("3", "Suitable cable gland will be provided at both ends of connecting cable."),
         ("4", "All solenoids will be wired up with oil resistance cable to junction box mounted on the valve desk.")]
# --- g19 HV11452-c (A0) ---   (valve stand: the material row is "Valve Stand Material", there is no "Tank Material" label)
add("SMS/01-HV11452-c-Hyd.Ckt.pdf", "A0",
    S("400827-0603644", "230 Bar", "190 Bar", "285 Bar ( By External Source )", "Mineral ISO VG46", "N.A.", "-", None,
      "24V DC", "24V DC", "N.A.", None, "CARBON STEEL", "CARBON STEEL", PDS_SMS, PMS_SMS, CT),
    ['Pm|G1"|P.M.S.C.|Ø25x3(t)', 'Tm|G11/4"|P.M.S.C.|Ø35x3(t)', 'Lm|G1/2"|P.M.S.C.|Ø18x2(t)',
     'A1,A2,B1,B2|G1"|P.M.S.C.|Ø25x3(t)', 'A3,B3|G1"|P.M.S.C.|Ø25x3(t)'],
    N_SMS)
# --- g20 HV11495-c (A0) ---
add("SMS/01-HV11495-c-Hyd.Ckt.pdf", "A0",
    S("400827-0603644", "230 Bar", "190 Bar", "285 Bar ( By External Source )", "Mineral ISO VG46", "N.A.", "N.A.", None,
      "24V DC", "24 VDC", "N.A.", None, "Carbon Steel", "Carbon Steel", PDS_SMS, PMS_SMS, CT),
    ['P1,P2|G1/2"|P.M.S.C.|Ø16x2 (t)', 'T1,T2|G1/2"|P.M.S.C.|Ø18x2 (t)', 'P3|G3/4"|P.M.S.C.|Ø20x2.5 (t)',
     'T3|G1"|P.M.S.C.|Ø28x3 (t)', 'SDV X1~X2|G3/8"|P.M.S.C.|Ø10x2 (t)', 'RBV X1~X2|G3/8"|P.M.S.C.|Ø10x2 (t)',
     'RCV X17~X20|G3/8"|P.M.S.C.|Ø10x2 (t)', 'PSDVX1~X4|G3/8"|P.M.S.C.|Ø10x2 (t)', 'PSDVX17~X20|G3/8"|P.M.S.C.|Ø10x2 (t)'],
    N_SMS)

HV95_PORTS = ['P1,P2|G1/2"|P.M.S.C.|Ø16x2 (t)', 'T1,T2|G1/2"|P.M.S.C.|Ø18x2 (t)', 'P3|G3/4"|P.M.S.C.|Ø20x2.5 (t)',
              'T3|G1"|P.M.S.C.|Ø28x3 (t)', 'SDV X1~X2|G3/8"|P.M.S.C.|Ø10x2 (t)', 'RBV X1~X2|G3/8"|P.M.S.C.|Ø10x2 (t)',
              'RCV X17~X20|G3/8"|P.M.S.C.|Ø10x2 (t)', 'PSDVX1~X4|G3/8"|P.M.S.C.|Ø10x2 (t)', 'PSDVX17~X20|G3/8"|P.M.S.C.|Ø10x2 (t)']
# --- g21 HV11495-d (A1) ---
add("SMS/01-HV11495-d-Hyd.Ckt (As Built).pdf", "A1",
    S("400827-0603644", "230 Bar", "190 Bar", "285 Bar ( By External Source )", "Mineral ISO VG46", "N.A.", "N.A.", None,
      "24V DC", "24 VDC", "N.A.", None, "Carbon Steel", "Carbon Steel", PDS_SMS, PMS_SMS, CT),
    HV95_PORTS, N_SMS)
PP02_PORTS = ['Pm|1 1/2"SAE6000|Split Flange with Stub|Ø48.3x7.14 (t)', 'Tac|G11/4"|P.M.S.C.|Ø35x3 (t)',
              'Tm|2"SAE3000|Split Flange with Stub|Ø60.3x3.91 (t)', 'Wi, Wo|DN50|SORF,ANSIB16.5,#150|Ø60.3x3.91 (t)',
              'Lm|G3/4"|P.M.S.C.|Ø22x3 (t)']
# --- g22 PP02123-c (A0) ---
add("SMS/01-PP02123-c-Hyd.Ckt.pdf", "A0",
    S("400827-0603644", "230 Bar", "190 Bar", "285 Bar ( By External Source )", "Mineral ISO VG46", "250 lpm", "~108 lpm", None,
      "24V DC", "24 VDC", "415V(+10%/-15%), 50Hz(+/-6%)", "IS 2062 E250A", "Carbon Steel", "Carbon Steel", PDS_SMS, PMS_SMS, CT),
    PP02_PORTS, N_SMS)
# --- g23 PP02123-d (A1) ---
add("SMS/01-PP02123-d-Hyd.Ckt (As Built).pdf", "A1",
    S("400827-0603644", "230 Bar", "190 Bar", "285 Bar ( By External Source )", "Mineral ISO VG46", "250 lpm", "~108 lpm", None,
      "24V DC", "24 VDC", "415V(+10%/-15%), 50Hz(+/-6%)", "IS 2062 E250A", "Carbon Steel", "Carbon Steel", PDS_SMS, PMS_SMS, CT),
    PP02_PORTS, N_SMS)

if __name__ == "__main__":
    json.dump({
        "description": "Ground truth for hyd_circuit spec boxes: read by eye from rendered crops of each drawing, written BEFORE "
                       "comparing with the extractor. See README.md in this folder for the method and its limits.",
        "drawings": GOLD,
    }, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(len(GOLD), "drawings,", sum(len(g["specs"]) for g in GOLD), "spec fields,",
          sum(len(g["terminations"]) for g in GOLD), "port rows,", sum(len(g["notes"]) for g in GOLD), "notes")
