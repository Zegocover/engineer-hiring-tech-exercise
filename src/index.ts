import { Crawler } from "./crawler"
import { AxiosHttpClient } from "./http-client"
import { CheerioLinkExtractor } from "./link-extractor"
import { ConsoleReporter, JsonReporter } from "./reporter"

interface CliOptions {
  url: string
  concurrency: number
  maxPages: number
  timeoutMs: number
  userAgent?: string
  json: boolean
}

const HELP_TEXT = `Usage: npm start -- <url> [options]
       npm run dev -- <url> [options]

Crawls every page reachable from <url> that stays on the same hostname,
printing each visited page and the links found on it.

Options:
  --concurrency <n>    Max concurrent in-flight requests (default: 5)
  --max-pages <n>      Stop after crawling this many pages (default: 10000)
  --timeout <ms>       Per-request HTTP timeout in milliseconds (default: 10000)
  --user-agent <str>   Custom User-Agent header to send with requests
  --json               Print machine-readable JSON instead of console log
  -h, --help           Show this help message

Example:
  npm run dev -- https://crawlme.zego.com/ --concurrency 10 --max-pages 50
`

const CAR_ART = `
              ______
             /|_||_'.__
            (   _    _ \\
            ='-(_)--(_)-'
`

function printBanner(): void {
  console.log(CAR_ART)
}

function printHelp(): void {
  console.log(HELP_TEXT)
}

function parsePositiveInt(name: string, value: string | undefined): number {
  const parsed = Number(value)
  if (value === undefined || !Number.isInteger(parsed) || parsed < 1) {
    throw new RangeError(`${name} must be a positive integer, got "${value}"`)
  }
  return parsed
}

/** Returns `null` when help was shown or no URL was given (caller should exit 0). */
function parseArgs(argv: string[]): CliOptions | null {
  let url: string | undefined
  let concurrency = 5
  let maxPages = 10_000
  let timeoutMs = 10_000
  let userAgent: string | undefined
  let json = false

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    switch (arg) {
      case "-h":
      case "--help":
        printHelp()
        return null
      case "--concurrency":
        concurrency = parsePositiveInt("--concurrency", argv[++i])
        break
      case "--max-pages":
        maxPages = parsePositiveInt("--max-pages", argv[++i])
        break
      case "--timeout":
        timeoutMs = parsePositiveInt("--timeout", argv[++i])
        break
      case "--user-agent":
        userAgent = argv[++i]
        if (!userAgent) throw new Error("--user-agent requires a value")
        break
      case "--json":
        json = true
        break
      default:
        if (arg.startsWith("--")) {
          throw new Error(`Unknown option: ${arg}`)
        }
        if (url) {
          throw new Error(`Unexpected argument: "${arg}"`)
        }
        url = arg
    }
  }

  if (!url) {
    printHelp()
    return null
  }

  return { url, concurrency, maxPages, timeoutMs, userAgent, json }
}

async function main(): Promise<void> {
  let options: CliOptions | null
  try {
    options = parseArgs(process.argv.slice(2))
  } catch (error) {
    console.error(error instanceof Error ? error.message : error)
    console.error("")
    printHelp()
    process.exit(1)
    return
  }

  if (!options) {
    return
  }

  try {
    new URL(options.url)
  } catch {
    console.error(`Invalid URL: "${options.url}"`)
    process.exit(1)
    return
  }

  const client = new AxiosHttpClient({
    timeoutMs: options.timeoutMs,
    ...(options.userAgent ? { userAgent: options.userAgent } : {}),
  })
  const extractor = new CheerioLinkExtractor()
  const reporter = options.json ? new JsonReporter() : new ConsoleReporter()
  const crawler = new Crawler(client, extractor, reporter, {
    concurrency: options.concurrency,
    maxPages: options.maxPages,
  })

  if (!options.json) {
    printBanner()
    console.log(`Starting crawl: ${options.url}`)
  }

  try {
    await crawler.crawl(options.url)
    reporter.summarise()
  } catch (error) {
    console.error(
      "Fatal error:",
      error instanceof Error ? error.message : error,
    )
    process.exit(1)
  }
}

main()
