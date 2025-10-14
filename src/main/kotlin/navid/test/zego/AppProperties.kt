package navid.test.zego

import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.boot.context.properties.NestedConfigurationProperty

@ConfigurationProperties(prefix = "app", ignoreUnknownFields = false)
data class AppProperties(
    @NestedConfigurationProperty
    val retry: RetryProperties,
    val connectionTimeout: Long,
)

@ConfigurationProperties(prefix = "app.retry", ignoreUnknownFields = false)
data class RetryProperties(
    val maxAttempts: Int,
    val interval: Long,
    val maxInterval: Long,
    val backOffMultiplier: Double
)
