package crawler

import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class FetcherTest {

    private val client = mockk<okhttp3.OkHttpClient>()
    private val fetcher = HttpFetcher(client)

    @Test
    fun `returns body on success`() = runTest {
        val call = mockk<okhttp3.Call>()
        val response = okhttp3.Response.Builder()
            .request(okhttp3.Request.Builder().url("https://example.com").build())
            .protocol(okhttp3.Protocol.HTTP_1_1)
            .code(200).message("OK")
            .body(okhttp3.ResponseBody.create(null, "hello"))
            .build()

        coEvery { client.newCall(any()) } returns call
        coEvery { call.execute() } returns response

        val result = fetcher.fetch("https://example.com")
        assertEquals("hello", result)
    }

    @Test
    fun `returns null on non-200`() = runTest {
        val call = mockk<okhttp3.Call>()
        val response = okhttp3.Response.Builder()
            .request(okhttp3.Request.Builder().url("https://example.com").build())
            .protocol(okhttp3.Protocol.HTTP_1_1)
            .code(404).message("Not Found")
            .body(okhttp3.ResponseBody.create(null, ""))
            .build()

        coEvery { client.newCall(any()) } returns call
        coEvery { call.execute() } returns response

        val result = fetcher.fetch("https://example.com")
        assertNull(result)
    }

    @Test
    fun `returns null on exception`() = runTest {
        val call = mockk<okhttp3.Call>()

        coEvery { client.newCall(any()) } returns call
        coEvery { call.execute() } throws RuntimeException("boom")

        val result = fetcher.fetch("https://example.com")
        assertNull(result)
    }
}