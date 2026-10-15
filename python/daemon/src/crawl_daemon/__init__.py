"""Background daemon that runs site crawls submitted with the ``crawld`` command.

Modules, each importing only the ones listed before it:

- ``settings``    service-wide settings from ``CRAWLD_*`` variables
- ``models``      jobs, their limits and statistics, and the daemon's errors
- ``storage``     where jobs, results and the parse cache live (SQLite or PostgreSQL)
- ``components``  the daemon's Fetcher, Parser and Writer for the crawler
- ``scheduler``   the job queue and the workers that run crawls
- ``protocol``    the JSON-lines wire format
- ``state``       the state file clients use to find the daemon
- ``server``      the loopback TCP server and the daemon's lifecycle
- ``client``      the blocking client the CLI uses
- ``cli``         the ``crawld`` command
"""

__version__ = "0.1.0"
