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
    public void Canon_matches_the_python_loader(string raw, string expected) =>
        Assert.Equal(expected, Canonicalizer.Canon(raw));
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
