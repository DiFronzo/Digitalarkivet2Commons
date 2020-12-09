#!/usr/bin/env python3
from PIL import Image
from PIL.TiffTags import TAGS
import xml.etree.ElementTree as ET
from io import BytesIO
from bs4 import BeautifulSoup
from pywikibot.specialbots import UploadRobot
import dateutil.parser as parser
import requests
import re
import json

name = "Digitalarkivet2Commons"
api_version = 'v1'
user_agent = "{} {}".format(name, api_version)

script_version = '1.0.0'


class Client:
    """
        Example usage:
            from d2c import Client
            import pywikibot
            commons = pywikibot.Site("commons","commons")

            R = d2c.Client()
            R.query('/fotoweb/archives/5001-Historiske-foto/?q=reinbeite*') # print(R.pages)
                                                                            # to check what will be uploaded
            R.upload(summary="I like to upload images from Digitalarkivet", size="tif", commons)
    """

    urlDA = 'https://foto.digitalarkivet.no'

    headersPost = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'nb-NO,nb;q=0.9,no;q=0.8,nn;q=0.7,en-US;q=0.6,en;q=0.5,ja;q=0.4',
        'content-type': 'application/vnd.fotoware.download-request+json',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'x-requested-with': 'XMLHttpRequest',
    }

    headersGet = {
        'accept': 'application/vnd.fotoware.download-status+json, */*; q=0.01',
        'accept-language': 'nb-NO,nb;q=0.9,no;q=0.8,nn;q=0.7,en-US;q=0.6,en;q=0.5,ja;q=0.4',
        'content-type': 'application/vnd.fotoware.metadata-edit-request+json',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'x-requested-with': 'XMLHttpRequest',
    }

    Licenses = {
        'falt i det fri': "{{PD-old-70}}",
        'cc0': "{{CC0}}",
        'cc-0': "{{CC0}}",
        'cc-by': "{{CC BY 4.0}}",
        'cc by': "{{CC BY 4.0}}",
        'cc-by-sa': "{{CC BY-SA 4.0}}",
        'cc by-sa': "{{CC BY-SA 4.0}}",
    }

    Size = {
        "small_jpg": "/__renditions/Liten%20JPG",
        "tif": "/__renditions/Originalfil%20(tif)",
        "big_jpg": "/__renditions/Stor%20JPG",
    }

    File_Ending = {
        "small_jpg": ".jpg",
        "tif": ".tif",
        "big_jpg": ".jpg",
    }

    def __init__(
            self,
            requests_timeout=None,
            requests_session=True,
            user_agent=user_agent
    ):
        self.pages = []
        self.dont_upload = []
        if isinstance(requests_session, requests.Session):
            self._S = requests_session
        else:
            if requests_session:  # Build a new session.
                self._S = requests.Session()
            else:  # Use the Requests API module as a "session".
                raise NotImplementedError()

    def __dir__(self):
        return self.__dict__.keys()

    def query(self, query, limit=2000):
        """
        API POST
        @param query: Search term used for finding images.
        @type query: str
        @param limit: Max amount of pages to check for images.
        @type limit: int
        """
        url = "{}{}&p=".format(self.urlDA, query)  # for loop &p=1 til 54
        regeximg = r"\/fotoweb\/cache\/[0-9]{0,5}\/Indekserte%20bilder\/([^.]+)"
        listfiles = []
        notend = True
        pagenr = 0

        while notend or limit <= pagenr:
            response = self._S.get(url + str(pagenr))
            soup = BeautifulSoup(response.text, 'html.parser')
            endpage = soup.findAll('h1')
            if endpage and endpage[0]:
                notend = False
            div = soup.findAll('a', {"class": 'js-link thumbnail'})
            for htmltag in div:
                match = re.search(regeximg, str(htmltag.find('img', {"class": 'js-image'})), re.IGNORECASE)
                if match != None:
                    listfiles.append(
                        '/fotoweb/archives/5001-Historiske-foto/Indekserte%20bilder/' + match.group(1) + '.tif.info')
            pagenr += 1
        self.pages = listfiles
        return True

    def _post(self, page_list, size):
        """
        API POST
        @param page_list: 4 or less images from "self.pages"
        @type page_list: list
        @param size: Size for the image. Most be in "self.Size". Default "tif".
        @type size: str
        """
        data = {"request": {"assets": []}}  # MAX 4 IMAGES!!!
        for urlimg in page_list:
            data['request']['assets'].append({'href': urlimg + self.Size[size]})
        response = self._S.post(self.urlDA + '/fotoweb/me/background-tasks/', headers=self.headersPost,
                                data=json.dumps(data))
        rdata = response.json()
        if rdata["location"]:
            return rdata["location"]

        return False

    def _get(self, background_task):
        """
        API GET
        @param background_task: URL from POST request. Link to all the images that is request.
        @type background_task: str
        """
        not_finished = True
        data = {}

        while not_finished:
            response = self._S.get(self.urlDA + background_task, headers=self.headersGet)
            data = response.json()
            if data and data['job']['status'] == 'done':
                not_finished = False

        return data

    def get_metadata(self, src2, href2):
        """
        handle_upload
        @param src2: Images file page on foto.digitalarkivet.no.
        @type src2: str
        @param href2: Image download link on foto.digitalarkivet.no.
        @type href2: str
        """
        # CustomField1 = Originalformat, CustomField17 = Institusjon, CustomField18 = Arkivnavn, IF4b_kommentar =
        # Tilleggsinformasjon, IF22a_aksesjonsnummer = Arkivreferanse, UserDefined223 = URN kataloginfo, UserDefined233 = Restriksjon

        commons_data = {
            'title': '',
            'rights': [],
            'desc': '',
            'creator': [],
            'DateCreated': '',
            'Country': '',
            'CustomField1': '',
            'keywords': [],
            'CustomField17': '',
            'CustomField18': '',
            'UserDefined233': '',
            'IF22a_aksesjonsnummer': '',
            'IF4b_kommentar': '',
            'UserDefined223': '',
            'State': '',
            'City': '',
            'source': self.urlDA + src2,
            'href': self.urlDA + href2
        }
        response = self._S.get(commons_data['href'])
        with Image.open(BytesIO(response.content)) as img:
            meta_dict = {TAGS[key]: img.tag[key] for key in img.tag.keys()}
            # print(meta_dict['XMP']) #DEBUG

        tree = ET.fromstring(meta_dict['XMP'])

        nmspdict = {'x': 'adobe:ns:meta/',
                    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'dc': 'http://purl.org/dc/elements/1.1/',
                    'fwc': 'http://ns.fotoware.com/iptcxmp-custom/1.0/',
                    'fwu': 'http://ns.fotoware.com/iptcxmp-user/1.0/',
                    'photoshop': "http://ns.adobe.com/photoshop/1.0/",
                    'xmpRights': "http://ns.adobe.com/xap/1.0/rights/"}

        tags = tree.findall("rdf:RDF/rdf:Description/dc:subject/rdf:Bag/rdf:li",  # Nøkkelord
                            namespaces=nmspdict)

        tags2 = tree.findall("rdf:RDF/rdf:Description/dc:title/rdf:Alt/rdf:li",  # Tittel
                             namespaces=nmspdict)

        tags3 = tree.findall("rdf:RDF/rdf:Description/dc:creator/rdf:Seq/rdf:li",  # Opphavsperson
                             namespaces=nmspdict)

        gjenbruk = tree.findall("rdf:RDF/rdf:Description/xmpRights:UsageTerms/rdf:Alt/rdf:li",  # Gjenbruk
                                namespaces=nmspdict)

        rettigheter = tree.findall("rdf:RDF/rdf:Description/dc:rights/rdf:Alt/rdf:li",  # Rettigheter
                                   namespaces=nmspdict)

        desc = tree.findall("rdf:RDF/rdf:Description/dc:description/rdf:Alt/rdf:li",  # Beskrivelse
                            namespaces=nmspdict)

        for descAttri in tree.findall('rdf:RDF/rdf:Description', namespaces=nmspdict):
            zipped = zip(descAttri.attrib.keys(), descAttri.attrib.values())
            for keyZ, valZ in zipped:
                keyRegZ = re.sub(r'{.*}', '', keyZ)
                if keyRegZ in commons_data:
                    if valZ != '\n':
                        commons_data[keyRegZ] = valZ

        for nOrd in tags:
            commons_data['keywords'].append(nOrd.text)

        if tags2 and tags2[0].text:
            commons_data['title'] = tags2[0].text

        for creatorname in tags3:
            commons_data['creator'].append(creatorname.text)

        for rett in rettigheter:
            commons_data['rights'].append(rett.text)

        for gjen in gjenbruk:
            commons_data['rights'].append(gjen.text)

        if desc and desc[0].text:
            commons_data['desc'] = desc[0].text

        return commons_data

    def media_upload(self, metadata, commons, file_type):
        """
        handle_upload
        @param metadata: All of the choosen metadata from the tif image.
        @type metadata: dict
        @param commons: site that is used for upload
        @type commons: pywikibot.site.APISite
        """
        countryTrans = {'norge': 'Norway', 'sverige': 'Sweden', 'finland': 'Finland', 'danmark': 'Denmark'}  # 20.06.
        dateFix = parser.parse(metadata['DateCreated']).isoformat()[0:10] if len(metadata['DateCreated']) > 4 else \
            metadata['DateCreated']
        unknownValues = ['Country', 'State', 'City']

        for val in unknownValues:
            metadata[val] = '' if metadata[val] == '' or metadata[val].lower() == 'ukjent' else metadata[val]

        if 'Ukjent' not in metadata['creator']:
            for i, name_creator in enumerate(metadata['creator']):
                splitname = name_creator.split(',')
                metadata['creator'][i] = '{} {}'.format(splitname[1], splitname[0])

        if len(metadata['keywords']) > 1:
            for seq in range(1, len(metadata['keywords'])):
                metadata['keywords'][seq] = metadata['keywords'][seq].lower()

        url = [metadata['href']]
        summary = "[[Commons:Bots/Requests/IngeniousBot 2|TEST UPLOAD]]"
        keep_filename = False
        always = True
        use_filename = '{} ({}){}'.format(metadata['title'], metadata['UserDefined223'],file_type)
        filename_prefix = None
        verify_description = True
        ignore_warning = True
        aborts = set()
        chunk_size = 0
        recursive = False
        description_file = None
        description = '''=={{int:filedesc}}==
{{Information
|description     = {{nb|1= Bildet er hentet fra Arkivverket.\n'''
        description += '''{0}
* Arkivinstitusjon: {1}
* Arkivnavn: {2}
* Sted: {3}
* Emneord: {4}
* Avbildet:
        '''.format(metadata['desc'], metadata['CustomField17'], metadata['CustomField18'],
                   ', '.join(filter(None, [metadata['City'], metadata['State'], metadata['Country']])),
                   ', '.join(filter(None, metadata['keywords'])))
        description += '}}\n'
        description += '|date            = {{ISOdate|' + dateFix + '}}\n' if metadata['DateCreated'] and metadata[
            'DateCreated'] != '' else '|date            = \n'
        description += '|source          = [{0} foto.digitalarkivet.no]<br/>Arkivreferanse: {1}'.format(
            metadata['source'], metadata['IF22a_aksesjonsnummer']) + '<br/>{{institution:Arkivverket}}\n'
        description += '|author          = {{creator:unknown}}' if metadata['creator'] and 'Ukjent' in metadata[
            'creator'] else '|author          = ' + ', '.join(filter(None, metadata['creator']))
        description += '''
|permission      =
|other_versions  =
}}

=={{int:license-header}}==
'''
        for license_meta in metadata['rights']:
            if license_meta.lower() in self.Licenses:
                if license_meta.lower() == 'falt i det fri' and metadata['Country'].lower() == "norge":
                    description += "{{PD-Norway70}}"
                else:
                    description += self.Licenses[license_meta.lower()]

        description += '[[Category:{} (Arkivverket)]]'.format(metadata['CustomField18']) if metadata[
                                                                                                'CustomField18'] and \
                                                                                            metadata[
                                                                                                'CustomField18'] != '' else '[[Category:Media from the National Archives of Norway]]'
        description += '[[Category:{} in {}]]'.format(dateFix[0:4],
                                                      countryTrans[metadata['Country'].lower()]) if dateFix and \
                                                                                                    metadata[
                                                                                                        'Country'].lower() in countryTrans else ''
        if metadata['UserDefined233'].lower() == 'ja':
            self.dont_upload.append(metadata['source'])

        if metadata['source'] in self.dont_upload:
            return 0

        do_not_exist = True
        number_file = 1
        while do_not_exist:
            page = pywikibot.Page(commons, "File:" + use_filename)
            if page.exists():
                if page.text == description:
                    return 0  # Exists
                elif pywikibot.Page(commons, 'File:{} ({}) {}{}'.format(metadata['title'], metadata['UserDefined223'],
                                                                          number_file, file_type)).exists():
                    number_file += 1
                else:
                    use_filename = '{} ({}) {}{}'.format(metadata['title'], metadata['UserDefined223'], number_file,
                                                                            file_type)
                    do_not_exist = False
            else:
                do_not_exist = False

        bot = UploadRobot(url, description=description, use_filename=use_filename,
                          keep_filename=keep_filename,
                          verify_description=verify_description, aborts=aborts,
                          chunk_size=chunk_size, ignore_warning=ignore_warning,
                          always=always, summary=summary,
                          filename_prefix=filename_prefix, target_site=commons)
        bot.run()

    def handle_upload(self, page_list, size, commons):
        """
        handle_upload
        @param page_list: 4 or less images for "self.pages"
        @type page_list: list
        @param size: Size for the image. Most be in "self.Size". Default "tif".
        @type size: str
        @param commons: site that is used for upload
        @type commons: pywikibot.site.APISite
        """
        location = self._post(page_list, size)
        result = self._get(location)
        file_type = self.File_Ending[size]

        for img in result['job']['result']['files']:
            meta = self.get_metadata(img['src'], img['href'])
            self.media_upload(meta, commons, file_type)
        return 0

    def upload(self, summary, size="tif", commons):
        """
        upload
        @param summary: Summary for each upload. Can be in wiki-syntax
        @type data: str
        @param size: Size for the image. Most be in "self.Size". Default "tif".
        @type size: str
        @param commons: site that is used for upload
        @type commons: pywikibot.site.APISite
        """
        if self.pages and size in self.Size:
            for num, val in enumerate(self.pages, start=1):
                if num % 4 == 0:
                    self.handle_upload(self.pages[num - 4:num], size, commons)
                elif val == self.pages[-1]:
                    self.handle_upload(self.pages[(len(self.pages) % 4) * -1::], size, commons)
            print("Done")
            return 0
