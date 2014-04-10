import json
import re
import webapp2
import urlparse
from lxml import etree
import lxml.html
import random

import sys
sys.path.insert(0, 'libs')

from BeautifulSoup import BeautifulSoup 

import requests
from requests.adapters import HTTPAdapter

import logging
logger = logging.getLogger(__name__)

from globals import URL_BASE 
from globals import X_PARSE_APPLICATION_ID 
from globals import X_PARSE_REST_API_KEY 
from globals import URL_PARSE_PROXY
from globals import URL_PARSE_BATCH 
from globals import URL_PARSE_BATCH_PROXY
from globals import IF_DEBUG
from globals import PARSE_BATCH_LIMIT
from globals import REQUESTS_MAX_RETRIES
from globals import REQUESTS_TIMEOUT
from globals import URL_PARSE_QUERY_LIMIT
    
import itertools
from itertools import tee, izip
from itertools import izip_longest

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
        # requests: retries, user-agent and Parse id/key
        self.session = requests.Session()
        self.session.mount('http://', HTTPAdapter(max_retries=REQUESTS_MAX_RETRIES))
        self.session.mount('https://', HTTPAdapter(max_retries=REQUESTS_MAX_RETRIES))
        headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'X-Parse-Application-Id': X_PARSE_APPLICATION_ID, 
                'X-Parse-REST-API-Key': X_PARSE_REST_API_KEY,
                'Content-Type': 'application/json'}
        self.session.headers = headers


        # get current proxies, will delete them afterward
        current_proxy = self.get_proxy()

        logging.info("len of current_proxy: %d", len(current_proxy))

        pages = []
        if IF_DEBUG:
            pages.append(self.get_pages_dbg())
        else:
            main_page = self.get_main_page()
            # get other pages from main_page
            pagination = self.parse_pagination(main_page)
            pages_after = self.get_pages(pagination)
            pages = [main_page] + pages_after

        new_proxy = []

        for p in pages:
            r = self.parse_page(p)
            new_proxy += r

        logging.info("len of new_proxy: %d", len(new_proxy))

        if new_proxy:
            # push new proxy to Parse
            self.post_parse(new_proxy, if_delete=False)
            # remove old proxy
            self.post_parse(current_proxy, if_delete=True)

    def make_batch(self, list_, if_delete=False):
        list_request = []

        dict_request = {"requests":[]}
        # FIXME
        # make it neat
        i = 0
        for l in list_:
            if if_delete:
                item = {"method": "DELETE",
                        "path": URL_PARSE_BATCH_PROXY+"/"+l.get("objectId")}
            else:
                item = {"method": "POST",
                        "path": URL_PARSE_BATCH_PROXY,
                        "body": l}
                
            dict_request["requests"].append(item)
            i+=1

            if i == PARSE_BATCH_LIMIT:
                list_request.append(dict_request)
                dict_request = {"requests":[]}
                i=0

        if dict_request.get("requests"):
            list_request.append(dict_request)

        return list_request
    
    def http_get(self, url, params=None, data=None, timeout=REQUESTS_TIMEOUT):
        logging.info("http_get(): %s, %s"%(url, params))
            
        if data:
            logging.info(data)
            response = self.session.post(url, params=params, data=data, timeout=timeout)
        else:
            response = self.session.get(url, params=params, timeout=timeout)

        if response.status_code != 200:
            logging.info(response.text)
            raise BaseException("http_get(): response_code != 200")
        else:
            return response

    def get_proxy(self):
        payload = {"limit": URL_PARSE_QUERY_LIMIT}
        response = self.http_get(URL_PARSE_PROXY, params=payload)
        response_json = response.json()

        return response_json.get("results")

    def post_parse(self, proxy, if_delete):

        batches = self.make_batch(proxy, if_delete)

        for b in batches:
            data = json.dumps(b)
            response = self.http_get(URL_PARSE_BATCH, data=data)
            # should check: if all returns success
        
    def get_main_page(self):
        return self.http_get(URL_BASE).text

    def get_pages_dbg(self):
        text = open("text.html","rb").read()

        return text
 
    def get_pages(self, pagination):
        if IF_DEBUG:
            pagination = pagination[0:1]

        pages = []
        for p in pagination:
            url = urlparse.urljoin(URL_BASE, p)
            response_text = self.http_get(url).text

            pages.append(response_text)

        return pages 

    def parse_pagination(self, page):
        tree = lxml.html.fromstring(page)

        div_pagination = tree.xpath('//div[@class="pagination"]//li//a/@href')
        div_pagination.pop()
        logging.info(div_pagination)       
        return div_pagination


    def parse_page(self, page):
        def pairwise(iterable):
            a, b = tee(iterable)
            next(b, None)
            return izip(a, b)

        def chunks(l, n):
            """ Yield successive n-sized chunks from l.
            """
            for i in xrange(0, len(l), n):
                yield l[i:i+n]

        def grouper(n, iterable, padvalue=None):
            return izip_longest(*[iter(iterable)]*n, fillvalue=padvalue)

        tree = lxml.html.fromstring(page)
        #td_ip_port = tree.xpath('//table//td[(position()="2") and (position()="3")]')
        td_ip_port_ = tree.xpath('//table//td')
        td_ip_port_ = grouper(8, td_ip_port_)

        #td_ip_port = [ [x[1],x[2],x[4],x[5]] for x in td_ip_port_ ]
        td_ip_port = [ x[1:] for x in td_ip_port_ ]
        list_result = []

        for td_ip, td_port, td_country, td_rtime, td_ctime, td_type, td_anonymity in td_ip_port:
            ip = ""
            port = ""
            country = ""
            response_time = 0
            connection_time = 0
            proxy_type = ""
            anonymity = ""

            try:
                # anonymity
                anonymity = td_anonymity.text

                # proxy_type
                proxy_type = td_type.text

                # country
                country = td_country.attrib.get("rel")

                # response_time
                response_time_ = td_rtime.find('div').find('div').attrib.get("style")
                re_response_time = re.search(r'width:(\d*)%',response_time_)
                response_time = int(re_response_time.group(1))

                # connection_time 
                connection_time_ = td_ctime.find('div').find('div').attrib.get("style")
                re_connection_time = re.search(r'width:(\d*)%',connection_time_)
                connection_time = int(re_connection_time.group(1))

                # ip
                ip_root_span = td_ip.find('span')
                ip_style = ip_root_span.find('style').text.strip().split("\n")
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
                # port
                port = td_port.text.strip()

            except:
                pass

            if( ip and port ):
                #list_result.append("%s:%s"%(ip,port))
                list_result.append( 
                        {
                            "ip": ip,
                            "port": port,
                            "country": country, 
                            "response_time": response_time,
                            "connection_time": connection_time,
                            "type": proxy_type,
                            "anonymity": anonymity
                            }
                        )
        
        logger.info(list_result)
        logger.info("len of above: %d" % len(list_result))
        return list_result
        

class mainPage(webapp2.RequestHandler):

    def post(self):
        #logging.info(self.request)
        return

    def get(self):
        hma = ParseHMA()
        return 
 
application = webapp2.WSGIApplication([
    ('/update', mainPage)], debug=True)
