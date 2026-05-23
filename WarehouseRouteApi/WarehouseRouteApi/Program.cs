using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddSingleton<WarehouseGraph>(sp => new WarehouseGraph("mapa_odleglosci.json"));
builder.Services.AddSingleton<RoutePlanner>();
var app = builder.Build();

// if (app.Environment.IsDevelopment())
// {
    app.UseSwagger(); app.UseSwaggerUI();
// }

app.UseRouting();
app.MapControllers();

app.Run();