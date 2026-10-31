using Npgsql;

namespace Docsearch.Api.Infrastructure;

public static class ConnectionStrings
{
    /// <summary>Accepts the scope's postgresql://user:pw@host:port/db form as well as a normal Npgsql string.</summary>
    public static string ToNpgsql(string db)
    {
        if (!db.StartsWith("postgres://") && !db.StartsWith("postgresql://")) return db;
        var u = new Uri(db);
        var user = u.UserInfo.Split(':', 2);
        return new NpgsqlConnectionStringBuilder
        {
            Host = u.Host,
            Port = u.Port > 0 ? u.Port : 5432,
            Database = u.AbsolutePath.TrimStart('/'),
            Username = Uri.UnescapeDataString(user[0]),
            Password = user.Length > 1 ? Uri.UnescapeDataString(user[1]) : null,
        }.ConnectionString;
    }
}
