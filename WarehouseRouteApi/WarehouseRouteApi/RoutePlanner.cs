using Google.OrTools.ConstraintSolver;

public class RoutePlanner
{
    private readonly WarehouseGraph graph;

    public RoutePlanner(WarehouseGraph graph)
    {
        this.graph = graph;
    }

    public List<(string Location, int Distance)> FindOptimalRoute(IEnumerable<string> locations, string start)
    {
        var locs = new List<string> { start };
        foreach (var l in locations)
            if (!locs.Contains(l)) locs.Add(l);

        if (locs.Count <= 8)
            return FindOptimalRouteBruteForce(locs, start);

        return FindOptimalRouteORTools(locs);
    }

    private List<(string Location, int Distance)> FindOptimalRouteBruteForce(List<string> locs, string start)
    {
        var otherLocs = locs.Where(l => l != start).ToList();
        var bestRoute = new List<string>();
        var bestDistance = int.MaxValue;

        foreach (var perm in GetPermutations(otherLocs))
        {
            var route = new List<string> { start };
            route.AddRange(perm);
            var totalDistance = CalculateRouteDistance(route);
            if (totalDistance < bestDistance)
            {
                bestDistance = totalDistance;
                bestRoute = new List<string>(route);
            }
        }

        return ConvertRouteToResult(bestRoute);
    }

