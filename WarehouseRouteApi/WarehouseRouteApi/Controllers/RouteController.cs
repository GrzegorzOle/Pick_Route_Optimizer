using Microsoft.AspNetCore.Mvc;
using WarehouseRouteApi.Models;

[Route("api/route")]
[ApiController]
public class RouteController : ControllerBase
{
    private const string DefaultStart = "A05";
    private const string DefaultStop = "M05";

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
        var start = (string.IsNullOrWhiteSpace(request.StartLocation) ? DefaultStart : request.StartLocation).ToUpper();
        var stop = (string.IsNullOrWhiteSpace(request.StopLocation) ? DefaultStop : request.StopLocation).ToUpper();
        var metaheuristic = request.SearchMetaheuristic ?? 3;

        if (request.Locations == null || request.Locations.Count == 0)
            return BadRequest("Provide at least one intermediate location.");

        var intermediates = request.Locations
            .Where(l => !string.IsNullOrWhiteSpace(l))
            .Select(l => l.ToUpper())
            .Distinct()
            .ToList();

        // Location validation
        if (!_graph.DistanceMatrix.ContainsKey(start) ||
            !_graph.DistanceMatrix.ContainsKey(stop) ||
            intermediates.Any(l => !_graph.DistanceMatrix.ContainsKey(l)))
            return BadRequest("Locations outside the warehouse.");

        // Start and stop are fixed endpoints, so they must not also be routed as stops.
        intermediates.RemoveAll(l => l == start || l == stop);

        // The solver needs start first and stop last; anything else silently reroutes the endpoints.
        var all = new List<string> { start };
        all.AddRange(intermediates);
        if (stop != start)
            all.Add(stop);

        var order = _planner.FindOptimalRouteORToolsWithEnd(all, start, stop, metaheuristic);
        if (order.Count == 0)
            return StatusCode(StatusCodes.Status500InternalServerError, "No route found.");

        // Each item carries the leg walked to reach it, so the legs sum to the true route length.
        var route = new List<RouteItem>();
        var totalDistance = 0;
        for (int i = 1; i < order.Count; i++)
        {
            var leg = _graph.DistanceMatrix[order[i - 1]].GetValueOrDefault(order[i], RoutePlanner.MissingEdgeCost);
            totalDistance += leg;

            if (!string.Equals(order[i], stop, StringComparison.OrdinalIgnoreCase))
                route.Add(new RouteItem { Location = order[i], Distance = leg });
        }

        return Ok(new RouteResponse
                      {
                          StartLocation = start,
                          StopLocation = stop,
                          Route = route,
                          TotalDistance = totalDistance
                      });
    }





    [HttpGet("locations")]
    public ActionResult<List<string>> GetLocations()
        => Ok(_graph.DistanceMatrix.Keys.OrderBy(k => k).ToList());

    [HttpGet("distance/{from}/{to}")]
    public ActionResult<int> GetDistance(string from, string to)
    {
        from = from.ToUpper();
        to = to.ToUpper();

        if (!_graph.DistanceMatrix.TryGetValue(from, out var neighbours) || !neighbours.TryGetValue(to, out var distance))
            return NotFound(RoutePlanner.MissingEdgeCost);

        return Ok(distance);
    }

}
