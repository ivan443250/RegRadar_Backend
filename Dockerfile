# --- build stage ---
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# сначала только то, что нужно для restore (кэш слоёв)
COPY Directory.Build.props Directory.Packages.props ./
COPY src/ src/

RUN dotnet restore src/RegRadar.Api/RegRadar.Api.csproj
RUN dotnet publish src/RegRadar.Api/RegRadar.Api.csproj -c Release -o /app/publish --no-restore

# --- runtime stage ---
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .
EXPOSE 8080
ENTRYPOINT ["dotnet", "RegRadar.Api.dll"]