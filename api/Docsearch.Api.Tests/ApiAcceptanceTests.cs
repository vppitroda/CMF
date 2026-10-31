using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace Docsearch.Api.Tests;

/// <summary>
/// Acceptance tests (scope.md §10) against the real API + the ingested Postgres.
/// Prerequisite: docker compose up -d, then scan/extract/load (see README). DOCSEARCH_* come from appsettings.json.
/// </summary>
public class ApiAcceptanceTests(WebApplicationFactory<Program> factory) : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _http = factory.CreateClient();

    private async Task<JsonElement> GetJson(string url)
    {
        var res = await _http.GetAsync(url);
        res.EnsureSuccessStatusCode();
        return JsonDocument.Parse(await res.Content.ReadAsStringAsync()).RootElement;
    }

    private async Task<List<JsonElement>> Results(string query) =>
        (await GetJson($"/api/search?{query}")).GetProperty("results").EnumerateArray().ToList();

    private const string Dp = "category=hyd_circuit&property=design_pressure";

    [Fact]
    public async Task AT1_near_223_ranks_230_bar_then_250_300_then_300()
    {
        var r = await Results($"{Dp}&value=223");
        var top3 = r.Take(3).Select(x => (x.GetProperty("matchedValue").GetString(), x.GetProperty("delta").GetDecimal())).ToList();
        Assert.All(top3, t => Assert.Equal(("230 Bar", 7m), t));
        Assert.Equal(new[] { "01-HV11452-c", "01-HV11495-d", "01-PP02123-d" },
            r.Take(3).Select(x => x.GetProperty("fileName").GetString()![..12]).Order());
        Assert.Equal(("250/300 Bar", 27m), (r[3].GetProperty("matchedValue").GetString(), r[3].GetProperty("delta").GetDecimal()));
        Assert.Equal("300 Bar", r[4].GetProperty("matchedValue").GetString());
        Assert.All(r, x => Assert.True(x.GetProperty("isLatest").GetBoolean()));
    }

    [Fact]
    public async Task AT2_hyd_circuit_has_all_17_properties()
    {
        var props = await GetJson("/api/categories/hyd_circuit/properties");
        Assert.Equal(17, props.GetArrayLength());
    }

    [Fact]
    public async Task AT2_bom_cylinder_has_its_title_properties()
    {
        var keys = (await GetJson("/api/categories/bom_cylinder/properties")).EnumerateArray()
            .Select(p => p.GetProperty("key").GetString()).ToList();
        Assert.Subset(keys.ToHashSet(), new HashSet<string?> { "bore_mm", "rod_mm", "stroke_mm", "make" });
    }

    [Fact]
    public async Task AT3_bore_80_returns_the_80x56_cylinders_first_with_their_reuse_lists()
    {
        var r = await Results("category=bom_cylinder&property=bore_mm&value=80");
        var top = r.Take(4).ToList();
        Assert.All(top, x => Assert.Equal(0m, x.GetProperty("delta").GetDecimal()));
        Assert.Equal(new[] { "HA90471", "HAS90264", "HAS90269", "HAS90545" },
            top.Select(x => x.GetProperty("projectCode").GetString()).Order());
        Assert.True(r[4].GetProperty("delta").GetDecimal() > 0);

        string[] Reused(string code) => top.Single(x => x.GetProperty("projectCode").GetString() == code)
            .GetProperty("reusedOn").EnumerateArray().Select(e => e.GetString()!).ToArray();
        Assert.Equal(new[] { "PP60050", "PP60053", "PP60056" }, Reused("HAS90264"));   // "(PP60050 / 53 / 56)" expanded
        Assert.Equal(new[] { "PP60052", "PP60055", "PP60058" }, Reused("HAS90545"));
        Assert.Empty(Reused("HA90471"));                                               // its title carries no list
    }

    [Fact]
    public async Task A_project_code_is_found_inside_a_reuse_list()
    {
        var r = await Results("category=bom_cylinder&property=reused_on&value=PP60056");
        Assert.Equal(new[] { "HAS90264", "HAS90265", "HAS90266", "HAS90267", "HAS90543" },
            r.Where(x => x.GetProperty("reusedOn").EnumerateArray().Any(e => e.GetString() == "PP60056"))
             .Select(x => x.GetProperty("projectCode").GetString()).Order());
    }

    [Fact]
    public async Task Bom_document_exposes_its_rows_with_page_and_bbox()
    {
        var hit = (await Results("category=bom_cylinder&property=bore_mm&value=160")).First();
        var doc = await GetJson($"/api/documents/{hit.GetProperty("documentId").GetInt64()}");
        var lines = doc.GetProperty("bomLines").EnumerateArray().ToList();
        Assert.Equal(12, lines.Count);
        Assert.Equal("121.00", lines[0].GetProperty("itemNo").GetString());
        Assert.Equal(4, lines[0].GetProperty("bbox").GetArrayLength());
    }

    // --- M6: coarse properties for motor datasheets, JB covers and cylinder GA books ----------------------

    [Fact]
    public async Task M6_categories_are_listed_with_hydraulic_circuit_first_and_ga_drawings_not_filterable()
    {
        var keys = (await GetJson("/api/categories")).EnumerateArray().Select(c => c.GetProperty("key").GetString()).ToList();
        Assert.Equal("hyd_circuit", keys[0]);
        Assert.Contains("motor_datasheet", keys);
        Assert.Contains("jb_doc", keys);
        Assert.Contains("cylinder_ga_book", keys);
        Assert.DoesNotContain("ga_drawing", keys);        // link-only in the POC: no properties
        Assert.DoesNotContain("crs", keys);
    }

    [Fact]
    public async Task M6_motor_power_near_100_kw_returns_the_110_kw_motors_latest_revision_only()
    {
        var props = await GetJson("/api/categories/motor_datasheet/properties");
        Assert.Equal(7, props.GetArrayLength());
        var r = await Results("category=motor_datasheet&property=rated_output_kw&value=100");
        Assert.Equal("110 kW", r[0].GetProperty("matchedValue").GetString());
        Assert.Equal(10m, r[0].GetProperty("delta").GetDecimal());
        Assert.All(r, x => Assert.True(x.GetProperty("isLatest").GetBoolean()));
        Assert.Equal(5, r.Count);                          // 110 (PP60056), 18.5 (PP60056), 110 (PP60057), 11 + 160 (PP60058): one per family
    }

    [Fact]
    public async Task M6_jb_enclosure_depth_350_matches_only_the_latest_revisions_that_have_it()
    {
        var r = await Results("category=jb_doc&property=enclosure_size&value=350");
        Assert.NotEmpty(r);
        Assert.All(r, x => Assert.Equal(0m, x.GetProperty("delta").GetDecimal()));
        Assert.All(r, x => Assert.Equal("b", x.GetProperty("revision").GetString()));
    }

    [Fact]
    public async Task M6_cylinder_book_bore_80_returns_the_latest_books_and_exposes_the_index_rows()
    {
        var r = await Results("category=cylinder_ga_book&property=bore_mm&value=80");
        Assert.Equal(2, r.Count);
        var doc = await GetJson($"/api/documents/{r[0].GetProperty("documentId").GetInt64()}");
        Assert.Equal(10, doc.GetProperty("bomLines").GetArrayLength());
    }

    [Fact]
    public async Task AT5_include_old_shows_all_revisions_otherwise_only_latest()
    {
        var all = await Results($"{Dp}&value=250&includeOld=true&limit=100");
        Assert.Equal(new[] { "0", "a", "b", "c", "d", "e" },
            all.Where(x => x.GetProperty("projectCode").GetString() == "PP60056").Select(x => x.GetProperty("revision").GetString()).Order());

        var latest = await Results($"{Dp}&value=250&limit=100");
        Assert.Equal(new[] { "e" },
            latest.Where(x => x.GetProperty("projectCode").GetString() == "PP60056").Select(x => x.GetProperty("revision").GetString()));
    }

    [Fact]
    public async Task AT6_copy_file_never_appears()
    {
        var r = await Results($"{Dp}&value=300&includeOld=true&limit=200");
        Assert.DoesNotContain(r, x => x.GetProperty("fileName").GetString()!.Contains("Copy"));
    }

    [Fact]
    public async Task Result_carries_page_bbox_and_cad_siblings()
    {
        var r = (await Results($"{Dp}&value=250")).First(x => x.GetProperty("projectCode").GetString() == "PP60056");
        Assert.Equal(4, r.GetProperty("bbox").GetArrayLength());
        Assert.True(r.GetProperty("page").GetInt32() >= 1);
        Assert.Contains(r.GetProperty("siblings").EnumerateArray(), s => s.GetProperty("kind").GetString() == "dwg");
    }

    [Fact]
    public async Task Non_number_for_numeric_property_is_400() =>
        Assert.Equal(HttpStatusCode.BadRequest, (await _http.GetAsync($"/api/search?{Dp}&value=abc")).StatusCode);

    [Theory]
    [InlineData("/api/categories/nope/properties")]
    [InlineData("/api/categories/hyd_circuit/properties/nope/values")]
    [InlineData("/api/documents/999999999")]
    public async Task Unknown_things_are_404(string url) =>
        Assert.Equal(HttpStatusCode.NotFound, (await _http.GetAsync(url)).StatusCode);

    [Fact]
    public async Task Text_property_matches_despite_typo_in_the_query()
    {
        var r = await Results("category=hyd_circuit&property=working_fluid&value=Minerial%20ISO%20VG%2068");
        Assert.NotEmpty(r);
        Assert.All(r.Take(3), x => Assert.Equal(1.0, x.GetProperty("similarity").GetDouble()));
    }

    [Fact]
    public async Task File_endpoint_supports_range_requests_and_never_leaks_paths()
    {
        var hit = (await Results($"{Dp}&value=250"))[0];
        var id = hit.GetProperty("documentId").GetInt64();
        var req = new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{id}/file");
        req.Headers.Range = new(0, 99);
        var res = await _http.SendAsync(req);
        Assert.Equal(HttpStatusCode.PartialContent, res.StatusCode);
        Assert.Equal("application/pdf", res.Content.Headers.ContentType!.MediaType);
        Assert.Equal(100, (await res.Content.ReadAsByteArrayAsync()).Length);

        var detail = (await _http.GetStringAsync($"/api/documents/{id}"));
        Assert.DoesNotContain("D:/", detail);
    }

    [Fact]
    public async Task Categories_lists_only_latest_non_duplicate_documents()
    {
        var cats = await GetJson("/api/categories");
        var hyd = cats.EnumerateArray().Single(c => c.GetProperty("key").GetString() == "hyd_circuit");
        Assert.Equal(6, hyd.GetProperty("docCount").GetInt32());   // PP60056/57/58 e + the three SMS drawings
    }
}
