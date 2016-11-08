import sys
import scrapy

def stderr_writer(text):
    print( text, file=sys.stderr)

class LinkCheckerParser(scrapy.Spider):
    name = 'blogspider'
    start_urls = ['https://less.works/']
    custom_settings = {
        'HTTPERROR_ALLOW_ALL': True
    }

    def __init__(self, error_writer=stderr_writer):
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
