
scalaVersion := "3.7.4"

libraryDependencies ++= Seq(
  "com.softwaremill.sttp.client4" %% "core" % "4.0.13",
  "ch.digitalfondue.jfiveparse" % "jfiveparse" % "1.1.4",
  "org.scalatest" %% "scalatest-flatspec" % "3.2.19" % Test,
  "org.scalatest" %% "scalatest-shouldmatchers" % "3.2.19" % Test
)
