"""Property registry per category: seeds the `properties` table that drives step 2 of the UI."""
from __future__ import annotations

from .circuit import LABELS, NUMERIC

LABEL_TEXT = {
    "customer_drawing_no": "Customer drawing no.",
    "design_pressure": "Design pressure",
    "working_pressure": "Working pressure",
    "test_pressure": "Test pressure",
    "working_fluid": "Working fluid",
    "main_pump_flow": "Main pump flow",
    "rec_pump_flow": "Recirculation pump flow",
    "open_loop_flow": "Open loop flow",
    "solenoid_voltage": "Solenoid control voltage",
    "instrumentation_voltage": "Instrumentation voltage",
    "supply_voltage": "Supply voltage",
    "tank_material": "Tank material",
    "piping_material": "Piping material",
    "fittings_flanges_material": "Fittings / flanges material",
    "pipe_dim_standard": "Tube/pipe dimensional standard",
    "pipe_material_standard": "Tube/pipe material standard",
    "connection_type": "Type of connection",
}

# category -> [(prop_key, label, data_type)] in display order. project_name is deliberately not a property.
PROPERTIES: dict[str, list[tuple[str, str, str]]] = {
    "hyd_circuit": [
        (k, LABEL_TEXT[k], "number" if k in NUMERIC else "text") for k in LABELS if k != "project_name"
    ],
    # BOM title block (bom.py). Numbers are mm / litres as printed.
    "bom_cylinder": [
        ("bore_mm", "Bore (mm)", "number"),
        ("rod_mm", "Rod (mm)", "number"),
        ("stroke_mm", "Stroke (mm)", "number"),
        ("application", "Application", "text"),
        ("options", "Options", "text"),
        ("make", "Make", "text"),
        ("reused_on", "Reused on (systems)", "text"),
    ],
    "bom_system": [("reservoir_litres", "Oil reservoir (litres)", "number")],
    "bom_spares": [("reused_on", "For systems", "text")],
    # POC: only what an engineer filters on, not every field on the sheet
    "motor_datasheet": [
        ("rated_output_kw", "Rated output (kW)", "number"),
        ("rated_speed_rpm", "Rated speed (rpm)", "number"),
        ("poles", "Poles", "number"),
        ("frame", "Frame", "text"),
        ("voltage_v", "Voltage (V)", "number"),
        ("efficiency_class", "Efficiency class", "text"),
        ("protection_ip", "Protection (IP)", "text"),
    ],
    "jb_doc": [
        ("enclosure_size", "Enclosure W x H x D (mm)", "number"),
        ("supply_voltage", "Supply voltage (V)", "number"),
        ("control_voltage", "Control voltage (V)", "number"),
    ],
    "cylinder_ga_book": [
        ("bore_mm", "Cylinder bores in the book (mm)", "number"),
        ("projects", "Projects covered", "text"),
    ],
}
