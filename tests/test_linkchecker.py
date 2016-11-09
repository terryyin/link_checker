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

class MyRequest:
    def __init__(self):
        self.method = 'GET'

test_domain = "http://domain/"
LinkCheckerParser.start_urls = [test_domain]

@pytest.fixture
def spider():
    writer = ErrorWriterForTest()
    return LinkCheckerParser(writer)

class TextResponseBuilder:
    def __init__(self):
        self.body_str = ""
        self.filename_str = ""
        self.status_code = 200
        self.request = MyRequest()

    def filename(self, fn):
        self.filename_str = fn
        return self

    def method(self, m):
        self.request.method = m
        return self

    def status(self, code):
        self.status_code = code
        return self

    def body(self, text):
        self.body_str += text
        return self

    def build(self, **kwargs):
        return scrapy.http.TextResponse(test_domain + self.filename_str, status=self.status_code, encoding="utf-8", body=self.body_str, request=self.request,**kwargs)

@pytest.fixture
def html_resp_builder():
    class HtmlResponseBuilder(TextResponseBuilder):
        def __init__(self):
            self.head_str = ""
            super(HtmlResponseBuilder, self).__init__()

        def link(self, text, link):
            self.body_str += "<a href='{}'>{}</a>".format(link, text)
            return self

        def head(self, code):
            self.head_str += code
            return self

        def build(self):
            return scrapy.http.HtmlResponse(test_domain, status=self.status_code, encoding="utf-8", body="<html><head>"+self.head_str+"</head><body>"+self.body_str+"</html>", headers={'Content-Type': 'text/html; charset=utf-8'}, request=self.request)

    return HtmlResponseBuilder()

@pytest.fixture
def css_builder():
    class CssResponseBuilder(TextResponseBuilder):
        def __init__(self):
            super(CssResponseBuilder, self).__init__()
            self.filename_str = "a.css"

        def build(self, **kwargs):
            return super(CssResponseBuilder, self).build(headers={'Content-Type': 'text/css; charset=utf-8'})
    return CssResponseBuilder()

@pytest.fixture
def image_resp_builder():
    class ImageResponseBuilder(TextResponseBuilder):
        def __init__(self):
            super(ImageResponseBuilder, self).__init__()
            self.filename_str = "a.png"

        def build(self, **kwargs):
            return super(ImageResponseBuilder, self).build(headers={'Content-Type': 'image/png; charset=utf-8'})
    return ImageResponseBuilder()


def test_head_response_of_html_page(spider, html_resp_builder):
    requests = [_ for _ in spider.parse(html_resp_builder.method("HEAD").build())]
    assert requests[0].method == "GET"

def test_head_response_of_image(spider, image_resp_builder):
    requests = [_ for _ in spider.parse(image_resp_builder.method("HEAD").build())]
    assert len(requests) == 0

def test_no_links_200(spider, html_resp_builder):
    requests = [_ for _ in spider.parse(html_resp_builder.build())]
    assert len(spider.error_writer.cache) == 0
    assert len(requests) == 0

def test_404(spider, html_resp_builder):
    [_ for _ in spider.parse(html_resp_builder.status(404).build(), parent="parent")]
    assert len(spider.error_writer.cache) == 1
    assert spider.error_writer.cache[0] == "http://domain/, status: 404, parent: parent"

def test_with_one_link(spider, html_resp_builder):
    requests = [_ for _ in spider.parse(html_resp_builder.link("a", "xxx.html").build())]
    assert len(requests) == 1
    assert requests[0].method == "HEAD"

def test_with_one_external_link(spider, html_resp_builder):
    requests = [_ for _ in spider.parse(html_resp_builder.link("a", "http://google.com").build())]
    assert len(requests) == 0

def test_with_image(spider, html_resp_builder):
    requests = [_ for _ in spider.parse(html_resp_builder.body("<img src='xxx.jpg'/>").build())]
    assert len(requests) == 1
    assert requests[0].method == "HEAD"

def test_with_link_in_head(spider, html_resp_builder):
    requests = [_ for _ in spider.parse(html_resp_builder.head("<link href='xxx.ico'>").build())]
    assert len(requests) == 1

def test_a_css_file(spider, css_builder):
    response = css_builder.body(".x{background:url('x.jpg')};").build()
    requests = [_ for _ in spider.parse(response)]
    assert len(requests) == 1
    assert requests[0].url == test_domain + 'x.jpg'

def test_a_different_css_file(spider, css_builder):
    response = css_builder.body(r'.x{background:url(  "x.jpg"  )};').build()
    requests = [_ for _ in spider.parse(response)]
    assert len(requests) == 1

def test_a_html_looks_like_css(spider, html_resp_builder):
    response = html_resp_builder.body(r'.x{background:url("x.jpg")};').build()
    requests = [_ for _ in spider.parse(response)]
    assert len(requests) == 0

def test_a_html_with_embedded_css(spider, html_resp_builder):
    response = html_resp_builder.body(r'<style>.x{background:url("x.jpg")};</style>').build()
    requests = [_ for _ in spider.parse(response)]
    assert len(requests) == 1

