using System;
using System.IO;
using System.Threading.Tasks;
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;

namespace ConsoleApp.Tests;

public sealed class StubSiteFixture : IAsyncLifetime
{
    private IContainer? _container;

    public string BaseUrl { get; private set; } = string.Empty;

    public async ValueTask InitializeAsync()
    {
        _container = new ContainerBuilder("nginx:alpine")
            .WithResourceMapping(Path.Combine(AppContext.BaseDirectory, "Stubs"), "/usr/share/nginx/html")
            .WithPortBinding(80, true)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilHttpRequestIsSucceeded(r => r.ForPath("/index.html")))
            .Build();

        await _container.StartAsync();

        BaseUrl = $"http://{_container.Hostname}:{_container.GetMappedPublicPort(80)}/";
    }

    public async ValueTask DisposeAsync()
    {
        if (_container is not null)
            await _container.DisposeAsync();
    }
}

[CollectionDefinition("Stub site")]
public sealed class StubSiteCollection : ICollectionFixture<StubSiteFixture>;
