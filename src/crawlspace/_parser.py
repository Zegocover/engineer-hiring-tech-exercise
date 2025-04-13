class Parser:
    @staticmethod
    def parse(url: str, page: str) -> set[str]:
        match url:
            case "http://localhost:8888":
                return {"http://localhost:8888/empty-page"}

            case "http://localhost:8888/empty-page":
                return set()

            case _:
                return set()
