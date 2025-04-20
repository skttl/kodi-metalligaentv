import os
import sys
from urllib.parse import urlencode, parse_qsl
import urllib.request
import json
import xbmc
import xbmcgui
import xbmcplugin
from xbmcaddon import Addon
from xbmcvfs import translatePath
from datetime import datetime, timezone
import xbmcaddon
import time

# Get the plugin url in plugin:// notation.
URL = sys.argv[0]
# Get a plugin handle as an integer number.
HANDLE = int(sys.argv[1])
# Get addon base path
ADDON_PATH = translatePath(Addon().getAddonInfo('path'))
addon_id = 'plugin.video.metalligaen.tv'
addon = xbmcaddon.Addon(addon_id)

# Global token og tidspunkt for udløb
token = None
token_expiry = 0  # Tidspunkt for hvornår tokenen udløber (i epoch-tid)

def save_credentials(email, password):
    xbmc.log("Save Credentials: Email: {}, Password: {}".format(email, password), level=xbmc.LOGDEBUG)
    try:
        addon.setSetting('email', email)
        addon.setSetting('password', password)
    except Exception as e:
        xbmc.log("Failed to save credentials: {}".format(e), level=xbmc.LOGERROR)
        show_alert("Kunne ikke gemme loginoplysninger", str(e))

def get_credentials():
    email = addon.getSetting('email')
    password = addon.getSetting('password')

    xbmc.log("Credentials: Email: {}, Password: {}".format(email, password), level=xbmc.LOGDEBUG)

    if not email or not password:
        # Implementer en metode til at spørge brugeren om email og password
        email = xbmcgui.Dialog().input("Indtast din email:")
        password = xbmcgui.Dialog().input("Indtast dit password:")

        save_credentials(email, password)

    return email, password

def clear_credentials():
    xbmc.log("Clear credentials", level=xbmc.LOGDEBUG)
    addon.setSetting('email', '')
    addon.setSetting('password', '')

def save_token(token, token_expiry):
    xbmc.log("Save Token: {}, Token expiry: {}".format(token, token_expiry), level=xbmc.LOGDEBUG)
    try:
        addon.setSetting('token', token)
        addon.setSetting('token_expiry', str(token_expiry))
    except Exception as e:
        xbmc.log("Failed to save token: {}".format(e), level=xbmc.LOGERROR)
        show_alert("Kunne ikke gemme token", str(e))

def get_token():
    global token, token_expiry

    if not token or time.time() > token_expiry:
        token = addon.getSetting('token')
        token_expiry = addon.getSetting('token_expiry')
        if not token_expiry:
            token_expiry = 0

        token_expiry = float(token_expiry)

    xbmc.log("Get Token: Token: {}, Token expiry: {}".format(token, token_expiry), level=xbmc.LOGDEBUG)
        
    return token, token_expiry

def clear_token():
    xbmc.log("Clear token", level=xbmc.LOGDEBUG)
    addon.setSetting('token', '')
    addon.setSetting('token_expiry', '0')

