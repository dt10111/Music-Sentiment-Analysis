import MySQLdb
import ai_cover
from gpt4all import GPT4All
import re
from bs4 import BeautifulSoup
import requests
import time
from dotenv import load_dotenv

load_dotenv()

# Initialize GPT4All model
model_path = r"E:\GPT4ALL"
model_name = "mistral-7b-instruct-v0.2.Q4_0.gguf"
model = GPT4All(model_name, model_path=model_path)

dtdb = MySQLdb.Connection(
        host=os.getenv('BI_HOST'),
        user=os.getenv('BI_USER'),
        password=os.getenv('BI_PASS'),
        port=3306,
        db=os.getenv('BI_DB_NAME'),
)
curdt = dtdb.cursor()
dtdb.set_character_set('utf8mb4')
curdt.execute('SET NAMES utf8mb4;')
curdt.execute('SET CHARACTER SET utf8mb4;')
curdt.execute('SET character_set_connection=utf8mb4;')

def clean_themes(response):
   response = re.sub(r'^.*?:\s*', '', response)
   response = re.sub(r'Theme.*?,?\s*', '', response)
   response = re.sub(r'\d+\.\s*', '', response)
   response = re.sub(r',\s*,', ',', response)  # Remove double commas
   response = re.sub(r'^\s*,\s*|\s*,\s*$', '', response)  # Remove leading/trailing commas
   return response.strip()

def replace_quoted_it(text):
    return re.sub(r'"It"', 'It', text)

def gpt_lyrics(title, artist_s,lyrics):
    song = title + ' by ' + artist_s
    prompt = f"""Without referring to it's musical qualities(don't call it a song, etc), provide a list of the top ten most prominent themes of {song}. the lyrics are {lyrics}.  The response should be a single line of text formatted strictly as a comma-separated list (e.g., theme1, theme2, theme3, etc.) with no other content."""
    
    response = model.generate(prompt, max_tokens=1500)
    cleaned_response = clean_themes(response)
    return cleaned_response

def gpt_theme(title, artist_s):
    song = title + ' by ' + artist_s
    prompt = f"""Without referring to it's musical qualities(don't call it a song, etc), provide list of the top ten most prominent themes of {song}.   The response should be a single line of text formatted strictly as a comma-separated list (e.g., theme1, theme2, theme3, etc.) with no other content."""
    
    response = model.generate(prompt, max_tokens=1500)
    cleaned_response = clean_themes(response)
    return cleaned_response

def get_lyrics(artist, title):
    # Clean the title by removing everything after and including the first hyphen
    title = title.split(' - ')[0].strip()
    
    try:
        print(f'Searching for "{title}" by {artist}...')
        search_url = "https://api.genius.com/search"
        headers = {"Authorization": "Bearer 03tVg9JpiMKWx3xK4Ml9YNvs9u2YPgfKIsKrGxygFb0LljjTyLOsZaHQEzzCxTZK"}
        params = {"q": f"{title} {artist}"}
        
        # Rest of the function remains the same
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Genius API error {response.status_code}: {response.text}")
            return None
            
        data = response.json()
        hits = data.get('response', {}).get('hits', [])
        
        if not hits:
            print("No results found in Genius API.")
            return None

        found_match = False
        for hit in hits:
            result = hit.get('result', {})
            genius_artist = result.get('artist_names', '').lower()
            
            search_artist = artist.lower().replace('/', ' ')
            
            if search_artist in genius_artist or genius_artist in search_artist:
                found_match = True
                first_hit = result
                print(f"Found Song: {first_hit.get('full_title')}")
                song_url = first_hit.get('url')
                print(f"Song URL: {song_url}")
                break
        
        if not found_match:
            print(f"Could not find matching artist: {artist}")
            return None
            
        lyrics_response = requests.get(song_url)
        if lyrics_response.status_code != 200:
            print("Failed to fetch lyrics from Genius URL.")
            return None
            
        soup = BeautifulSoup(lyrics_response.text, 'html.parser')
        
        lyrics_div = soup.find("div", class_="lyrics")
        if not lyrics_div:
            lyrics_divs = soup.find_all("div", {'data-lyrics-container': 'true'})
            if lyrics_divs:
                lyrics = '\n'.join([div.get_text(separator="\n") for div in lyrics_divs])
            else:
                print("Could not find lyrics in page structure")
                return None
        else:
            lyrics = lyrics_div.get_text(separator="\n")
            
        lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
        return lyrics
        
    except Exception as e:
        print(f"Error in get_lyrics: {str(e)}")
        return None

def get_theme(artist_s, title, track_id):
    lyrics = get_lyrics(artist_s, title)
    
    if lyrics:
        # Remove section headers and clean up newlines
        lyrics = re.sub(r'\[.*?\]|\[.*?\n.*?\]', '', lyrics, flags=re.DOTALL)
        lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
        print("\n--- Lyrics ---\n")
        print(lyrics)
        song_theme = gpt_lyrics(title, artist_s, lyrics)
        print('lyrics processed successfully')
    else:
        song_theme = gpt_theme(title, artist_s)
        lyrics = None  # Ensure lyrics is None if not found
    
    song_theme = replace_quoted_it(song_theme)
    print(f'\nResponse: {song_theme}')

    sql = "UPDATE tracks SET song_themes=%s, lyrics=%s WHERE spotify_id=%s;"
    curdt.execute(sql, (song_theme, lyrics, track_id))
    dtdb.commit()

    return song_theme
def process_daily_tracks():
    sql = """
    SELECT t.spotify_id, t.name, t.artist
    FROM playlist_app.tracks t
    inner join tracks_playlists tp on t.spotify_id = tp.track_id 
    where song_themes is null
    and date(tp.created_at) = CURDATE()
    group by t.spotify_id
    order by date(tp.created_at) DESC
    """

    curdt.execute(sql)
    data = curdt.fetchall()
    print(f"\nFound {len(data)} songs to process")
    for i, row in enumerate(data, 1):
        spotify_id = row[0]
        artist_s = row[2]
        title = row[1]
        print(f"\nProcessing Song #{i} of {len(data)}: {artist_s} - {title}")
        get_theme(artist_s, title, spotify_id)
        time.sleep(3)
