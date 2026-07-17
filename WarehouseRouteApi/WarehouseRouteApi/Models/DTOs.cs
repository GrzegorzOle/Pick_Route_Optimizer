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
        public string Location { get; set; } = string.Empty;

        /// <summary>Distance walked from the previous location to reach this one.</summary>
        public int Distance { get; set; }
    }

    public class RouteResponse
    {
        public string StartLocation { get; set; } = string.Empty;

        public string StopLocation { get; set; } = string.Empty;

        /// <summary>Intermediate stops in visit order; start and stop are omitted.</summary>
        public List<RouteItem> Route { get; set; } = new();

        /// <summary>Full length of the walk, including the legs to the start and stop that Route omits.</summary>
        public int TotalDistance { get; set; }
    }
}