import axios, { isAxiosError, type AxiosInstance } from "axios"
import type { HttpClient, HttpResponse } from "./types"

interface AxiosHttpClientConfig {
  timeoutMs?: number
  userAgent?: string
}

export class AxiosHttpClient implements HttpClient {
  private readonly client: AxiosInstance

  constructor({
    timeoutMs = 10_000,
    userAgent = "web-crawler/1.0",
  }: AxiosHttpClientConfig = {}) {
    this.client = axios.create({
      timeout: timeoutMs,
      headers: { "User-Agent": userAgent },
    })
  }

  async get(url: string): Promise<HttpResponse | null> {
    try {
      const response = await this.client.get<string>(url, {
        responseType: "text",
      })

      const contentType =
        (response.headers["content-type"] as string | undefined) ?? ""
      if (!contentType.includes("text/html")) {
        return null
      }

      // After redirects, the final URL is the correct base for resolving relative links.
      const finalUrl: string =
        (response.request as { res?: { responseUrl?: string } })?.res
          ?.responseUrl ?? url

      return { html: response.data, finalUrl }
    } catch (error) {
      if (isAxiosError(error) && error.response != null) {
        // HTTP error
        return null
      }
      // Network failure, DNS error, timeout
      throw error
    }
  }
}
