import { test } from '@japa/runner'
import Webpage from '#models/webpage'

const MOCK_BASE_URL = 'https://example.com'

const MOCK_HTML_CONTENT = `
  <html lang="en">
    <head><title>Test Page</title></head>
    <body>
      <a href="/about">About Us</a>
      <a href="https://example.com/contact">Contact</a>
      <a href="https://example.com/contact#form">Contact Form</a>
      <a href="https://external.com/other">External Link</a>
      <a href="mailto:test@example.com">Email Us</a>
      <a href="/about">Duplicate About</a>
      <a href="/invalid-relative-url"></a>
    </body>
  </html>
`

test.group('Webpage Model', () => {
  test('constructor should correctly initialize with a valid URL', ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)

    assert.instanceOf(page.url, URL)
    assert.equal(page.url.href, `${MOCK_BASE_URL}/`)
  })

  test('constructor should throw for an invalid URL', ({ assert }) => {
    assert.throws(() => new Webpage('not-a-valid-url'), 'Invalid URL')
  })

  test('load() should fetch and store HTML content', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)

    await page.load()

    assert.equal(page.htmlContent, MOCK_HTML_CONTENT)
  })

  test('load() should not store content for non-HTML responses', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)

    await page.load()

    assert.isEmpty(page.htmlContent)
  })

  test('getLinks() should return an empty array if HTML is not loaded', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)
    const links = await page.getLinks()

    assert.deepEqual(links, [])
  })

  test('getLinks() should extract, normalize, and filter links correctly', async ({ assert }) => {
    const page = new Webpage(MOCK_BASE_URL)
    page.htmlContent = MOCK_HTML_CONTENT

    const links = await page.getLinks()

    assert.deepEqual(links, ['https://example.com/about', 'https://example.com/contact'])
  })
})
