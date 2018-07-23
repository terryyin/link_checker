"""
Link checker for Less.works
"""
from __future__ import print_function
import re
import sys
import scrapy
import optparse
from scrapy.commands import runspider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


class STDErrorWriter():
    return_code = 0
    def __call__(self, text):
        print( text, file=sys.stderr)
        STDErrorWriter.return_code = 2


class LinkCheckerParser(scrapy.Spider):
    name = 'linkchecker'
    max_pages = 20
    start_urls = ['https://less.works/']
    #start_urls = ['http://localhost:3000/']
    custom_settings = {
        'USER_AGENT': "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 LeSS",
        'HTTPERROR_ALLOW_ALL': True
    }

    def __init__(self, error_writer=STDErrorWriter()):
        super(LinkCheckerParser, self).__init__()
        self.error_writer = error_writer

    def parse(self, response, parent=None):
        bot = LinkCheckerBot(response, self.start_urls[0])
        # linkedin and amazon don't allow HEAD requests
        if response.status == 405:
            yield scrapy.Request(response.url, method="GET", callback=lambda r: self.parse_405(r, parent))
        elif response.status // 100 != 2 and response.status != 999:
            self._error(response, parent=parent)
        else:
            if bot.is_unfetched_text() and bot.is_internal_link(response.url):
                yield scrapy.Request(response.url, method="GET", callback=lambda r: self.parse(r, parent))
        for next_page in bot.all_links():
            yield scrapy.Request(next_page, method="HEAD", callback=lambda r: self.parse(r, response.url))

    def parse_405(self, response, parent=None):
        if response.status // 100 != 2 and response.status != 999:
            self._error(response, parent=parent)

    def _error(self, response, parent=None):
        self.error_writer("{rsp.url}, status: {rsp.status}, parent: {parent}".format(
            rsp=response, parent=parent))


class LinkCheckerBot:
    def __init__(self, response, start_url):
        self.response = response
        self.start_url = start_url

    def all_links(self):
        for uri in list(self._css_links()) + list(self._html_links()):
            if 'linkedin.com' in uri:
                continue
            if 'amazonaws.com' in uri:
                continue
            next_page = self.response.urljoin(uri)
            yield next_page

    def is_unfetched_text(self):
        return self.response.request.method == "HEAD" and 'text' in self._content_type()

    def is_internal_link(self, next_page):
        return self.start_url in next_page

    def _css_links(self):
        if 'text/css' not in self._content_type():
            return
        for link in self._find_all_links_in_css(self.response.text):
            yield link

    def _html_links(self):
        for uri in self.response.css('::attr("href")') + self.response.css('::attr("src")'):
            yield uri.extract()
        for style in self.response.css('style'):
            for link in self._find_all_links_in_css(style.extract()):
                yield link

    def _find_all_links_in_css(self, content):
        for m in re.finditer(r"url\(\s*.(.*).\s*\)", content):
            yield m.group(1)

    def _content_type(self):
        return ''.join(str(x) for x in self.response.headers.getlist("content-type"))


def execute(argv):
    settings = get_project_settings()
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(),
                                   conflict_handler='resolve')
    cmd = runspider.Command()
    settings.setdict(cmd.default_settings, priority='command')
    cmd.settings = settings
    cmd.add_options(parser)
    opts, args = parser.parse_args(args=argv[2:])
    cmd.process_options(args, opts)

    crawler_process = CrawlerProcess(settings)
    crawler_process.crawl(LinkCheckerParser)
    crawler_process.start()
    return STDErrorWriter.return_code


if __name__ == '__main__':
    sys.exit(execute(['scrapy', 'runspider', '--nolog']))
