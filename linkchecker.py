from __future__ import print_function
import sys
import scrapy
from scrapy.commands import runspider
import optparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


class STDErrorWriter():
    return_code = 0
    def __call__(self, text):
        print( text, file=sys.stderr)
        STDErrorWriter.return_code = 2

class LinkCheckerParser(scrapy.Spider):
    name = 'linkchecker'
    start_urls = ['https://less.works/']
    #start_urls = ['http://localhost:3000/less/framework/']
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
            for quote in response.css('a'):
                uri = quote.css('a::attr("href")').extract_first()
                next_page = response.urljoin(uri)
                if self.start_urls[0] in next_page:
                    #self.error_writer(next_page)
                    yield scrapy.Request(next_page, callback=self.parse)

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

