package crawler

import org.scalatest.OptionValues
import org.scalatest.matchers.should.Matchers
import org.scalatest.wordspec.AnyWordSpec

class UrlVisitStrategySpec extends AnyWordSpec with Matchers with OptionValues {

  "Same-Domain URL VisitStrategy" when {
    "Given a base URL for a domain" should {
      val urlVisitStrategy = new SameDomainStrategy(PageUrl("http://www.example.com").value)
      "return isForTraverse=true for same domain" in {
        val sameDomainUrl = PageUrl("http://www.example.com/one/two").value
        urlVisitStrategy.isForTraverse(sameDomainUrl) shouldBe true
      }
      "return isForTraverse=false for different domains" in {
        val differentDomainUrl = PageUrl("http://someothersite.com/one/two").value
        urlVisitStrategy.isForTraverse(differentDomainUrl) shouldBe false

        val differentDomainUrl2 = PageUrl("http://sub.example.com/one/two").value
        urlVisitStrategy.isForTraverse(differentDomainUrl2) shouldBe false
      }
    }
    "Given a base URL for a domain with port" should {
      val urlVisitStrategy = new SameDomainStrategy(PageUrl("http://localhost:8080").value)
      "return isForTraverse=true for same domain" in {
        val sameDomainUrl = PageUrl("http://localhost:8080/one/two").value
        urlVisitStrategy.isForTraverse(sameDomainUrl) shouldBe true
      }
      "return isForTraverse=false for same domain with no port" in {
        val sameDomainUrl = PageUrl("http://localhost/one/two").value
        urlVisitStrategy.isForTraverse(sameDomainUrl) shouldBe false
      }
    }
  }
}
