using System;
using Microsoft.Extensions.DependencyInjection;
using Spectre.Console.Cli;

namespace ConsoleApp.DependencyInjection;

public sealed class DependencyRegistrar(IServiceCollection services) : ITypeRegistrar
{
    private readonly IServiceCollection services = services;

    public ITypeResolver Build()
    {
        return new Resolver(services.BuildServiceProvider());
    }

    public void Register(Type service, Type implementation)
    {
        services.AddSingleton(service, implementation);
    }

    public void RegisterInstance(Type service, object implementation)
    {
        services.AddSingleton(service, implementation);
    }

    public void RegisterLazy(Type service, Func<object> factory)
    {
        services.AddSingleton(service, _ => factory());
    }

    private sealed class Resolver(IServiceProvider provider) : ITypeResolver
    {
        public object? Resolve(Type? type)
        {
            return type == null ? null : provider.GetService(type);
        }
    }
}
