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

    // --- M7: fuzzy free-text search ---------------------------------------------------------------------

    private async Task<List<JsonElement>> Text(string query) =>
        (await GetJson($"/api/text-search?{query}")).GetProperty("results").EnumerateArray().ToList();

    private static string Kind(JsonElement r) => r.GetProperty("matchKind").GetString()!;

    [Fact]
    public async Task M7_typod_query_finds_the_right_bom_rows()
    {
        var exact = await Text("q=pressure%20relief%20valve");
        var typo = await Text("q=presure%20relef%20valve");
        Assert.NotEmpty(typo);
        Assert.All(typo.Take(5), r => Assert.Equal("BomLine", Kind(r)));
        Assert.All(typo.Take(5), r => Assert.Contains("Pressure Relief Valve", r.GetProperty("matchedText").GetString()));
        // the same documents come back as for the correctly spelled query
        Assert.Equal(exact.Select(r => r.GetProperty("documentId").GetInt64()).Order(),
                     typo.Select(r => r.GetProperty("documentId").GetInt64()).Order().Take(exact.Count));
        Assert.True(typo[0].GetProperty("score").GetDouble() < exact[0].GetProperty("score").GetDouble());
    }

    [Fact]
    public async Task M7_part_number_with_o_for_zero_still_finds_the_part()
    {
        var r = await Text("q=TPN0O041");                       // letter O typed for the digit 0
        Assert.Equal("PartNo", Kind(r[0]));
        Assert.Equal("TPN00041", r[0].GetProperty("matchedText").GetString());
        Assert.Equal(1.0, r[0].GetProperty("score").GetDouble());
        Assert.Contains("PP60056", r[0].GetProperty("fileName").GetString());
        // near-miss part numbers (different parts) rank strictly below
        Assert.All(r.Skip(1).Where(x => x.GetProperty("matchedText").GetString() != "TPN00041"),
                   x => Assert.True(x.GetProperty("score").GetDouble() < 1.0));
    }

    [Fact]
    public async Task M7_cad_parts_are_found_by_file_name_exact_matches_first_then_near_misses()
    {
        var r = await Text("q=4we6&category=cad");
        Assert.All(r, x => Assert.Equal("FileName", Kind(x)));
        Assert.All(r, x => Assert.EndsWith(".SLDPRT", x.GetProperty("fileName").GetString()));
        Assert.All(r, x => Assert.Equal("PP60058", x.GetProperty("projectCode").GetString()));
        var exact = r.TakeWhile(x => x.GetProperty("score").GetDouble() == 1.0).Select(x => x.GetProperty("fileName").GetString()).Order();
        Assert.Equal(new[] { "4WE6-D-ASM.SLDPRT", "4WE6-E-H-G-J.SLDPRT" }, exact);
        // "4WE 10 D" is the same valve family at another size: a fair near-match, but it must rank below the exact parts
        Assert.All(r.Skip(2), x => Assert.True(x.GetProperty("score").GetDouble() < 1.0));
    }

    [Fact]
    public async Task M7_spec_value_typo_matches_the_canonical_value_and_points_at_the_cell()
    {
        var r = await Text("q=minerial%20iso%20vg%2068&category=hyd_circuit");
        var top = r.First();
        Assert.Equal("Spec", Kind(top));
        Assert.Equal("working_fluid", top.GetProperty("matchedKey").GetString());
        Assert.Equal(4, top.GetProperty("bbox").GetArrayLength());
        Assert.Contains("VG68", top.GetProperty("matchedText").GetString());           // VG68 outranks VG46
        Assert.Equal(1.0, top.GetProperty("score").GetDouble());
    }

    [Fact]
    public async Task M7_notes_are_searchable_despite_a_typo()
    {
        var r = await Text("q=metal%20condiut&category=hyd_circuit");          // "metal conduit"
        Assert.Equal(new[] { "01-HV11452-c", "01-HV11495-d", "01-PP02123-d" },
                     r.Select(x => x.GetProperty("fileName").GetString()![..12]).Order());
        Assert.All(r, x => Assert.Equal("Note", Kind(x)));
        Assert.All(r, x => Assert.True(x.GetProperty("isLatest").GetBoolean()));
    }

    [Fact]
    public async Task M7_old_revisions_only_on_request_and_never_the_copy()
    {
        // the SMPS note exists only on the rev-0 drawing of PP60056
        Assert.Empty(await Text("q=smps&category=hyd_circuit"));
        var all = await Text("q=smps&category=hyd_circuit&includeOld=true");
        Assert.Single(all);
        Assert.False(all[0].GetProperty("isLatest").GetBoolean());
        Assert.Contains("PP60056-0", all[0].GetProperty("fileName").GetString());
        var many = await Text("q=hyd.ckt&includeOld=true&limit=100");
        Assert.DoesNotContain(many, x => x.GetProperty("fileName").GetString()!.Contains("Copy"));
    }

    [Fact]
    public async Task M7_matched_bom_line_carries_its_page_and_bbox_and_a_match_count()
    {
        var r = await Text("q=hot%20oil%20shuttle&category=bom_system");
        Assert.NotEmpty(r);
        Assert.All(r, x => Assert.Equal("BomLine", Kind(x)));
        Assert.All(r, x => Assert.Equal(4, x.GetProperty("bbox").GetArrayLength()));
        Assert.All(r, x => Assert.True(x.GetProperty("matchCount").GetInt32() >= 1));
    }

    [Fact]
    public async Task M7_too_short_a_query_is_a_readable_400() =>
        Assert.Equal(HttpStatusCode.BadRequest, (await _http.GetAsync("/api/text-search?q=ab")).StatusCode);

    [Fact]
    public async Task M7_nonsense_returns_nothing_rather_than_junk()
    {
        Assert.Empty(await Text("q=zzqxjkw"));
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
