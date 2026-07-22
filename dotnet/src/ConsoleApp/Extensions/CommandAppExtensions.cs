using System;
using ConsoleApp.DependencyInjection;
using Microsoft.Extensions.DependencyInjection;
using Spectre.Console.Cli;

namespace ConsoleApp.Extensions;

public static class CommandAppExtensions
{
    extension(CommandApp)
    {
        public static CommandApp<TCommand> CreateWithServices<TCommand>(Action<IServiceCollection> configure) where TCommand : class, ICommand
        {
            var services = new ServiceCollection();

            configure.Invoke(services);

            return new CommandApp<TCommand>(new DependencyRegistrar(services));
        }
    }
}
