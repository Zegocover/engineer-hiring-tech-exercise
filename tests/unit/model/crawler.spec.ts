import { test } from '@japa/runner'
import WebCrawler from '#models/crawler'
import MockAdapter from 'axios-mock-adapter'
import axios from 'axios'

const MOCK_BASE_URL = 'https://example.com'

const MOCK_HTML_CONTENT = `
  <html lang="en">
    <head><title>Test Page</title></head>
    <body>
      <a href="/about">About Us</a>
      <a href="https://example.com/contact">Contact Us</a>
      <a href="https://example.com/contact#form">Contact Form</a>
      <a href="https://external.com/other">External Link</a>
      <a href="mailto:test@example.com">Email Us</a>
      <a href="/about">Duplicate About</a>
      <a href="/valid-relative-url"></a>
    </body>
  </html>
`

test.group('WebCrawler Model', (group) => {
  let mock: MockAdapter
  group.each.setup(() => {
    mock = new MockAdapter(axios)
  })

  group.each.teardown(() => {
    mock.reset()
  })

  test('constructor initializes correctly', ({ assert }) => {
    const crawler = new WebCrawler(MOCK_BASE_URL, 10)

    assert.equal(crawler.baseUrl.href, `${MOCK_BASE_URL}/`)
    assert.equal(crawler.maxConcurrent, 10)
    assert.deepEqual(crawler.queue, [`${MOCK_BASE_URL}/`])
    assert.equal(crawler.queueHead, 0)
    assert.instanceOf(crawler.visitedLinks, Set)
    assert.isEmpty(crawler.visitedLinks)
  })

  test('loadUrl fetches HTML content', async ({ assert }) => {
    mock.onGet(MOCK_BASE_URL).reply(200, MOCK_HTML_CONTENT, { 'content-type': 'text/html' })

    const crawler = new WebCrawler(MOCK_BASE_URL)
    const content = await crawler.loadUrl(MOCK_BASE_URL)

    assert.equal(content, MOCK_HTML_CONTENT)
  })

  test('loadUrl handles non-HTML content', async ({ assert }) => {
    mock.onGet(MOCK_BASE_URL).reply(200, {}, { 'content-type': 'application/json' })

    const crawler = new WebCrawler(MOCK_BASE_URL)
    const content = await crawler.loadUrl(MOCK_BASE_URL)

    assert.equal(content, '')
  })

  test('loadUrl handles network error', async ({ assert }) => {
    mock.onGet(MOCK_BASE_URL).networkError()

    const crawler = new WebCrawler(MOCK_BASE_URL)
    const content = await crawler.loadUrl(MOCK_BASE_URL)

    assert.equal(content, '')
  })

  test('extractLinks extracts and normalizes URLs', ({ assert }) => {
    const crawler = new WebCrawler(MOCK_BASE_URL)
    const links = crawler.extractLinks(MOCK_HTML_CONTENT)

    assert.deepEqual(links, [
      'https://example.com/about',
      'https://example.com/contact',
      'https://example.com/valid-relative-url',
    ])
  })

  test('getAbsoluteUrl resolves relative and absolute URLs', ({ assert }) => {
    const crawler = new WebCrawler(MOCK_BASE_URL)

    assert.equal(crawler.getAbsoluteUrl('/about'), 'https://example.com/about')
    assert.equal(crawler.getAbsoluteUrl('contact'), 'https://example.com/contact')
    assert.equal(crawler.getAbsoluteUrl('https://example.com/jobs'), 'https://example.com/jobs')
  })

  test('getAbsoluteUrl returns null for external or invalid URLs', ({ assert }) => {
    const crawler = new WebCrawler(MOCK_BASE_URL)

    assert.isNull(crawler.getAbsoluteUrl('https://external.com'))
    assert.isNull(crawler.getAbsoluteUrl('mailto:test@example.com'))
    assert.isNull(crawler.getAbsoluteUrl('javascript:void(0)'))
  })

  test('crawlPage loads, extracts, and enqueues links', async ({ assert }) => {
    mock.onGet(`${MOCK_BASE_URL}/`).reply(200, MOCK_HTML_CONTENT)

    const crawler = new WebCrawler(MOCK_BASE_URL)
    await crawler.crawlPage(`${MOCK_BASE_URL}/`)

    assert.deepEqual(crawler.pageAndItsLinks[`${MOCK_BASE_URL}/`], [
      'https://example.com/about',
      'https://example.com/contact',
      'https://example.com/valid-relative-url',
    ])
    assert.deepEqual(crawler.queue, [
      `${MOCK_BASE_URL}/`,
      'https://example.com/about',
      'https://example.com/contact',
      'https://example.com/valid-relative-url',
    ])
  })
})
