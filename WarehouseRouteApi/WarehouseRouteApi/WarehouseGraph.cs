using System.Collections.Generic;
using System.IO;
using System.Text.Json;

public class WarehouseGraph
{
    public Dictionary<string, Dictionary<string, int>> DistanceMatrix { get; }

    public WarehouseGraph(string jsonPath)
    {
        var json = File.ReadAllText(jsonPath);
        DistanceMatrix = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, int>>>(json);
    }
}