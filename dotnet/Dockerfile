# syntax=docker/dockerfile:1

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY global.json Directory.Build.props ./
COPY src/ConsoleApp/ConsoleApp.csproj src/ConsoleApp/
COPY tests/ConsoleApp.Tests/ConsoleApp.Tests.csproj tests/ConsoleApp.Tests/
RUN dotnet restore src/ConsoleApp/ConsoleApp.csproj
RUN dotnet restore tests/ConsoleApp.Tests/ConsoleApp.Tests.csproj

COPY src/ src/
COPY tests/ tests/

FROM build AS test
ENTRYPOINT ["dotnet", "test", "tests/ConsoleApp.Tests/ConsoleApp.Tests.csproj"]

FROM build AS publish
RUN dotnet publish src/ConsoleApp/ConsoleApp.csproj -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/runtime:10.0 AS runtime
WORKDIR /app
COPY --from=publish /app .

ENTRYPOINT ["dotnet", "ConsoleApp.dll"]
