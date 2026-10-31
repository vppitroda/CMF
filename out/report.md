# Docsearch extraction report

## Documents per category

| category | files | duplicates | ok | partial | failed | skipped (not parsed) | pending |
|---|---|---|---|---|---|---|---|
| bom_cylinder | 10 | 0 | 10 | 0 | 0 | 0 | 0 |
| bom_spares | 7 | 0 | 7 | 0 | 0 | 0 | 0 |
| bom_system | 18 | 0 | 18 | 0 | 0 | 0 | 0 |
| bom_valve_stand | 3 | 0 | 3 | 0 | 0 | 0 | 0 |
| cad | 41 | 0 | 0 | 0 | 0 | 41 | 0 |
| crs | 36 | 0 | 0 | 0 | 0 | 36 | 0 |
| cylinder_ga_book | 5 | 0 | 5 | 0 | 0 | 0 | 0 |
| elec_load_list | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| ga_drawing | 12 | 0 | 0 | 0 | 0 | 12 | 0 |
| hyd_circuit | 24 | 1 | 23 | 0 | 0 | 1 | 0 |
| io_list | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| jb_doc | 15 | 0 | 15 | 0 | 0 | 0 | 0 |
| motor_datasheet | 11 | 0 | 11 | 0 | 0 | 0 | 0 |
| operation_writeup | 3 | 0 | 0 | 0 | 0 | 3 | 0 |

## Parse success (target: 95 % of parsed documents `ok`)

| category | parsed | ok | rate | target |
|---|---|---|---|---|
| bom_cylinder | 10 | 10 | 100.0 % | met |
| bom_spares | 7 | 7 | 100.0 % | met |
| bom_system | 18 | 18 | 100.0 % | met |
| bom_valve_stand | 3 | 3 | 100.0 % | met |
| cylinder_ga_book | 5 | 5 | 100.0 % | met |
| hyd_circuit | 23 | 23 | 100.0 % | met |
| jb_doc | 15 | 15 | 100.0 % | met |
| motor_datasheet | 11 | 11 | 100.0 % | met |

## Field coverage: hyd_circuit (23 documents)

| property | documents |
|---|---|
| customer_drawing_no | 23/23 |
| design_pressure | 23/23 |
| working_pressure | 23/23 |
| test_pressure | 23/23 |
| working_fluid | 23/23 |
| main_pump_flow | 23/23 |
| rec_pump_flow | 18/23 |
| open_loop_flow | 5/23 |
| solenoid_voltage | 23/23 |
| instrumentation_voltage | 23/23 |
| supply_voltage | 23/23 |
| tank_material | 20/23 |
| piping_material | 23/23 |
| fittings_flanges_material | 23/23 |
| pipe_dim_standard | 23/23 |
| pipe_material_standard | 23/23 |
| connection_type | 23/23 |

## Field coverage: bom_cylinder (10 documents)

| property | documents |
|---|---|
| bore_mm | 10/10 |
| rod_mm | 10/10 |
| stroke_mm | 10/10 |
| application | 10/10 |
| options | 8/10 |
| make | 9/10 |
| reused_on | 9/10 |

## Field coverage: bom_system (18 documents)

| property | documents |
|---|---|
| reservoir_litres | 18/18 |

## Field coverage: bom_spares (7 documents)

| property | documents |
|---|---|
| reused_on | 7/7 |

## Field coverage: motor_datasheet (11 documents)

| property | documents |
|---|---|
| rated_output_kw | 11/11 |
| rated_speed_rpm | 11/11 |
| poles | 11/11 |
| frame | 11/11 |
| voltage_v | 11/11 |
| efficiency_class | 11/11 |
| protection_ip | 11/11 |

## Field coverage: jb_doc (15 documents)

| property | documents |
|---|---|
| enclosure_size | 9/15 |
| supply_voltage | 15/15 |
| control_voltage | 15/15 |

## Field coverage: cylinder_ga_book (5 documents)

| property | documents |
|---|---|
| bore_mm | 5/5 |
| projects | 5/5 |

## Partial / failed documents

none

## Unclassified files

none

## Accuracy against the golden set (23 circuit drawings)

Golden values were read by eye from rendered crops (see `ingest/tests/golden/README.md`); scoring rules are in `docsearch_ingest/golden.py`.

| measure | correct / total | accuracy |
|---|---|---|
| spec fields (all drawings) | 365 / 365 | 100.0 % |
| drawings with every field correct | 23 / 23 | 100.0 % |
| fields extracted that the drawing does not have | 0 | |
| port rows (exact on all 4 columns) | 177 / 177 | 100.0 % |
| port rows extracted that are not on the drawing | 0 | |
| notes (exact text) | 84 / 84 | 100.0 % |
| notes with the right words but junk appended | 0 | |

### Per field

| field | correct / present | accuracy |
|---|---|---|
| connection_type | 23 / 23 | 100.0 % |
| customer_drawing_no | 23 / 23 | 100.0 % |
| design_pressure | 23 / 23 | 100.0 % |
| fittings_flanges_material | 23 / 23 | 100.0 % |
| instrumentation_voltage | 23 / 23 | 100.0 % |
| main_pump_flow | 23 / 23 | 100.0 % |
| open_loop_flow | 5 / 5 | 100.0 % |
| pipe_dim_standard | 23 / 23 | 100.0 % |
| pipe_material_standard | 23 / 23 | 100.0 % |
| piping_material | 23 / 23 | 100.0 % |
| rec_pump_flow | 18 / 18 | 100.0 % |
| solenoid_voltage | 23 / 23 | 100.0 % |
| supply_voltage | 23 / 23 | 100.0 % |
| tank_material | 20 / 20 | 100.0 % |
| test_pressure | 23 / 23 | 100.0 % |
| working_fluid | 23 / 23 | 100.0 % |
| working_pressure | 23 / 23 | 100.0 % |

### By customer

| customer | fields | port rows |
|---|---|---|
| ELECON | 288 / 288 (100.0 %) | 144 / 144 (100.0 %) |
| SMS | 77 / 77 (100.0 %) | 33 / 33 (100.0 %) |

### By sheet size

| sheet size | fields | port rows |
|---|---|---|
| A0 | 94 / 94 (100.0 %) | 42 / 42 (100.0 %) |
| A1 | 159 / 159 (100.0 %) | 77 / 77 (100.0 %) |
| A2 | 112 / 112 (100.0 %) | 58 / 58 (100.0 %) |

### Field mismatches

none

### Port-row mismatches

none

### Notes missing or wrong

