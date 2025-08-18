import { test } from '@japa/runner'
import { getAbsoluteUrl } from '#helpers/utils'

const baseUrl = 'https://example.com'

test.group('getAbsoluteUrl', () => {
  test('should return null for an empty URL', ({ assert }) => {
    assert.isNull(getAbsoluteUrl('', baseUrl))
  })

  test('should return null for a URL with an ignored prefix', ({ assert }) => {
    const ignoredUrl = 'javascript:alert(1)'
    assert.isNull(getAbsoluteUrl(ignoredUrl, baseUrl))
  })

  test('should return a full URL when a relative URL is provided', ({ assert }) => {
    const relativeUrl = '/path/to/resource'
    assert.equal(getAbsoluteUrl(relativeUrl, baseUrl), 'https://example.com/path/to/resource')
  })

  test('should return a full URL when an absolute URL is provided with the same hostname', ({
    assert,
  }) => {
    const absoluteUrl = 'https://example.com/path/to/resource'
    assert.equal(getAbsoluteUrl(absoluteUrl, baseUrl), 'https://example.com/path/to/resource')
  })

  test('should return null for an absolute URL with a different hostname', ({ assert }) => {
    const externalUrl = 'https://anotherdomain.com/path'
    assert.isNull(getAbsoluteUrl(externalUrl, baseUrl))
  })

  test('should return null for a subdomain URL', ({ assert }) => {
    const externalUrl = 'https://sub.example.com/path'
    assert.isNull(getAbsoluteUrl(externalUrl, baseUrl))
  })

  test('should return null for an invalid URL format', ({ assert }) => {
    const invalidUrl = 'htt://invalid-url'
    assert.isNull(getAbsoluteUrl(invalidUrl, baseUrl))
  })

  test('should strip the hash from a valid URL', ({ assert }) => {
    const urlWithHash = 'https://example.com/path#section'
    assert.equal(getAbsoluteUrl(urlWithHash, baseUrl), 'https://example.com/path')
  })

  test('should keep query params while stripping hash', ({ assert }) => {
    const url = '/path?q=1#frag'
    assert.equal(getAbsoluteUrl(url, baseUrl), 'https://example.com/path?q=1')
  })

  test('should resolve fragment-only link to base URL without hash', ({ assert }) => {
    const url = '#section'
    // Note: trailing slash is expected by URL normalization
    assert.equal(getAbsoluteUrl(url, baseUrl), 'https://example.com/')
  })

  test('should return null when protocol differs (strict same-origin)', ({ assert }) => {
    const httpUrl = 'http://example.com/path'
    assert.isNull(getAbsoluteUrl(httpUrl, baseUrl))
  })

  test('should handle ports strictly in origin comparison', ({ assert }) => {
    const baseWithPort = 'https://example.com:8080'
    const samePort = '/a'
    const differentPort = 'https://example.com:9090/a'

    assert.equal(getAbsoluteUrl(samePort, baseWithPort), 'https://example.com:8080/a')
    assert.isNull(getAbsoluteUrl(differentPort, baseWithPort))
  })

  test('should return null when baseUrl itself is invalid', ({ assert }) => {
    assert.isNull(getAbsoluteUrl('/a', 'not a url'))
  })

  test('should resolve relative paths with dot segments against a base with path', ({ assert }) => {
    const baseWithPath = 'https://example.com/dir/page'
    const relative = '../a'
    assert.equal(getAbsoluteUrl(relative, baseWithPath), 'https://example.com/a')
  })

  test('should return null for non-http(s) absolute URLs due to origin mismatch', ({ assert }) => {
    const wsUrl = 'ws://example.com/socket'
    assert.isNull(getAbsoluteUrl(wsUrl, baseUrl))
  })

  test('should ignore other listed schemes like tel: and mailto:', ({ assert }) => {
    assert.isNull(getAbsoluteUrl('tel:+123456789', baseUrl))
    assert.isNull(getAbsoluteUrl('mailto:user@example.com', baseUrl))
  })
})
