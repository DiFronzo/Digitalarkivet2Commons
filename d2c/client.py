#!/usr/bin/env python3
from PIL import Image
from PIL.TiffTags import TAGS
import xml.etree.ElementTree as ET
from io import BytesIO
from pywikibot.specialbots import UploadRobot
import dateutil.parser as parser
import pywikibot
import requests
import re
import json
import time

name = "Digitalarkivet2Commons"
api_version = 'v1'
user_agent = "{} {}".format(name, api_version)

script_version = '1.0.1'


class Client:
    """
        Example usage:
            from d2c import Client as d2c
            import pywikibot
            commons = pywikibot.Site("commons","commons")

            r = d2c.Client()
            r.query('/fotoweb/archives/5001-Historiske-foto/;o=+?q=reinbeite*') # print(r.pages)
                                                                            # to check images that will be uploaded
            r.upload(commons, file_ending="tif", summary="I like to upload images from Digitalarkivet")
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
        'falt i det fri': "{{PD-Norway50}}",
        'cc0': "{{CC0}}",
        'cc-0': "{{CC0}}",
        'cc-by': "{{CC BY 4.0}}",
        'cc by': "{{CC BY 4.0}}",
        'cc-by-sa': "{{CC BY-SA 4.0}}",
        'cc by-sa': "{{CC BY-SA 4.0}}",
    }

    SizeOld = {
        "small_jpg": "/__renditions/Liten%20JPG",
        "tif": "/__renditions/Originalfil%20(tif)",
        "big_jpg": "/__renditions/Stor%20JPG",
    }
    
    Size = {
        "small_jpg": "/__renditions/cb53ad28-fc46-445d-9bed-3fce5bf0570d",
        "tif": "/__renditions/06df8390-99b9-478a-87c9-939148dba0a0",
        "big_jpg": "/__renditions/7e57641d-85a1-47b3-9637-0f2db54b49ea",
    }

    File_ending = {
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
            else:  # todo: Use the Requests API module as a "session".
                raise NotImplementedError()

    def __dir__(self):
        return self.__dict__.keys()

    def query(self, query, limit=2000):
        """
        query
        @param query: Search term used for finding images.
        @type query: str
        @param limit: Max amount of pages to check for images.
        @type limit: int

        :return: return True if success
        :rtype: the return type bool
        """
        is_last = False
        pagenr = 0
        list_files = []
        url = self.urlDA + query

        while True or limit <= pagenr:

            response = self._S.get(url,
                                   headers={'Accept': 'application/vnd.fotoware.assetlist+json, */*; '
                                                      'q=0.01'})
            data = response.json()

            for ref in data["data"]:
                if ref['href'].endswith(".tif.info"):
                    list_files.append(ref['href'])
            pagenr += 1

            if is_last:
                break

            if data['paging']['next'] == "":
                url = self.urlDA + data['paging']['last']
                is_last = True
            else:
                url = self.urlDA + data['paging']['next']
            # break
        self.pages = list_files

    def _post(self, page_list, size):
        """
        API POST
        @param page_list: 4 or less images from "self.pages"
        @type page_list: list
        @param size: Size for the image. Most be in "self.Size". Default "tif".
        @type size: str

        :return: return True if success
        :rtype: the return type bool
        """
        data = {"request": {"assets": []}}  # Takes MAX 4 images in one request!
        for urlimg in page_list:
            data['request']['assets'].append({'href': urlimg + size})
        response = self._S.post(self.urlDA + '/fotoweb/me/background-tasks/', headers=self.headersPost,
                                data=json.dumps(data))
        rdata = response.json()
        if "message" in rdata:
            raise TypeError(rdata["message"])
            
        if rdata["location"]:
            return rdata["location"]

        return False

    def _get(self, background_task):
        """
        API GET
        @param background_task: part of the url for access to image
        @type background_task: str

        :return: return the JSON object
        :rtype: the return type dict
        """
        not_finished = True
        data = {}

        while not_finished:
            response = self._S.get(self.urlDA + background_task, headers=self.headersGet)
            data = response.json()
            if data and data['job']['status'] == 'done':
                not_finished = False

        return data

    def get_metadata(self, src2, href2, file_ending):
        """
        get_metadata
        @param src2: Images page file on foto.digitalarkivet.no.
        @type src2: str
        @param href2: Image download link on foto.digitalarkivet.no.
        @type href2: str
        @param file_ending: Type of image file. Valid options: tif, small_jpg or big_jpg.
        @type file_ending: str

        :return: returns a JSON object with metadata
        :rtype: the return type dict
        """
        # CustomField1 = Originalformat, CustomField17 = Institusjon, CustomField18 = Arkivnavn, IF4b_kommentar =
        # Tilleggsinformasjon, IF22a_aksesjonsnummer = Arkivreferanse, UserDefined223 = URN kataloginfo,
        # UserDefined233 = Restriksjon, digitalarkivetName = Unique name from digitalarkivet

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
            'digitalarkivetName': re.match(r'.+/(.+)\.', href2)[1],
            'source': self.urlDA + src2,
            'href': self.urlDA + href2
        }
        response = self._S.get(commons_data['href'])
        meta_dict2 = ""
        if file_ending == "tif":
            with Image.open(BytesIO(response.content)) as img:
                meta_dict = {TAGS[key]: img.tag[key] for key in img.tag.keys()}
                # print(meta_dict['XMP']) #DEBUG
                meta_dict2 = ET.fromstring(meta_dict['XMP'])

        elif file_ending == "small_jpg" or file_ending == "big_jpg":
            with Image.open(BytesIO(response.content)) as im:
                for segment, content in im.applist:
                    if segment == 'APP1' and content.startswith(b'http://ns.adobe.com/xap/1.0/'):
                        # print(content[29::]) #DEBUG
                        meta_dict2 = ET.fromstring(content[29::])
                        break
        else:
            raise TypeError(
                f"File type, {file_ending}, is out of the scope"
            )

        tree = meta_dict2

        nmspdict = {'x': 'adobe:ns:meta/',
                    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'dc': 'http://purl.org/dc/elements/1.1/',
                    'fwc': 'http://ns.fotoware.com/iptcxmp-custom/1.0/',
                    'fwu': 'http://ns.fotoware.com/iptcxmp-user/1.0/',
                    'photoshop': "http://ns.adobe.com/photoshop/1.0/",
                    'xmpRights': "http://ns.adobe.com/xap/1.0/rights/"}

        tags = tree.findall("rdf:RDF/rdf:Description/dc:subject/rdf:Bag/rdf:li",  # Keyword
                            namespaces=nmspdict)

        tags2 = tree.findall("rdf:RDF/rdf:Description/dc:title/rdf:Alt/rdf:li",  # Title
                             namespaces=nmspdict)

        tags3 = tree.findall("rdf:RDF/rdf:Description/dc:creator/rdf:Seq/rdf:li",  # Creator
                             namespaces=nmspdict)

        gjenbruk = tree.findall("rdf:RDF/rdf:Description/xmpRights:UsageTerms/rdf:Alt/rdf:li",  # Usage terms
                                namespaces=nmspdict)

        rettigheter = tree.findall("rdf:RDF/rdf:Description/dc:rights/rdf:Alt/rdf:li",  # rights
                                   namespaces=nmspdict)

        desc = tree.findall("rdf:RDF/rdf:Description/dc:description/rdf:Alt/rdf:li",  # Description
                            namespaces=nmspdict)

        jpg_desc = tree.findall("rdf:RDF/rdf:Description",  # Description for JPGs
                                namespaces=nmspdict)

        blacklist_jpg = ['title', 'subject', 'creator', 'description']
        for val in jpg_desc:  # for JPG files
            for keys2 in list(val):
                keyRegZ = re.sub(r'{.*}', '', str(keys2.tag))
                if keyRegZ not in blacklist_jpg and keyRegZ in commons_data:
                    if keys2.text != '\n' and keys2.tag:
                        commons_data[keyRegZ] = keys2.text

        for descAttri in tree.findall('rdf:RDF/rdf:Description', namespaces=nmspdict):  # For JPG and TIF files (
            # description)
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

    def media_upload(self, metadata, commons, file_ending=".tif", user_summary=""):
        """
        media_upload
        @param metadata: All of the choosen metadata from the image.
        @type metadata: dict
        @param commons: site that is used for upload
        @type commons: pywikibot.site.APISite
        @param file_ending: Type of image file. Valid options: .tif or .jpg
        @type file_ending: str
        @param user_summary: Summary for the image upload
        @type user_summary: str
        """
        file_ending_local = file_ending.lower()
        if file_ending.lower() == 'small_jpg' or file_ending.lower() == 'big_jpg':
            file_ending_local = '.jpg'

        if metadata['Country'] and metadata['Country'].lower() == "ukjent land":
            metadata['Country'] = ''

        countryTrans = {'norge': 'Norway', 'sverige': 'Sweden', 'finland': 'Finland', 'danmark': 'Denmark', 'ukjent '
                                                                                                            'land': ''}
        try:
            dateFix = parser.parse(metadata['DateCreated']).isoformat()[0:10] if len(metadata['DateCreated']) > 4 else \
                metadata['DateCreated']
        except:
            dateFix = metadata['DateCreated']

        unknownValues = ['Country', 'State', 'City']

        for val in unknownValues:
            metadata[val] = '' if metadata[val] == '' or metadata[val].lower() == 'ukjent' else metadata[val]

        if 'Ukjent' not in metadata['creator']:
            for i, name_creator in enumerate(metadata['creator']):
                splitname = name_creator.split(',')
                if splitname and (splitname[1] + ' ' + splitname[0]).lower() == " jens holmboe":
                    metadata['creator'][i] = "{{Creator:Jens Holmboe (botanist)}}"
                else:
                    metadata['creator'][i] = '{} {}'.format(splitname[1], splitname[0])

        if len(metadata['keywords']) > 1:
            for seq in range(1, len(metadata['keywords'])):
                metadata['keywords'][seq] = metadata['keywords'][seq].lower()

        depicted_place = ', '.join(filter(None, [metadata['City'], metadata['State'], metadata['Country']]))

        url = [metadata['href']]
        summary = user_summary
        keep_filename = False
        always = True
        use_filename = '{} ({}){}'.format(metadata['title'], metadata['digitalarkivetName'], file_ending_local)
        filename_prefix = None
        verify_description = True
        ignore_warning = True
        aborts = set()
        chunk_size = 0
        recursive = False
        description_file = None
        description = '''=={{int:filedesc}}==
{{Photograph
|description        = {{nb|1= Bildet er hentet fra Arkivverket.<br/>\n'''
        description += metadata['desc'] + '}}\n'
        description += '|title              = {}\n'.format(metadata['title'])
        description += '|depicted place     = {{nb | 1 = ' + depicted_place + ' }}\n' if depicted_place else '|depicted place     = \n'
        description += '|date               = {{ISOdate|' + dateFix + '}}\n' if metadata['DateCreated'] and dateFix and \
                                                                                metadata[
                                                                                    'DateCreated'] != '' else '|date               = \n'
        description += '|institution        = {}\n'.format(metadata['CustomField17'])
        description += '|department         = {}\n'.format('{{institution:Arkivverket}}')
        description += '|accession number   = {}\n'.format(metadata['IF22a_aksesjonsnummer'])
        description += '|notes              = {{nb | 1 = ' + '{}'.format(', '.join(
            filter(None, metadata['keywords']))) + ' }}\n' if "keywords" in metadata else '|notes              = \n'
        description += '|object history     = {{nb | 1 = ' + metadata[
            'CustomField18'] + ' }}\n' if 'CustomField18' in metadata else '|object history     = '
        description += '|source             = [{0} foto.digitalarkivet.no]\n'.format(metadata['source'])

        description += '|photographer       = {{creator:unknown}}' if metadata['creator'] and 'Ukjent' in metadata[
            'creator'] else '|photographer       = ' + ', '.join(filter(None, metadata['creator']))
        description += '''
|depicted people    =
|permission         =
|other_versions     =
|wikidata           =
|camera coord       =
}}

=={{int:license-header}}==
'''
        for license_meta in metadata['rights']:
            if license_meta.lower() in self.Licenses:
                description += self.Licenses[license_meta.lower()]

        description += '[[Category:{} (Arkivverket)]]\n'.format(metadata['CustomField18']) if metadata[
                                                                                                  'CustomField18'] and \
                                                                                              metadata[
                                                                                                  'CustomField18'] != \
                                                                                              '' else '[[Category' \
                                                                                                      ':Media ' \
                                                                                                      'from the ' \
                                                                                                      'National ' \
                                                                                                      'Archives of ' \
                                                                                                      'Norway]] '
        if metadata['Country']:
            country_picker = countryTrans[metadata['Country'].lower()]
            description += '[[Category:{} in {}]]'.format(dateFix[0:4],
                                                          country_picker) if dateFix and \
                                                                             country_picker != '' else ''

        if metadata['UserDefined233'].lower() == 'ja':
            self.dont_upload.append(metadata['source'])

        if metadata['source'] in self.dont_upload:
            return 0

        page = pywikibot.Page(commons, "File:" + use_filename)
        if page.exists():
            # if page.text == description:
            print("image exist!")
            return 0  # Exists

        bot = UploadRobot(url, description=description, use_filename=use_filename,
                          keep_filename=keep_filename,
                          verify_description=verify_description, aborts=aborts,
                          chunk_size=chunk_size, ignore_warning=ignore_warning,
                          always=always, summary=summary,
                          filename_prefix=filename_prefix, target_site=commons)
        bot.run()

        # print(description)
        # print(use_filename)

    def handle_upload(self, page_list, commons, file_ending="tif", summary=""):
        """
        handle_upload
        @param page_list: 4 or less images for "self.pages"
        @type page_list: list
        @param commons: site that is used for upload
        @type commons: pywikibot.site.APISite
        @param file_ending: Size for the image. Most be in "self.Size". Default "tif".
        @type file_ending: str
        @param summary: Upload comment for each image. Allows Wikitext. Default None.
        @type summary: str
        """
        location = self._post(page_list, self.Size[file_ending])
        result = self._get(location)

        for img in result['job']['result']['files']:
            meta = self.get_metadata(img['src'], img['href'], file_ending)
            self.media_upload(meta, commons, self.File_ending[file_ending], summary)

    def upload(self, commons, file_ending="tif", summary=""):
        """
        upload
        @param commons: site that is used for upload
        @type commons: pywikibot.site.APISite
        @param file_ending: Size for the image. Most be in "self.Size". Default "tif".
        @type file_ending: str
        @param summary: Upload comment for each image. Allows Wikitext. Default None.
        @type summary: str
        """
        if self.pages and file_ending in self.File_ending:
            for num, val in enumerate(self.pages, start=1):
                if num % 4 == 0:
                    self.handle_upload(self.pages[num - 4:num], commons, file_ending, summary)
                    print("sleep 30 sec.")
                    time.sleep(30)
                elif val == self.pages[-1]:
                    self.handle_upload(self.pages[(len(self.pages) % 4) * -1::], commons, file_ending, summary)
            print("Done")
            return 0
        else:
            raise TypeError(
                f"File type is out of the scope or there is nothing to upload."
            )
