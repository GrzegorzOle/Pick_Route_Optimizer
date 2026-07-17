using System.Collections.Generic;
using System.IO;
using System.Text.Json;

public class WarehouseGraph
{
    public Dictionary<string, Dictionary<string, int>> DistanceMatrix { get; }

    public WarehouseGraph(string jsonPath)
    {
        // Resolved against the working directory, so a launch from elsewhere must fail loudly here.
        if (!File.Exists(jsonPath))
            throw new FileNotFoundException(
                $"Distance matrix '{jsonPath}' not found. Run the API from the project directory, or regenerate it with MAP_Generator/export.py.",
                jsonPath);

        var json = File.ReadAllText(jsonPath);
        DistanceMatrix = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, int>>>(json)
                         ?? throw new InvalidDataException($"Distance matrix '{jsonPath}' is empty or malformed.");
    }
}