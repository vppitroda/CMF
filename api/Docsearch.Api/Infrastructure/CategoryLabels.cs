namespace Docsearch.Api.Infrastructure;

public static class CategoryLabels
{
    // display order of step 1 (the circuit drawings are the lead demo story)
    private static readonly (string Key, string Label)[] All =
    [
        ("hyd_circuit", "Hydraulic circuit"),
        ("bom_cylinder", "Cylinder BOM"),
        ("bom_system", "System BOM"),
        ("bom_spares", "Commissioning spares BOM"),
        ("bom_valve_stand", "Valve stand BOM"),
        ("ga_drawing", "GA drawing"),
        ("cylinder_ga_book", "Cylinder GA book"),
        ("jb_doc", "Junction box document"),
        ("motor_datasheet", "Motor datasheet"),
        ("elec_load_list", "Electrical load list"),
        ("io_list", "I/O list"),
        ("operation_writeup", "Operation write-up"),
        ("crs", "Comments review sheet"),
        ("cad", "CAD"),
    ];

    public static string For(string key) => All.FirstOrDefault(c => c.Key == key).Label ?? key;

    /// <summary>Position in the display order; unknown categories go last.</summary>
    public static int SortOrder(string key)
    {
        var i = Array.FindIndex(All, c => c.Key == key);
        return i < 0 ? int.MaxValue : i;
    }
}
