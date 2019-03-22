from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from urllib import request, error
from PyPDF2 import utils, PdfFileReader
import urllib
import os
import io
import time

_DIRECTORY = "../../target/generated-resources/"


class PDF:
    def __init__(self, source, name):
        self.source = source
        self.name = name
        self.pdfReader = PdfFileReader(io.BytesIO(self.source))

    def is_10K(self):
        try:
            if self.pdfReader.isEncrypted:
                self.decrypt()
            if self.pdfReader is None:
                return False
            for i in range(0, self.pdfReader.getNumPages()):
                pageObj = self.pdfReader.getPage(i)
                text = str(pageObj.extractText())
                if 'SECURITIES AND EXCHANGE COMMISSION' in text:
                    if '10-K' in text:
                        return True
                    else:
                        return False

        except utils.PdfReadError as e:
            log_error('Error while reading from PDF object {0}: {1}'.format(self.name, str(e)))
            return None

    def get_year(self):
        try:
            if self.pdfReader.isEncrypted:
                self.decrypt()
            if self.pdfReader is None:
                return -1
            for i in range(0, self.pdfReader.getNumPages()):
                pageObj = self.pdfReader.getPage(i)
                text = str(pageObj.extractText())
                if 'SECURITIES AND EXCHANGE COMMISSION' in text:
                    text = str(pageObj.extractText()).split(',')[2].lstrip()
                    year = int(text[:4])
                    if year > 1000:
                        return year
                    else:
                        return -1

        except utils.PdfReadError as e:
            log_error('Error while reading from PDF object {0}: {1}'.format(self.name, str(e)))
            return None

    def decrypt(self):
            try:
                self.pdfReader.decrypt('')
                print('File Decrypted (PyPDF2)')
            except NotImplementedError as e:
                command = ("cp " + self.name +
                           " temp.pdf; qpdf --password='' --decrypt temp.pdf " + self.name
                           + "; rm temp.pdf")
                os.system(command)
                print('File Decrypted (qpdf)')
                try:
                    fp = open(self.name)
                    return PdfFileReader(fp)
                except FileNotFoundError as e:
                    log_error('Error while reading from file {0}: {1}'.format(self.name, str(e)))
                    return None


def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def get_report():
    """
    Downloads the PDFs from the given url
    """
    urls = []
    names = []
    _TICKER = "DIS"
    _DOMAIN = "https://www.thewaltdisneycompany.com/investor-relations/"
    _URL = _DOMAIN #+ "/investor"
    response = simple_get(_URL)
    start = time.time()

    if response is not None:
        response = BeautifulSoup(response, 'html.parser')

        for i, link in enumerate(response.findAll('a')):
            _FULLURL = str(link.get('href'))
            _TYPE = str(link.get('type'))
            if 'pdf' in _TYPE or '.pdf' in _FULLURL:
                if not str(_FULLURL).startswith('http'):
                    _FULLURL = _DOMAIN + _FULLURL
                urls.append(_FULLURL)
                name = response.select('a')[i].attrs['href'].replace('/', '_').split('.com')[1]
                if not name.endswith('.pdf'):
                    name = name + '.pdf'
                names.append(name)
        names_urls = zip(names, urls)

        # Create target folder if it does not exist
        TARGET_PATH = _DIRECTORY + _TICKER
        create_directory(TARGET_PATH)

        numberOfFiles = 0
        for name, url in names_urls:
            try:
                rq = urllib.request.urlopen(url)
                pdf = rq.read()
                header = rq.info()
                if 'Content-Disposition' in str(header) or 'application/pdf' in str(header):
                    pdfObj = PDF(pdf, name)
                    if PDF.is_10K(pdfObj):
                        pdfYear = pdfObj.get_year()
                        year = str(pdfYear) if pdfYear > 0 else 'etc'
                        path = TARGET_PATH + '/' + year + '/'
                        create_directory(path)
                        with open(path+name, 'wb') as f:
                            f.write(pdf)
                            numberOfFiles += 1
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    log_error('File not found during requests to {0} : {1}'.format(_URL, str(e)))
                else:
                    raise
        end = time.time()
        print('Execution Time: ' + str(round(end - start, 2)) + ' seconds')
        print('Number of files copied over: ' + str(numberOfFiles))
    else:
        # Raise an exception if we failed to get any data from the url
        log_error('error found for {}'.format(response))
        raise Exception('Error retrieving contents at {}'.format(_URL))


def is_good_response(resp):
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def create_directory(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def log_error(e):
    print(e)


get_report()