    // OR-Tools - explicit start and stop in RoutingIndexManager
    public List<(string Location, int Distance)> FindOptimalRouteORToolsWithEnd(
    List<string> all, string start, string stop, int searchMetaheuristic = 3)
    {
        int n = all.Count;
        int[,] distances = new int[n, n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                distances[i, j] = i == j ? 0 : graph.DistanceMatrix[all[i]].GetValueOrDefault(all[j], 9999);

        int startIdx = 0;
        int stopIdx = all.IndexOf(stop);

        if (startIdx == -1 || stopIdx == -1)
        {
            Console.WriteLine($"Error: start ({start}) or stop ({stop}) not found in the location list.");
            return new List<(string, int)>();
        }

        // var manager = new RoutingIndexManager(n, 1, startIdx, new[] { stopIdx }); // Start/stop
        RoutingIndexManager manager = null;
        try
        {
            manager = new RoutingIndexManager(n, 1, new[] { startIdx }, new[] { stopIdx });
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error while creating RoutingIndexManager: {ex.Message}");
            return new List<(string, int)>();
        }

        RoutingModel routing = new RoutingModel(manager);

        int transitCallbackIndex = routing.RegisterTransitCallback((long fromIdx, long toIdx) =>
        {
            int from = manager.IndexToNode(fromIdx);
            int to = manager.IndexToNode(toIdx);
            return distances[from, to];
        });

        routing.SetArcCostEvaluatorOfAllVehicles(transitCallbackIndex);
        routing.AddDimension(transitCallbackIndex, 0, 10000, true, "Distance");

        var searchParams = operations_research_constraint_solver.DefaultRoutingSearchParameters();
        searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.Savings;
        if (searchMetaheuristic < 0 || searchMetaheuristic > 17 || searchMetaheuristic == null)
        {
            searchMetaheuristic = 3; // Default: SimulatedAnnealing
        }

        switch (searchMetaheuristic)
        {
            case 0:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.Unset;
                break;
            case 1:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.GlobalCheapestArc;
                break;
            case 2:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.LocalCheapestArc;
                break;
            case 3:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.PathCheapestArc;
                break;
            case 4:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.PathMostConstrainedArc;
                break;
            case 5:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.EvaluatorStrategy;
                break;
            case 6:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.AllUnperformed;
                break;
            case 7:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.BestInsertion;
                break;
            case 8:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.ParallelCheapestInsertion;
                break;
            case 9:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.LocalCheapestInsertion;
                break;
            case 10:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.Savings;
                break;
            case 11:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.Sweep;
                break;
            case 12:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.FirstUnboundMinValue;
                break;
            case 13:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.Christofides;
                break;
            case 14:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.SequentialCheapestInsertion;
                break;
            case 15:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.Automatic;
                break;
            case 16:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.LocalCheapestCostInsertion;
                break;
            case 17:
                searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.ParallelSavings;
                break;
        }

        searchParams.TimeLimit = new Google.Protobuf.WellKnownTypes.Duration { Seconds = 30 };
        searchParams.LnsTimeLimit = new Google.Protobuf.WellKnownTypes.Duration { Seconds = 15 };

        var solution = routing.SolveWithParameters(searchParams);

        var result = new List<(string, int)>();
        if (solution != null)
        {
            long idx = routing.Start(0);
            while (!routing.IsEnd(idx))
            {
                int node = manager.IndexToNode(idx);
                int nextNode = manager.IndexToNode(solution.Value(routing.NextVar(idx)));
                result.Add((all[node], distances[node, nextNode]));
                idx = solution.Value(routing.NextVar(idx));
            }
            result.Add((all[stopIdx], 0));
        }
        return result;
    }



    private List<(string Location, int Distance)> FindOptimalRouteORTools(List<string> locs)
    {
        int n = locs.Count;
        int[,] distances = new int[n, n];

        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                distances[i, j] = i == j ? 0 : graph.DistanceMatrix[locs[i]].GetValueOrDefault(locs[j], 9999);

        var manager = new RoutingIndexManager(n, 1, 0);
        var routing = new RoutingModel(manager);

        int transitCallbackIndex = routing.RegisterTransitCallback((long fromIdx, long toIdx) =>
        {
            int from = manager.IndexToNode(fromIdx);
            int to = manager.IndexToNode(toIdx);
            return distances[from, to];
        });

        routing.SetArcCostEvaluatorOfAllVehicles(transitCallbackIndex);
        routing.AddDimension(transitCallbackIndex, 0, 10000, true, "Distance");

        var searchParams = operations_research_constraint_solver.DefaultRoutingSearchParameters();

        searchParams.FirstSolutionStrategy = FirstSolutionStrategy.Types.Value.Savings;
        searchParams.LocalSearchMetaheuristic = LocalSearchMetaheuristic.Types.Value.SimulatedAnnealing;
        searchParams.TimeLimit = new Google.Protobuf.WellKnownTypes.Duration { Seconds = 30 };
        searchParams.LnsTimeLimit = new Google.Protobuf.WellKnownTypes.Duration { Seconds = 15 };

        var solution = routing.SolveWithParameters(searchParams);

        var result = new List<(string, int)>();
        if (solution != null)
        {
            long idx = routing.Start(0);
            while (!routing.IsEnd(idx))
            {
                int node = manager.IndexToNode(idx);
                int nextNode = manager.IndexToNode(solution.Value(routing.NextVar(idx)));
                result.Add((locs[node], distances[node, nextNode]));
                idx = solution.Value(routing.NextVar(idx));
            }
        }
        return result;
    }

    private int CalculateRouteDistance(List<string> route)
    {
        int totalDistance = 0;
        for (int i = 0; i < route.Count - 1; i++)
        {
            var from = route[i];
            var to = route[i + 1];
            totalDistance += graph.DistanceMatrix[from].GetValueOrDefault(to, 9999);
        }
        return totalDistance;
    }

    private List<(string Location, int Distance)> ConvertRouteToResult(List<string> route)
    {
        var result = new List<(string, int)>();
        for (int i = 0; i < route.Count - 1; i++)
        {
            var from = route[i];
            var to = route[i + 1];
            var distance = graph.DistanceMatrix[from].GetValueOrDefault(to, 9999);
            result.Add((from, distance));
        }
        if (route.Count > 0)
            result.Add((route.Last(), 0));
        return result;
    }


    private static IEnumerable<IEnumerable<T>> GetPermutations<T>(IEnumerable<T> enumerable)
    {
        var array = enumerable as T[] ?? enumerable.ToArray();

        var factorial = (int)(FactorialHelper(array.Length));
        for (var i = 0; i < factorial; i++)
        {
            var sequence = GeneratePermutation(array, i);
            yield return sequence;
        }
    }

    private static IEnumerable<T> GeneratePermutation<T>(T[] array, int index)
    {
        var result = new T[array.Length];
        var list = new List<T>(array);
        for (int i = 0; i < array.Length; i++)
        {
            var factorial = (int)FactorialHelper(array.Length - 1 - i);
            var selectedIndex = index / factorial;
            result[i] = list[selectedIndex];
            list.RemoveAt(selectedIndex);
            index %= factorial;
        }
        return result;
    }

    private static long FactorialHelper(int n)
    {
        if (n <= 1) return 1;
        return n * FactorialHelper(n - 1);
    }
}
