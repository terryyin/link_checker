'''
* follow all the hrefs, srcs in html on own site
* follow a redirection when it redirects to own site
* report broken link
'''
import pytest
from linkchecker import LinkCheckerParser
import scrapy

class ErrorWriterForTest(object):
    def __init__(self):
        self.cache = []

    def __call__(self, text):
        self.cache.append(text)

test_domain = "http://domain"
LinkCheckerParser.start_urls = [test_domain]

@pytest.fixture
def spider():
    writer = ErrorWriterForTest()
    return LinkCheckerParser(writer)

@pytest.fixture
def resp_builder():
    class ResponseBuilder:
        def __init__(self):
            self.body = ""
            self.status_code = 200

        def status(self, code):
            self.status_code = code
            return self

        def link(self, text, link):
            self.body += "<a href='{}'>{}</a>".format(link, text)
            return self

        def build(self):
            return scrapy.http.HtmlResponse(test_domain, status=self.status_code, encoding="utf-8", body="<html><body>"+self.body+"</html>")
    return ResponseBuilder()



def test_no_links_200(spider, resp_builder):
    requests = [_ for _ in spider.parse(resp_builder.build())]
    assert len(spider.error_writer.cache) == 0
    assert len(requests) == 0

def test_404(spider, resp_builder):
    [_ for _ in spider.parse(resp_builder.status(404).build(), parent="parent")]
    assert len(spider.error_writer.cache) == 1
    assert spider.error_writer.cache[0] == "http://domain, status: 404, parent: parent"

def test_with_one_link(spider, resp_builder):
    requests = [_ for _ in spider.parse(resp_builder.link("a", "xxx").build())]
    assert len(requests) == 1

def test_with_one_external_link(spider, resp_builder):
    requests = [_ for _ in spider.parse(resp_builder.link("a", "http://google.com").build())]
    assert len(requests) == 0

