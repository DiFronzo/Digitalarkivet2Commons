# Digitalarkivet2Commons
 Easily upload a single or multiple files from foto.digitalarkivet.no to Wikimedia Commons. 
```
Prerequisites:
- Python 3.5 or higher
 - Pillow
 - python-dateutil
 - requests
 - pywikibot
```
`pip3 install -r requirements.txt`

# Terms and conditions
By using this program, you consent to Digitalarkivet's terms and conditions: The CC licenses state the terms that apply to the use of the photograph. We ask that the terms of use to be respected. Photographer, license and conservation institution must in all cases be credited. (original: CC-lisensene angir hvilke vilkår som gjelder for videre bruk av fotografiet. Vi ber om at vilkårene for bruk respekteres. Fotograf, rettighetshaver og bevaringsinstitusjon skal i alle tilfeller krediteres).

Use this script on your own risk.

## User Account

The script must be run from a Wikimedia account with the `upload_by_url` user right.
On Wikimedia Commons this is limited to users with one of the `image-reviewer`,
`bot`, `gwtoolset` or `sysop` flags. [Apply for bot rights](https://commons.wikimedia.org/wiki/Commons:Bots/Requests).

# Usage
The program only works for images under https://foto.digitalarkivet.no/fotoweb/.

For usage on function upload() the following values are allowed:
* `file_ending` has to be either `tif, small_jpg or big_jpg`.
* `summary` is required to be set.

```py
from d2c import Client as d2c
import pywikibot
commons = pywikibot.Site("commons","commons")

r = d2c.Client()
r.query('/fotoweb/archives/5001-Historiske-foto/;o=+?q=reinbeite*') # print(r.pages)
                                                                # to check images that will be uploaded
r.upload(commons, file_ending="tif", summary="I like to upload images from Digitalarkivet")
```

# Disclosure
This program was made with payment from Wikimedia Norway. Per [Wikimedia Terms of Use](https://foundation.wikimedia.org/wiki/Terms_of_Use).