def login_to_livearena():
    token, token_expiry = get_token()

    xbmc.log("Login: Token: {}, Token expiry: {}".format(token, token_expiry), level=xbmc.LOGDEBUG)

    # Hvis token er gyldig, returner den
    if token and time.time() < token_expiry:
        return token

    email, password = get_credentials()

    url = "https://api.livearenasports.com/user/login"
    payload = {
        "userName": email,
        "password": password
    }

    # Konverter payload til JSON
    data = json.dumps(payload).encode('utf-8')

    # Opret en request med de nødvendige headers
    headers = {
        'Content-Type': 'application/json',
        'site-id': 'COM_META'
    }
    
    req = urllib.request.Request(url, data=data, headers=headers)
    # Log hele svaret
    xbmc.log("Login Request: {}".format(req), level=xbmc.LOGDEBUG)
    xbmc.log("Login payload : {}".format(payload), level=xbmc.LOGDEBUG)

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            response_json = json.loads(response_data)

            # Log hele svaret
            xbmc.log("Login Response: {}".format(response_json), level=xbmc.LOGDEBUG)

            # Forvent at serveren returnerer en token
            token = response_json.get('jwt_token')
            if token:
                print("Login successful!")
                token_expiry = time.time() + 3600 * 24 * 365  # Antag tokenen er gyldig i 1 år

                xbmc.log("Login: Token: {}, Token expiry: {}".format(token, token_expiry), level=xbmc.LOGDEBUG)

                save_token(token, token_expiry)
                return token
            else:
                xbmc.log("Login failed: {}".format(response_json.get('message', 'No message')), level=xbmc.LOGERROR)
                print("Login failed: No token returned.")

                dialog = xbmcgui.Dialog()
                ret = dialog.yesno("Login fejlede", "", yeslabel="Prøv igen", nolabel="Annullér")
                
                if ret == 1:  # Brugeren valgte "Retry"
                    # Her kan du kalde en funktion til at spørge om loginoplysninger igen
                    clear_token()
                    clear_credentials()
                    login_to_livearena()
                else:
                    xbmc.log("User cancelled login.", level=xbmc.LOGDEBUG)

                return None

    except urllib.error.HTTPError as e:
        print(f"HTTP error occurred: {e.code} - {e.reason}")
        xbmc.log("HTTP Error during login: {}".format(str(e)), level=xbmc.LOGERROR)

        dialog = xbmcgui.Dialog()
        ret = dialog.yesno("Login fejlede", f"HTTP error occurred: {e.code} - {e.reason}", yeslabel="Prøv igen", nolabel="Annullér")
        
        if ret == 1:  # Brugeren valgte "Retry"
            # Her kan du kalde en funktion til at spørge om loginoplysninger igen
            clear_token()
            clear_credentials()
            login_to_livearena()
        else:
            xbmc.log("User cancelled login.", level=xbmc.LOGDEBUG)

        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        xbmc.log("Error during login: {}".format(str(e)), level=xbmc.LOGERROR)

        dialog = xbmcgui.Dialog()
        ret = dialog.yesno("Login fejlede", str(e), yeslabel="Prøv igen", nolabel="Annullér")
        
        if ret == 1:  # Brugeren valgte "Retry"
            # Her kan du kalde en funktion til at spørge om loginoplysninger igen
            clear_token()
            clear_credentials()
            login_to_livearena()
        else:
            xbmc.log("User cancelled login.", level=xbmc.LOGDEBUG)

        return None


def show_alert(heading, message):
    dialog = xbmcgui.Dialog()
    dialog.ok(heading, message)

def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{}?{}'.format(URL, urlencode(kwargs))


