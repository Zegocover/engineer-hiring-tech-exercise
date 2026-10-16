package com.hamzaali.crawler.url;

import java.net.URI;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;

public final class RobotsTxtScope implements CrawlScope {

    private final List<String> disallowedPrefixes;

    public RobotsTxtScope(List<String> disallowedPrefixes) {
        this.disallowedPrefixes = List.copyOf(disallowedPrefixes);
    }

    public static RobotsTxtScope allowAll() {
        return new RobotsTxtScope(List.of());
    }

    public static RobotsTxtScope parse(String robotsTxt, String userAgent) {
        return new RobotsTxtScope(disallowsFor(robotsTxt, userAgent));
    }

    @Override
    public boolean allows(URI uri) {
        String path = Optional.ofNullable(uri.getRawPath())
                .filter(value -> !value.isEmpty())
                .orElse("/");
        return disallowedPrefixes.stream().noneMatch(path::startsWith);
    }

    private static List<String> disallowsFor(String robotsTxt, String userAgent) {
        String wanted = Optional.ofNullable(userAgent).orElse("*").strip().toLowerCase(Locale.ROOT);
        Optional<List<String>> starRules = Optional.empty();
        Optional<List<String>> exactRules = Optional.empty();
        Set<String> agents = Set.of();
        List<String> current = List.of();
        boolean collectingAgents = false;

        for (String raw : Optional.ofNullable(robotsTxt).orElse("").lines().toList()) {
            String line = stripComment(raw).strip();
            if (line.isEmpty()) {
                continue;
            }
            int colon = line.indexOf(':');
            if (colon < 0) {
                continue;
            }
            String field = line.substring(0, colon).strip().toLowerCase(Locale.ROOT);
            String value = line.substring(colon + 1).strip();
            if (field.equals("user-agent")) {
                if (!collectingAgents) {
                    starRules = mergeIfStar(starRules, agents, current);
                    exactRules = mergeIfExact(exactRules, agents, current, wanted);
                    agents = Set.of();
                    current = List.of();
                }
                collectingAgents = true;
                agents = union(agents, value.toLowerCase(Locale.ROOT));
            } else if (field.equals("disallow")) {
                collectingAgents = false;
                current = append(current, value);
            } else {
                collectingAgents = false;
            }
        }
        Optional<List<String>> resolvedStar = mergeIfStar(starRules, agents, current);
        Optional<List<String>> resolvedExact = mergeIfExact(exactRules, agents, current, wanted);
        return resolvedExact.orElseGet(() -> resolvedStar.orElseGet(List::of));
    }

    private static String stripComment(String line) {
        int comment = line.indexOf('#');
        return comment < 0 ? line : line.substring(0, comment);
    }

    private static Optional<List<String>> mergeIfStar(
            Optional<List<String>> existing, Set<String> agents, List<String> current) {
        return agents.contains("*") ? Optional.of(current) : existing;
    }

    private static Optional<List<String>> mergeIfExact(
            Optional<List<String>> existing, Set<String> agents, List<String> current, String wanted) {
        return matchesAgent(agents, wanted) ? Optional.of(current) : existing;
    }

    private static boolean matchesAgent(Set<String> agents, String wanted) {
        return agents.contains(wanted)
                || agents.stream().anyMatch(agent -> !agent.equals("*") && wanted.startsWith(agent + "/"));
    }

    private static Set<String> union(Set<String> agents, String agent) {
        HashSet<String> next = new HashSet<>(agents);
        next.add(agent);
        return Set.copyOf(next);
    }

    private static List<String> append(List<String> current, String disallow) {
        if (disallow.isEmpty()) {
            return current;
        }
        ArrayList<String> next = new ArrayList<>(current);
        next.add(disallow);
        return List.copyOf(next);
    }
}
