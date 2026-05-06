import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("outputs")
LILYPOND_PATH = os.getenv("LILYPOND_PATH", "lilypond")
AUDIO_FORMATS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}

SECTION_ORDER = [
    "intro", "build",
    "verse 1", "verse 2", "verse 3", "verse 4", "verse 5",
    "pre-chorus", "pre chorus",
    "chorus", "hook", "refrain",
    "post-chorus", "post chorus",
    "drop", "breakdown", "interlude",
    "bridge", "rap", "verse rap", "spoken", "skit",
    "outro", "coda", "fade out",
]

GENRE_TEMPO_MAP = {
    # K-Pop & variants
    "k-pop": 128, "kpop": 128, "k pop": 128,
    "k-ballad": 70, "kballad": 70, "k-hip hop": 95, "k-trap": 140,
    # Pop
    "pop": 120, "indie pop": 115, "bedroom pop": 95, "dream pop": 95,
    "bubblegum pop": 130, "power pop": 130,
    # R&B / Soul
    "r&b": 90, "rnb": 90, "neo soul": 90, "soul": 95,
    "trap soul": 88, "motown": 110,
    # Hip-Hop
    "hip-hop": 95, "hip hop": 95, "hiphop": 95,
    "boom bap": 90, "boombap": 90,
    "grime": 140, "uk rap": 140,
    # Trap / Drill
    "trap": 140, "drill": 145, "uk drill": 145, "ny drill": 145,
    "phonk": 145, "dark trap": 142,
    # Hyperpop / Future
    "hyperpop": 160, "hyper pop": 160, "future bass": 150,
    # EDM
    "edm": 130, "dance": 128,
    "house": 128, "deep house": 122, "tech house": 130,
    "techno": 135, "trance": 138, "psytrance": 145,
    "dubstep": 140, "brostep": 142,
    "dnb": 175, "drum and bass": 175, "liquid funk": 174, "jungle": 175,
    "footwork": 160, "juke": 155, "jersey club": 165,
    "uk garage": 132, "garage": 132,
    "electro": 130, "electronica": 120,
    # Ballad / Chill
    "ballad": 72, "slow ballad": 60,
    "lo-fi": 85, "lofi": 85, "lo fi": 85, "chillhop": 85,
    "chill": 90, "chillwave": 95, "vaporwave": 90,
    "ambient": 75, "drone": 60,
    # Jazz / Blues
    "jazz": 100, "bebop": 220, "cool jazz": 90, "hard bop": 180,
    "swing": 120, "big band": 140,
    "bossa nova": 120, "samba": 110,
    "blues": 85, "12-bar blues": 85,
    "funk": 110, "new jack swing": 100,
    # Rock / Metal
    "rock": 120, "classic rock": 120, "hard rock": 130,
    "alternative": 115, "grunge": 120,
    "indie rock": 120, "math rock": 130, "post-rock": 110,
    "metal": 160, "heavy metal": 160, "thrash metal": 180,
    "melodic metal": 140, "power metal": 165,
    "prog rock": 120, "progressive rock": 120,
    "punk": 150, "hardcore": 155, "post-punk": 140,
    "new wave": 130, "shoegaze": 100,
    "ska": 170, "rockabilly": 155,
    # Folk / Country / Acoustic
    "folk": 90, "acoustic": 95, "country": 100, "bluegrass": 130,
    "singer-songwriter": 85, "celtic": 125, "irish": 130,
    # World / Latin
    "reggae": 80, "dancehall": 90, "dub": 80,
    "latin": 110, "reggaeton": 95,
    "afrobeats": 100, "afropop": 105, "afrobeat": 100,
    "flamenco": 130, "cumbia": 105,
    # Classical / Orchestral
    "classical": 80, "orchestral": 80, "baroque": 120,
    "cinematic": 90, "film score": 80,
    # Synthwave / Retro
    "synthwave": 110, "retrowave": 110, "outrun": 110,
    # Gospel / Worship
    "gospel": 90, "worship": 78, "praise": 85,
}

KEY_TO_LILYPOND = {
    "C": ("c", "\\major"), "C#": ("cis", "\\major"), "Db": ("des", "\\major"),
    "D": ("d", "\\major"), "D#": ("dis", "\\major"), "Eb": ("ees", "\\major"),
    "E": ("e", "\\major"), "F": ("f", "\\major"), "F#": ("fis", "\\major"),
    "Gb": ("ges", "\\major"), "G": ("g", "\\major"), "G#": ("gis", "\\major"),
    "Ab": ("aes", "\\major"), "A": ("a", "\\major"), "A#": ("ais", "\\major"),
    "Bb": ("bes", "\\major"), "B": ("b", "\\major"),
    "Cm": ("c", "\\minor"), "C#m": ("cis", "\\minor"), "Dbm": ("des", "\\minor"),
    "Dm": ("d", "\\minor"), "D#m": ("dis", "\\minor"), "Ebm": ("ees", "\\minor"),
    "Em": ("e", "\\minor"), "Fm": ("f", "\\minor"), "F#m": ("fis", "\\minor"),
    "Gbm": ("ges", "\\minor"), "Gm": ("g", "\\minor"), "G#m": ("gis", "\\minor"),
    "Abm": ("aes", "\\minor"), "Am": ("a", "\\minor"), "A#m": ("ais", "\\minor"),
    "Bbm": ("bes", "\\minor"), "Bm": ("b", "\\minor"),
}

CHORD_TO_LILYPOND = {
    "C": "c", "Cm": "c:m", "C7": "c:7", "Cmaj7": "c:maj7", "Cm7": "c:m7",
    "D": "d", "Dm": "d:m", "D7": "d:7", "Dmaj7": "d:maj7", "Dm7": "d:m7",
    "E": "e", "Em": "e:m", "E7": "e:7", "Emaj7": "e:maj7", "Em7": "e:m7",
    "F": "f", "Fm": "f:m", "F7": "f:7", "Fmaj7": "f:maj7", "Fm7": "f:m7",
    "G": "g", "Gm": "g:m", "G7": "g:7", "Gmaj7": "g:maj7", "Gm7": "g:m7",
    "A": "a", "Am": "a:m", "A7": "a:7", "Amaj7": "a:maj7", "Am7": "a:m7",
    "B": "b", "Bm": "b:m", "B7": "b:7", "Bmaj7": "b:maj7", "Bm7": "b:m7",
    "Bb": "bes", "Bbm": "bes:m", "Bb7": "bes:7",
    "Eb": "ees", "Ebm": "ees:m", "Eb7": "ees:7",
    "Ab": "aes", "Abm": "aes:m", "Ab7": "aes:7",
    "F#": "fis", "F#m": "fis:m", "F#7": "fis:7",
    "C#": "cis", "C#m": "cis:m", "C#7": "cis:7",
    "G#": "gis", "G#m": "gis:m", "G#7": "gis:7",
}

VISUAL_THEME_MAP = {
    "dark": "Cyberpunk Dark", "neon": "Cyberpunk Neon",
    "bright": "Vibrant Pop", "minimal": "Minimalist",
    "sad": "Emotional Cinematic", "love": "Romantic Soft",
    "lonely": "Melancholic Noir", "fire": "High Energy Dynamic",
    "rain": "Atmospheric Moody", "night": "Nocturnal Urban",
    "color": "Color-Saturated Artistic", "dream": "Dreamlike Surreal",
    "city": "Urban Cinematic", "nature": "Natural Organic",
    "future": "Futuristic Sci-Fi", "retro": "Retro Vintage",
}
