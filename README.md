# Digitalarkivet2Commons
Easily upload single and multiple files from Digitalarkivet to Commons
```
Prerequisites:
- Python 3
 - Pillow
 - beautifulsoup4
 - python-dateutil
 - requests
 - pywikibot
```

# Terms and conditions
By using this program, you consent to Digitalarkivet's terms and conditions: The CC licenses state the terms that apply to the use of the photograph. We ask that the terms of use to be respected. Photographer, license and conservation institution must in all cases be credited. (original: CC-lisensene angir hvilke vilkår som gjelder for videre bruk av fotografiet. Vi ber om at vilkårene for bruk respekteres. Fotograf, rettighetshaver og bevaringsinstitusjon skal i alle tilfeller krediteres.)

# Usage
The program only works for images under https://foto.digitalarkivet.no/fotoweb/.
```py
from d2c import Client as d2c
import pywikibot
commons = pywikibot.Site("commons","commons")

R = d2c.Client()
R.query('/fotoweb/archives/5001-Historiske-foto/?q=reinbeite*') # print(R.pages) to check what will be uploaded
R.upload(summary="I like to upload images from Digitalarkivet", size="tif", commons)
```

# Disclosure
This program was made with payment from Wikimedia Norway. Per [Wikimedia Terms of Use](https://foundation.wikimedia.org/wiki/Terms_of_Use).
