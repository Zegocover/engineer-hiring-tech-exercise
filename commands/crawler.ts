import { BaseCommand, args, flags } from '@adonisjs/core/ace'
import type { CommandOptions } from '@adonisjs/core/types/ace'

import WebCrawler from '#models/crawler'

export default class Crawler extends BaseCommand {
  static readonly commandName = 'crawler'
  static readonly description = 'Crawls a website from a base URL, staying on the same domain'

  static readonly help = [
    'Usage: node ace crawler <baseURL>',
    'Example: node ace crawler https://www.zego.com',
  ]

  static readonly options: CommandOptions = {}

  @args.string({ description: 'Base URL to crawl', required: false })
  declare baseURL: string

  @flags.boolean({ default: true, description: 'Enable verbose mode' })
  declare verbose: boolean

  @flags.number({ default: 5, description: 'how many pages to crawl at a time' })
  declare concurrency: number

  @flags.number({ default: 200, description: 'maximum number of pages to crawl' })
  declare maxPages: number

  crawler: Crawler | undefined

  async run() {
    await this.validate()

    const tasks = this.ui.tasks({ verbose: this.verbose })

    await tasks
      .add('validating base URL', async () => await this.validate())
      .add('crawling links', async () => await this.crawlAllLinks())
      .run()
  }

  private async validate(): Promise<string> {
    if (!this.baseURL) {
      this.baseURL = await this.prompt.ask('Enter the Base URL:', {
        validate: (value) => {
          if (!value) {
            return 'Base URL is required'
          }
          return true
        },
      })
    }

    return 'valid input ✅ '
  }

  private async crawlAllLinks(): Promise<string> {
    const webCrawler = new WebCrawler(this.baseURL, this.concurrency)

    await webCrawler.start()

    return 'crawling completed ✅ '
  }
}
