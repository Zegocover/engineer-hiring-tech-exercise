plugins {
    kotlin("jvm") version "1.9.23"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    // Kotlin + Coroutines
    implementation("org.jetbrains.kotlin:kotlin-stdlib")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")

    // HTTP Client
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // HTML Parser
    implementation("org.jsoup:jsoup:1.18.1")

    // Logging (optional but recommended)
    implementation("org.slf4j:slf4j-simple:2.0.12")

    // --- TESTING ---
    testImplementation(kotlin("test"))
    // Ktor (for integration test server)
    testImplementation("io.ktor:ktor-server-netty:2.3.9")
    testImplementation("io.ktor:ktor-server-core:2.3.9")
    testImplementation("io.ktor:ktor-server-host-common:2.3.9")
    testImplementation("io.ktor:ktor-server-test-host:2.3.9")
    testImplementation("io.mockk:mockk:1.13.12")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("org.junit.jupiter:junit-jupiter-params:5.10.2")
    testImplementation("io.kotest:kotest-runner-junit5:5.8.0")
}

application {
    mainClass.set("crawler.MainKt")
}

tasks.test {
    useJUnitPlatform()
}