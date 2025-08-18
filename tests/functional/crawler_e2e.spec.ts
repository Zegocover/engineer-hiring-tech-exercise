import { test } from '@japa/runner'
import MockAdapter from 'axios-mock-adapter'
import axios from 'axios'
import WebCrawler from '#models/crawler'

const MOCK_BASE_URL = 'https://example.com'

const MOCK_HTML_HOME = `
  <html>
    <head><title>Home Page</title></head>
    <body>
      <a href="/about">About Us</a>
      <a href="/contact">Contact</a>
      <a href="/products">Products</a>
    </body>
  </html>
`

const MOCK_HTML_ABOUT = `
  <html>
    <head><title>About Page</title></head>
    <body>
      <a href="/">Home</a>
      <a href="/team">Team</a>
      <a href="/history">History</a>
    </body>
  </html>
`

const MOCK_HTML_CONTACT = `
  <html>
    <head><title>Contact Page</title></head>
    <body>
      <a href="/">Home</a>
      <a href="/about">About</a>
      <form action="/submit" method="post">
        <input type="email" name="email">
      </form>
    </body>
  </html>
`

test.group('Functional | Crawler E2E Tests', (group) => {
  let mock: MockAdapter

  group.each.setup(() => {
    mock = new MockAdapter(axios)
  })

  group.each.teardown(() => {
    mock.reset()
  })

  test('should successfully crawl a complete website with multiple pages', async ({ assert }) => {
    // Setup mock responses for a complete website structure
    mock.onGet(`${MOCK_BASE_URL}/`).reply(200, MOCK_HTML_HOME, { 'content-type': 'text/html' })
    mock
      .onGet(`${MOCK_BASE_URL}/about`)
      .reply(200, MOCK_HTML_ABOUT, { 'content-type': 'text/html' })
    mock
      .onGet(`${MOCK_BASE_URL}/contact`)
      .reply(200, MOCK_HTML_CONTACT, { 'content-type': 'text/html' })
    mock
      .onGet(`${MOCK_BASE_URL}/products`)
      .reply(200, '<html><body><h1>Products</h1><a href="/about">About</a></body></html>', {
        'content-type': 'text/html',
      })
    mock
      .onGet(`${MOCK_BASE_URL}/team`)
      .reply(200, '<html><body><h1>Team</h1><a href="/">Home</a></body></html>', {
        'content-type': 'text/html',
      })
    mock
      .onGet(`${MOCK_BASE_URL}/history`)
      .reply(200, '<html><body><h1>History</h1><a href="/about">About</a></body></html>', {
        'content-type': 'text/html',
      })

    const crawler = new WebCrawler(MOCK_BASE_URL, 2)
    await crawler.start()

    // Verify that pages were crawled and links were discovered
    const crawledPages = Object.keys(crawler.pageAndItsLinks)
    assert.isTrue(crawledPages.length >= 3, 'Should crawl multiple pages')
    assert.isTrue(crawledPages.includes(`${MOCK_BASE_URL}/`), 'Should crawl home page')
    assert.isTrue(crawler.visitedLinks.size >= 3, 'Should visit multiple unique links')

    // Verify specific page links were extracted correctly
    const homeLinks = crawler.pageAndItsLinks[`${MOCK_BASE_URL}/`]
    assert.isArray(homeLinks, 'Home page should have extracted links')
    assert.isTrue(homeLinks.includes('https://example.com/about'), 'Should extract about link')
    assert.isTrue(homeLinks.includes('https://example.com/contact'), 'Should extract contact link')
  }).timeout(15000)

  test('should crawl within the same domain only', async ({ assert }) => {
    const htmlWithExternalLinks = `
      <html>
        <body>
          <a href="/internal">Internal Link</a>
          <a href="https://example.com/same-domain">Same Domain</a>
          <a href="https://external.com/other">External Link</a>
          <a href="https://subdomain.example.com/sub">Subdomain</a>
          <a href="mailto:test@example.com">Email Link</a>
        </body>
      </html>
    `

    mock
      .onGet(`${MOCK_BASE_URL}/`)
      .reply(200, htmlWithExternalLinks, { 'content-type': 'text/html' })
    mock
      .onGet(`${MOCK_BASE_URL}/internal`)
      .reply(200, '<html><body>Internal Page</body></html>', { 'content-type': 'text/html' })
    mock
      .onGet(`${MOCK_BASE_URL}/same-domain`)
      .reply(200, '<html><body>Same Domain Page</body></html>', { 'content-type': 'text/html' })

    const crawler = new WebCrawler(MOCK_BASE_URL, 2)
    await crawler.start()

    const allLinks = crawler.pageAndItsLinks[`${MOCK_BASE_URL}/`]
    assert.isArray(allLinks, 'Should extract links')

    // Should only include same-domain links
    for (const link of allLinks) {
      assert.isTrue(link.startsWith('https://example.com'), `Link ${link} should be same domain`)
    }

    // Should not include external domains, emails, etc.
    assert.isFalse(
      allLinks.some((link) => link.includes('external.com')),
      'Should not include external domains'
    )
    assert.isFalse(
      allLinks.some((link) => link.includes('subdomain.example.com')),
      'Should not include subdomains'
    )
    assert.isFalse(
      allLinks.some((link) => link.includes('mailto:')),
      'Should not include email links'
    )
  }).timeout(15000)

  test('should handle maximum pages limit', async ({ assert }) => {
    // Create a large site structure
    const manyLinksHtml = Array.from(
      { length: 20 },
      (_, i) => `<a href="/page${i}">Page ${i}</a>`
    ).join('\n')
    const homeHtml = `<html><body>${manyLinksHtml}</body></html>`

    mock.onGet(`${MOCK_BASE_URL}/`).reply(200, homeHtml, { 'content-type': 'text/html' })

    // Mock all the individual pages
    for (let i = 0; i < 20; i++) {
      mock
        .onGet(`${MOCK_BASE_URL}/page${i}`)
        .reply(200, `<html><body>Page ${i}</body></html>`, { 'content-type': 'text/html' })
    }

    const crawler = new WebCrawler(MOCK_BASE_URL, 3, 5) // Set maxPagesToCrawl to 5
    await crawler.start()

    // Should respect the page limit
    assert.isTrue(
      crawler.visitedLinks.size <= 5,
      `Should not exceed max pages limit, visited: ${crawler.visitedLinks.size}`
    )
    assert.isTrue(crawler.visitedLinks.size >= 1, 'Should crawl at least the base URL')
  }).timeout(15000)
})