def list_options():
    """
    Create the list of movie genres in the Kodi interface.
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(HANDLE, 'Metalligaen.TV')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(HANDLE, 'sports')

    resource_path = translatePath('special://home/addons/plugin.video.metalligaen.tv/resources/')
    
    # Get movie genres
    categories = [
        {
            'title': 'Live kampe',
            'action': 'live',
            'icon': 'live.jpg',
        },
        {
            'title': 'Arkiv kampe',
            'action': 'archive',
            'icon': 'archive.jpg'
        },
        {
            'title': 'Higlights',
            'action': 'highlights',
            'icon': 'highlights.jpg',
        }
    ]
    # Iterate through genres
    for index, category in enumerate(categories):
        list_item = xbmcgui.ListItem(label=category['title'])
        list_item.setArt({'thumb': os.path.join(resource_path, category['icon']), 'icon': os.path.join(resource_path, category['icon']), 'fanart': os.path.join(resource_path, category['icon'])})
        url = get_url(action=category['action'])
        is_folder = True
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(HANDLE)

def get_highlights_feed():
    url = "https://player.videosyndicate.io/services/get/widget/41398/1036.json"
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                data = json.loads(response.read())
                return data
            else:
                print(f"Fejl ved hentning af feed: {response.status}")
                show_alert("Fejl ved hentning af feed", response.status)
                return None
    except Exception as e:
        print(f"Fejl: {e}")
        show_alert("Fejl ved hentning af feed", str(e))
        return None

def format_highlight_title(highlight):
    try:
        return f"{highlight['name']} - {highlight['publish']}"
    except Exception as e:
        print(f"Fejl ved formatering af titel: {e}")
        return ""


def list_highlights():
    feed_data = get_highlights_feed()

    if feed_data:
        xbmcplugin.setPluginCategory(HANDLE, 'Highlights')
        xbmcplugin.setContent(HANDLE, 'sports')

        for highlight in feed_data['Video']:
            # Format title
            formatted_title = format_highlight_title(highlight)
            
            # Opret et ListItem for hver video
            list_item = xbmcgui.ListItem(label=formatted_title)
            
            # Tilføj billede/thumbnail
            list_item.setArt({
                'thumb': highlight['snapshots']['sd'],
                'icon': highlight['snapshots']['sd'],
                'fanart': highlight['snapshots']['sd']  # Kan tilføjes som baggrundsbillede
            })
            
            # Tilføj metadata for videoen
            list_item.setInfo('video', {
                'title': formatted_title,
                'genre': 'Sports',
                'plot': highlight['description'],  # Beskrivelse af highlightet
                'duration': int(highlight['duration']),  # Varigheden i sekunder
                'date': highlight['publish'],  # Udgivelsesdato
                'aired': highlight['publish']  # Datoen det blev udsendt
            })
            
            # Angiv at det er et afspilleligt element
            list_item.setProperty('IsPlayable', 'true')
            
            # URL til videoen
            url = get_url(action='play', video=highlight['source']['hd'])
            is_folder = False
            
            # Tilføj highlightet til Kodi-listen
            xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
        
        # Tilføj sorteringsmetoder
        #xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        #xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        # Afslut listen
        xbmcplugin.endOfDirectory(HANDLE)

def get_livestreams(archive=True):
    global token
    login_to_livearena()

    xbmc.log("List streams: Archive: {}".format(archive), level=xbmc.LOGDEBUG)

    # Generer den nuværende tid i ISO 8601-format
    current_time = datetime.utcnow().isoformat() + "Z"  # Tilføj 'Z' for UTC

    # Vælg de relevante parametre baseret på archive
    if archive:
        start_parameter = f"start-to={urllib.parse.quote(current_time)}"
        include_live = "false"
        sort_order = "Descending"
    else:
        start_parameter = f"start-from={urllib.parse.quote(current_time)}"
        include_live = "true"
        sort_order = "Ascending"

    # Byg URL'en
    url = f"https://api.livearenasports.com/broadcast/?page-index=0&page-size=24&{start_parameter}&include-live={include_live}&sort-column=start&sort-order={sort_order}"

    # Opret headers med authorization token
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'site-id': 'COM_META',
        'authorization': f'Bearer {token}'
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            livestreams = json.loads(response_data)

            # Returner livestreams
            return livestreams
    except urllib.error.HTTPError as e:
        print(f"HTTP error occurred: {e.code} - {e.reason}")
        xbmc.log(f"HTTP error occurred: {e.code} - {e.reason}", level=xbmc.LOGERROR)
        show_alert("HTTP fejl", f"HTTP error occurred: {e.code} - {e.reason}")
        
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        xbmc.log(f"An error occurred: {e}", level=xbmc.LOGERROR)
        show_alert("An error occurred", str(e))

        return None

def set_listitem_images(list_item, home_team_short, away_team_short):
    try:
        # Definer stien til billedmappen
        resource_path = translatePath('special://home/addons/plugin.video.metalligaen.tv/resources/')
        
        # Definer de forskellige mulige kombinationer af billednavne
        possible_images = [
            f"{home_team_short}_{away_team_short}.jpg",
            f"{away_team_short}_{home_team_short}.jpg",
            f"{home_team_short}.jpg",
            f"{away_team_short}.jpg"
        ]

        # Prøv at finde det første eksisterende billede
        image_path = None
        for img in possible_images:
            potential_path = os.path.join(resource_path, img)
            if os.path.exists(potential_path):
                image_path = potential_path
                break

        # Hvis vi fandt et billede, sæt det som thumbnail for list_item
        if image_path:
            list_item.setArt({'thumb': image_path, 'icon': image_path, 'fanart': image_path})

    except Exception as e:
        xbmc.log(f"An error occurred {sys.exc_info()[2].tb_lineno}: {e}", level=xbmc.LOGERROR)

def list_streams(archive=True):

    if archive:
        xbmcplugin.setPluginCategory(HANDLE, 'Arkiv')
    else:
        xbmcplugin.setPluginCategory(HANDLE, 'Live')

    xbmcplugin.setContent(HANDLE, 'sports')

    livestreams_data = get_livestreams(archive)

    if livestreams_data:

        for stream in livestreams_data:
            try:
                start_broadcast = datetime.fromisoformat(stream['startBroadcast'])

                start_time = start_broadcast.strftime('%d/%m %H:%M')
                
                title = f"{stream['homeTeam']['teamName']}-{stream['awayTeam']['teamName']} {start_broadcast.strftime('%Y-%m-%d')}"
                description = f"{stream['competition']['name']} - {stream['homeTeam']['teamName']} - {stream['awayTeam']['teamName']}. Sendes {start_broadcast.strftime('%d/%m kl. %H:%M')}"

                # Opret list item
                list_item = xbmcgui.ListItem(label=f"{title}")

                # Tilføj metadata for videoen
                list_item.setInfo('video', {
                    'title': title,
                    'genre': 'Sports',
                    'plot': description,  # Beskrivelse af highlightet
                })

                set_listitem_images(list_item, stream['homeTeam']['shortName'], stream['awayTeam']['shortName'])

                if start_broadcast > datetime.now(timezone.utc):
                    list_item.setProperty('IsPlayable', 'false')
                else:
                    list_item.setProperty('IsPlayable', 'true')

                url = get_url(action='playstream', video=stream['id'])  # Tilpas URL-genereringen efter behov
                is_folder = False
                
                xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)

            except Exception as e:
                print(f"An error occurred: {e}")
                xbmc.log(f"An error occurred in line {sys.exc_info()[2].tb_lineno}: {e}", level=xbmc.LOGERROR)
                show_alert("An error occurred", str(e))


    # Tilføj sorteringsmetoder for de virtuelle mappeelementer
    #xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    #xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    # Afslut oprettelsen af en virtuel mappe
    xbmcplugin.endOfDirectory(HANDLE)

def get_livestream(videoId):
    global token
    login_to_livearena()

    url = f"https://api.livearenasports.com/broadcast/video/{videoId}?video-format=HLS"

    # Opret headers med authorization token
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'site-id': 'COM_META',
        'authorization': f'Bearer {token}'
    }

    xbmc.log("Livestream: URL: {}".format(url), level=xbmc.LOGDEBUG)
    xbmc.log("Livestream: Headers: {}".format(headers), level=xbmc.LOGDEBUG)

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            livestreams = json.loads(response_data)

            xbmc.log("Livestream found: {}".format(livestreams), level=xbmc.LOGDEBUG)

            # tjek om livestreams indeholder en videoUrl
            if 'videoUrl' not in livestreams:
                print("Livestream not found.")
                show_alert("Livestream not found", "")
                return None

            # Returner livestreams
            return livestreams
    except urllib.error.HTTPError as e:
        print(f"HTTP error occurred: {e.code} - {e.reason}")
        show_alert("HTTP fejl", f"HTTP error occurred: {e.code} - {e.reason}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        show_alert("An error occurred", str(e))
        return None


def play_stream(videoId):
    stream = get_livestream(videoId)

    if stream:
        xbmc.log("Stream found: {}".format(stream), level=xbmc.LOGDEBUG)
        stream_url = stream['videoUrl']
        play_video(stream_url)

    else:
        print("No livestream found.")
        show_alert("No livestream found", "")

    return



def play_video(path):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    # offscreen=True means that the list item is not meant for displaying,
    # only to pass info to the Kodi player
    play_item = xbmcgui.ListItem(offscreen=True)
    play_item.setPath(path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if not params:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_options()
    elif params['action'] == 'highlights':
        list_highlights()
    elif params['action'] == 'live':
        list_streams(False)
    elif params['action'] == 'archive':
        list_streams(True)
    elif params['action'] == 'playstream':
        play_stream(params['video'])
    elif params['action'] == 'play':
        # Play a video from a provided URL.
        play_video(params['video'])
    else:
        # If the provided paramstring does not contain a supported action
        # we raise an exception. This helps to catch coding errors,
        # e.g. typos in action names.
        show_alert("Invalid paramstring", f"Invalid paramstring: {paramstring}")
        raise ValueError(f'Invalid paramstring: {paramstring}!')



if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])