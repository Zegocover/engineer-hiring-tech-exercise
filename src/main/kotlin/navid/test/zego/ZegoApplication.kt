package navid.test.zego

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.boot.runApplication

@SpringBootApplication
@EnableConfigurationProperties(
    AppProperties::class,
    RetryProperties::class
)
class ZegoApplication

fun main(args: Array<String>) {
    runApplication<ZegoApplication>(*args)
}
