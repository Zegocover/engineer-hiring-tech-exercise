package crawler

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

interface Fetcher {
    suspend fun fetch(url: String): String?
}

class HttpFetcher(
    private val client: OkHttpClient = OkHttpClient()
) : Fetcher {

    override suspend fun fetch(url: String): String? = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url).get().build()

        runCatching {
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return@runCatching null
                resp.body?.string()
            }
        }.getOrNull()
    }
}