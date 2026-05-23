namespace WarehouseRouteApi.Models
{

    public class RouteRequest
    {
        public string? StartLocation { get; set; }
        public string? StopLocation { get; set; }
        public List<string>? Locations { get; set; }
        public int? SearchMetaheuristic { get; set; } // 0..6 (optional)
    }

    public class RouteItem
    {
        public string Location { get; set; }

        public int Distance { get; set; }
    }

    public class RouteResponse
    {
        public string StartLocation { get; set; }

        public List<RouteItem> Route { get; set; }

        public int TotalDistance => Route != null ? Route.Sum(x => x.Distance) : 0;
    }
}