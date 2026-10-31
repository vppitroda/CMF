namespace Docsearch.Api.Infrastructure;

public static class CategoryLabels
{
    static readonly Dictionary<string, string> Labels = new()
    {
        ["hyd_circuit"] = "Hydraulic circuit",
        ["bom_system"] = "System BOM",
        ["bom_cylinder"] = "Cylinder BOM",
        ["bom_spares"] = "Commissioning spares BOM",
        ["bom_valve_stand"] = "Valve stand BOM",
        ["ga_drawing"] = "GA drawing",
        ["cylinder_ga_book"] = "Cylinder GA book",
        ["jb_doc"] = "Junction box document",
        ["motor_datasheet"] = "Motor datasheet",
        ["elec_load_list"] = "Electrical load list",
        ["io_list"] = "I/O list",
        ["operation_writeup"] = "Operation write-up",
        ["crs"] = "Comments review sheet",
        ["cad"] = "CAD",
    };

    public static string For(string key) => Labels.TryGetValue(key, out var l) ? l : key;
}
