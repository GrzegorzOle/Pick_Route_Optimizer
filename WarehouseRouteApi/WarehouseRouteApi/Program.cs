using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
// Resolve the map next to the executable, not the working directory, so a packaged server
// works no matter where it is launched from (double-clicked, run from another folder, …).
var mapPath = Path.Combine(AppContext.BaseDirectory, "mapa_odleglosci.json");
builder.Services.AddSingleton<WarehouseGraph>(sp => new WarehouseGraph(mapPath));
builder.Services.AddSingleton<RoutePlanner>();
var app = builder.Build();

// if (app.Environment.IsDevelopment())
// {
    app.UseSwagger(); app.UseSwaggerUI();
// }

app.UseRouting();
app.MapControllers();

app.Run();