"""A simple webapp2 server."""
import json
import re
import webapp2
import urllib2
import time
import datetime
import urlparse
from datetime import timedelta
from google.appengine.ext import db
from lxml import etree
import lxml.html
from io import StringIO
import random

import sys
sys.path.insert(0, 'libs')
from BeautifulSoup import BeautifulSoup 

import logging
logger = logging.getLogger(__name__)

from globals import USER_AGENT 
from globals import URL_BASE 
from globals import X_PARSE_APPLICATION_ID 
from globals import X_PARSE_REST_API_KEY 
from globals import URL_PARSE 

from itertools import izip

USER_AGENTS = [
    'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10',
    'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en) AppleWebKit/125.2 (KHTML, like Gecko) Safari/125.8',
    'Opera/9.80 (Macintosh; Intel Mac OS X; U; en) Presto/2.2.15 Version/10.00',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_1) AppleWebKit/536.25 (KHTML, like Gecko) Version/6.0 Safari/536.25',
    'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25',
    'Mozilla/5.0 (compatible; MSIE 10.6; Windows NT 6.1; Trident/5.0; InfoPath.2; SLCC1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 2.0.50727) 3gpp-gba UNTRUSTED/1.0',
    ]



class ParseHMA:
    def __init__(self):
        self.pages = []
        self.pages.append(self.get_main_page())
        self.pagination = self.parse_pagination(self.pages[0])
        self.get_pages()
        self.proxies = []
        for p in self.pages:
            r = self.parse_ip_port(p)
            self.proxies += r

        self.proxies_json = []
        self.list_to_json()

    def list_to_json(self):
        for p in self.proxies:
            self.proxies_json.append({"ip":p})

    def put_parse(self):
        request = urllib2.Request(URL_PARSE)
        request.add_header('X-Parse-Application-Id', X_PARSE_APPLICATION_ID)
        request.add_header('X-Parse-REST-API-Key', X_PARSE_REST_API_KEY)
        request.add_header('Content-Type', 'application/json')
        data = json.dumps(self.proxies_json)
        data = json.dumps([{"ip":"123123123ggiiii"},{"ip":"iia1sgsdg"}])
        response = urllib2.urlopen(request, data=data)
        logger.info(response.read())


               


    def get_page_dbg(self, url):
         return open("text.html","rb")
        
    def get_main_page(self):
        request = urllib2.Request(URL_BASE)
        request.add_header('User-Agent',random.choice(USER_AGENTS))
        response = urllib2.urlopen(request)
        response_code = response.getcode()
        if response_code != 200:
            response_text = ""
            return
        else:
            response_text = response.read()
            return response_text

 
    def get_pages(self):

        for p in self.pagination:
            url = urlparse.urljoin(URL_BASE, p)
            request = urllib2.Request(url)
            request.add_header('User-Agent',random.choice(USER_AGENTS))
            response = urllib2.urlopen(request)
            response_code = response.getcode()

            if response_code != 200:
                response_text = ""
            else:
                response_text = response.read()

            self.pages.append(response_text)

        return self.pages 

    def parse_pagination(self, page):
        tree = lxml.html.fromstring(page)

        div_pagination = tree.xpath('//div[@class="pagination"]//li//a/@href')
        div_pagination.pop()
        logging.info(div_pagination)       
        return div_pagination


    def parse_ip_port(self, page):
        def pairwise(iterable):
            a = iter(iterable)
            return izip(a, a)

        tree = lxml.html.fromstring(page)
        

        td_ip_port = tree.xpath('//table//td[position()>1 and position()<4]')

        list_ip_port = []

        for td_ip, td_port in pairwise(td_ip_port[2:]):
            ip = ""
            port = ""
            try:
                ip_root_span = td_ip.find('span')
                ip_style = ip_root_span.find('style').text.strip().split("\n")
                # .drc9{display:inline}
                ip_style_inline = [ m.group(1) for x in ip_style for m in [re.search(r'\.(.*){display:inline',x)] if m ]

                ip_free_text = ip_style = ip_root_span.text
                ip_spans = ip_root_span.getchildren()

                for s in ip_spans:
                    attr = s.attrib
                    text = s.text
                    tail = s.tail
                    span_style = attr.get("style")
                    span_class = attr.get("class")
                    if(span_class in ip_style_inline) or (span_class.isdigit() if span_class else False) or (span_style == "display: inline"): 
                        ip = ip+text
                    if tail:
                        ip = ip+tail

                port = td_port.text.strip()
            except:
                pass

            #logger.info("%s:%s"%(ip,port))
            list_ip_port.append("%s:%s"%(ip,port))
        
        #logger.info(list_ip_port)
        #logger.info(len(list_ip_port))
        return list_ip_port
        

class mainPage(webapp2.RequestHandler):

    def post(self):
        #logging.info(self.request)
        return

    def get(self):
        hma = ParseHMA()
        logger.info(hma.proxies)
        logger.info(len(hma.proxies))
        hma.put_parse()
        return 
 
application = webapp2.WSGIApplication([
    ('/', mainPage)], debug=True)
