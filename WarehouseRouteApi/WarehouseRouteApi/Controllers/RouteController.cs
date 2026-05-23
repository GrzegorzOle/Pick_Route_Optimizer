using Microsoft.AspNetCore.Mvc;
using WarehouseRouteApi.Models;

[Route("api/route")]
[ApiController]
public class RouteController : ControllerBase
{
    private readonly WarehouseGraph _graph;
    private readonly RoutePlanner _planner;

    public RouteController(WarehouseGraph graph, RoutePlanner planner)
    {
        _graph = graph;
        _planner = planner;
    }

    [HttpPost("optimal")]
    public ActionResult<RouteResponse> OptimizeRoute([FromBody] RouteRequest request)
    {
        var start = (string.IsNullOrWhiteSpace(request.StartLocation) ? "A05" : request.StartLocation).ToUpper();
        var stop = (string.IsNullOrWhiteSpace(request.StopLocation) ? "M05" : request.StopLocation).ToUpper();
        var metaheuristic = request.SearchMetaheuristic ?? 3;

        if (request.Locations == null)
            return BadRequest("Provide at least one intermediate location.");

        // Location validation
        if (!_graph.DistanceMatrix.ContainsKey(start) ||
            !_graph.DistanceMatrix.ContainsKey(stop) ||
            request.Locations.Any(l => !_graph.DistanceMatrix.ContainsKey(l)))
            return BadRequest("Locations outside the warehouse.");

        // Build "all" list = intermediate points + start + stop (if missing)
        var all = request.Locations.Distinct().ToList();

        if (!all.Contains(start, StringComparer.OrdinalIgnoreCase))
            all.Insert(0, start);

        if (!all.Contains(stop, StringComparer.OrdinalIgnoreCase))
            all.Add(stop);

        // Compute route
        var result = _planner.FindOptimalRouteORToolsWithEnd(all, start, stop, metaheuristic);

        // Filter out start and stop from final result (if you don't want them in response)
        var filtered = result.Where(r =>
            !string.Equals(r.Location, start, StringComparison.OrdinalIgnoreCase) &&
            !string.Equals(r.Location, stop, StringComparison.OrdinalIgnoreCase)).ToList();

        return Ok(new RouteResponse
                      {
                          StartLocation = start,
                          Route = filtered.Select(r => new RouteItem
                                                           {
                                                               Location = r.Location,
                                                               Distance = r.Distance
                                                           }).ToList()
                      });
    }





    [HttpGet("locations")]
    public ActionResult<List<string>> GetLocations()
        => Ok(_graph.DistanceMatrix.Keys.OrderBy(k => k).ToList());

    [HttpGet("distance/{from}/{to}")]
    public ActionResult<int> GetDistance(string from, string to)
    {
        if (!_graph.DistanceMatrix.ContainsKey(from) || !_graph.DistanceMatrix[from].ContainsKey(to))
            return NotFound(9999);

        return Ok(_graph.DistanceMatrix[from][to]);
    }

}
