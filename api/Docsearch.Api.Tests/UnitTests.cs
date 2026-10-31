using Docsearch.Api.Infrastructure;

namespace Docsearch.Api.Tests;

public class CanonicalizerTests
{
    // must agree with ingest/tests/test_aliases.py
    [Theory]
    [InlineData("Minerial ISO VG68", "mineral iso vg68")]
    [InlineData("Mineral ISO VG 68", "mineral iso vg68")]
    [InlineData("315 Bar ( By External Source )", "315 bar")]
    [InlineData("250/300  Bar", "250/300 bar")]
    [InlineData("N.A.", "na")]
    [InlineData("-", "na")]
    [InlineData("IS 2062 Gr.A", "is 2062 gr.a")]
    [InlineData("Mineral ISO VG-68", "mineral iso vg68")]
    [InlineData("230Bar", "230 bar")]
    [InlineData("230  bar", "230 bar")]
    [InlineData("105+105lpm", "105+105 lpm")]
    [InlineData("250 / 300 Bar", "250/300 bar")]
    [InlineData("215 + 215 lpm", "215+215 lpm")]
    [InlineData("N/A", "na")]
    [InlineData("n.a", "na")]
    [InlineData("415 +/-10% V AC, 50Hz", "415 +/-10% v ac, 50 hz")]
    public void Canon_matches_the_python_loader(string raw, string expected) =>
        Assert.Equal(expected, Canonicalizer.Canon(raw));

    // same cases as ingest/tests/test_bom.py::test_part_no_canon
    [Theory]
    [InlineData("2103-01-18.00 HDN", "2103011800HDN")]
    [InlineData("TPN00041", "TPN00041")]
    [InlineData("tpn 0004l", "TPN0004L")]
    [InlineData("RM-IOO1", "RM1001")]
    public void PartNo_matches_the_python_loader(string raw, string expected) =>
        Assert.Equal(expected, Canonicalizer.PartNo(raw));

    [Theory]
    [InlineData("TPN0O041", "TPN00041")]          // letter O typed for zero
    [InlineData("2103-01-18.00", "2103011800")]
    [InlineData("4we6", "4WE6")]
    [InlineData("ball valve", null)]               // ordinary words must not be O/I-folded
    [InlineData("ab", null)]
    [InlineData("pressure relief", null)]
    public void AsPartNo_only_treats_part_number_looking_queries_as_part_numbers(string q, string? expected) =>
        Assert.Equal(expected, Canonicalizer.AsPartNo(q));
}

public class ConnectionStringTests
{
    [Fact]
    public void Url_form_is_converted()
    {
        var cs = ConnectionStrings.ToNpgsql("postgresql://docsearch:p%40ss@localhost:5432/docsearch");
        var b = new Npgsql.NpgsqlConnectionStringBuilder(cs);
        Assert.Equal(("localhost", 5432, "docsearch", "docsearch", "p@ss"), (b.Host, b.Port, b.Database, b.Username, b.Password));
    }

    [Fact]
    public void Key_value_form_is_passed_through() =>
        Assert.Equal("Host=x;Database=y", ConnectionStrings.ToNpgsql("Host=x;Database=y"));
}
