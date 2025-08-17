import { WebpageInterface } from '../interfaces/webpage_interface.js'

export default class Webpage implements WebpageInterface {
  url: URL

  links: string[] = []

  htmlContent: string = ''

  constructor(baseURL: string) {
    this.url = new URL(baseURL)
  }
}
