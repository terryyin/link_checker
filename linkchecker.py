from __future__ import print_function
import sys
import scrapy
from scrapy.commands import runspider
import optparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import re

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
        'HTTPERROR_ALLOW_ALL': True
    }

    def __init__(self, error_writer=STDErrorWriter()):
        super(LinkCheckerParser, self).__init__()
        self.error_writer = error_writer

    def parse(self, response, parent=None):
        if response.status // 100 != 2:
            self.error_writer("{response.url}, status: {response.status}, parent: {parent}".format(response=response, parent=parent))
        else:
            if response.request.method == "HEAD" and 'text' in self._content_type(response):
                yield scrapy.Request(response.url, method="GET", callback=lambda r: self.parse(r, parent))
        for uri in list(self._css_links(response)) + list(self._html_links(response)):
            next_page = response.urljoin(uri)
            if self.start_urls[0] in next_page:
                yield scrapy.Request(next_page, method="HEAD", callback=lambda r: self.parse(r, response.url))

    def _css_links(self, response):
        if 'text/css' not in self._content_type(response):
            return
        for link in self._find_all_links_in_css(response.text):
            yield link

    def _html_links(self, response):
        for uri in response.css('::attr("href")') + response.css('::attr("src")'):
            yield uri.extract()
        for style in response.css('style'):
            for link in self._find_all_links_in_css(style.extract()):
                yield link

    def _find_all_links_in_css(self, content):
        for m in re.finditer(r"url\(\s*.(.*).\s*\)", content):
            yield m.group(1)

    def _content_type(self, response):
        return ''.join(str(x) for x in response.headers.getlist("content-type"))

def execute(argv=None, settings=None):
    if settings is None:
        settings = get_project_settings()

    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(), \
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

