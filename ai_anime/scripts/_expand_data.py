"""
Comprehensive music recognition data expansion.
Expands genres.json, emotions.json, atmosphere_rules.json, color_palette.json
with Suno tag list, Wikipedia genre taxonomy, and Korean music vocabulary.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
GENRES_PATH    = ROOT / "configs" / "genres.json"
EMOTIONS_PATH  = ROOT / "configs" / "emotions.json"
ATMOSPHERE_PATH= ROOT / "configs" / "atmosphere_rules.json"
COLOR_PATH     = ROOT / "configs" / "color_palette.json"

# ─────────────────────────────────────────────────────────────────────────────
# 1. GENRE KEYWORD EXPANSIONS
# ─────────────────────────────────────────────────────────────────────────────
GENRE_EXPANSIONS = {

    "late-night jazz anime noir": [
        # Jazz subgenres (Wikipedia + JazzFuel)
        "acid jazz","afro-cuban jazz","avant-garde jazz","bebop","big band",
        "cool jazz","crossover jazz","dixieland","electro swing","free jazz",
        "gypsy jazz","hard bop","jazz blues","jazz-funk","jazz fusion",
        "jazz poetry","jazz pop","jazz rap","jazz rock","jump blues",
        "kansas city jazz","latin jazz","mainstream jazz","modal jazz",
        "neo-bop","neo-swing","nu jazz","orchestral jazz","post-bop",
        "smooth jazz","soul jazz","spiritual jazz","stride jazz","swing",
        "trad jazz","west coast jazz","crime jazz","spy jazz","sweet jazz",
        "new orleans jazz","bossa nova","contemporary jazz","jazztronica",
        "vocal jazz","piano jazz","guitar jazz","progressive jazz",
        "organ trio","free funk","chamber jazz","cape jazz","ethio-jazz",
        # Jazz instruments/production
        "saxophone","tenor sax","alto sax","soprano sax","baritone sax",
        "upright bass","double bass","walking bass","brushed drums",
        "ride cymbal","vibraphone","hammond organ","muted trumpet",
        "brushed snare","jazz waltz","bebop phrasing","scat singing",
        "jazz piano","jazz guitar","improvisation","improvisational",
        "syncopated","swing feel","latin feel","rubato","trading fours",
        # Blues subgenres
        "delta blues","chicago blues","texas blues","blues rock",
        "piedmont blues","classic blues","soul-blues","country blues",
        "swamp blues","electric blues","acoustic blues","urban blues",
        "west coast blues","memphis blues","boogie woogie",
        "rhythm and blues","jump blues","british blues","bayou blues",
        # Blues instruments/production
        "slide guitar","bottleneck slide","harmonica","blues harp",
        "resonator guitar","12-bar blues","overdriven guitar",
        "dobro","raw","gritty","dirty","swampy","twangy",
        # Mood/atmosphere
        "smoky","late-night","cool","hot","swinging","bluesy",
        "laid-back","sophisticated","nostalgic","loungy","noir jazz",
        "candlelit","after hours","blue note","jazz club","lounge",
        "cocktail hour","intimate bar","smoky atmosphere","urban jazz",
        "night jazz","late night vibes","supper club","speakeasy",
        # Korean
        "재즈","재즈바","재즈카페","새벽감성","늦은밤","밤감성",
        "블루스","소울","재즈발라드","재즈풍",
    ],

    "orchestral cinematic anime": [
        # Classical periods
        "baroque","classical period","romantic","late romantic",
        "impressionism","modernism","neoclassicism","post-romanticism",
        "minimalism","spectralism","contemporary classical","post-classical",
        "indie classical","new complexity","electroacoustic",
        # Film/game score styles
        "film score","game score","anime ost","ost","score",
        "movie soundtrack","game soundtrack","anime soundtrack",
        "trailer music","promo music","adventure score","spy music",
        "horror score","romantic score","action score","sci-fi score",
        "fantasy score","war score","period drama score","thriller score",
        "animation score","suspense score","heroic theme","villain theme",
        "love theme","spaghetti western","epic orchestral",
        # Mood descriptors
        "epic","grand","heroic","majestic","sweeping","dramatic",
        "stirring","triumphant","soaring","grandiose","bombastic",
        "intimate classical","contemplative","elegant","tragic","ominous",
        "mysterious classical","ethereal","transcendent","heavenly",
        "pastoral","bucolic","playful classical","magical","dark orchestral",
        "brooding","somber","elegiac","mournful","haunting classical",
        "exhilarating","breathtaking","moving","heavenly choir",
        # Neoclassical/post-classical
        "neoclassical","modern classical","minimalist piano",
        "piano and strings","chamber music","string quartet",
        "string trio","piano trio","solo violin","solo cello",
        "solo piano","prepared piano","harp and strings","strings with synth",
        "hybrid orchestral","hybrid score","hybrid orchestral-electronic",
        # Instruments
        "full orchestra","chamber orchestra","string orchestra",
        "brass ensemble","woodwind quintet","choir","choral",
        "vocal ensemble","boys choir","strings section","brass section",
        "woodwinds","timpani","harp","cello solo","grand piano",
        "violins","violas","cellos","double bass section",
        "trumpet section","french horn","trombone","tuba",
        "oboe","clarinet","bassoon","flute section","piccolo",
        # Production
        "pizzicato strings","tremolo strings","harmonics","col legno",
        "brass fanfare","horn call","con sordino","sforzando",
        "symphonic","symphony orchestra","full orchestra","concerto",
        "symphonic metal","orchestral pop","cinematic pop","epic pop",
        # Korean
        "웅장한","웅장","장엄","교향곡","오케스트라","클래식",
        "영화음악","게임음악","드라마ost","애니메이션ost",
    ],

    "vivid urban latin anime": [
        # Latin American subgenres
        "latin pop","latin trap","latin hip-hop","latin r&b","latin rock",
        "latin freestyle","salsa romantica","salsa dura","son cubano",
        "mambo","cha-cha-cha","danzon","bolero","guaracha","timba",
        "songo","son montuno","guajira","nueva trova","trova",
        "bossa nova","samba","forro","baiao","axe","pagode","sertanejo",
        "merengue","merengue tipico","pambiche","norteño","ranchera",
        "corrido","banda","mariachi","grupero","tejano","cumbia villera",
        "vallenato","champeta","mapale","porro","tango","milonga",
        "cueca","bomba","plena","jibarom","bachata pop","salsa choke",
        "gaita","joropo","pasillo","latin house","latin electronic",
        # Caribbean subgenres
        "reggae","roots reggae","dancehall","lovers rock","dub reggae",
        "ska","rocksteady","ragga","mento","calypso","soca","zouk",
        "kompa","compas","moombahton","guaracha edm",
        # Production/rhythm terms
        "dembow","dembow rhythm","clave","tresillo","son clave",
        "rumba clave","guaguanco","reggaeton beat","808 bass latin",
        "digital latin production","melodic hooks","catchy spanish",
        # Instruments
        "nylon guitar","nylon-string guitar","conga","bongos","timbales",
        "guiro","maracas","cowbell","claves","tres guitar","cuatro",
        "bandoneon","accordion","steel drum","steelpan","charanga flute",
        "bass tumbao","piano montuno","brass section",
        # Mood/atmosphere
        "vibrant","infectious","sensual rhythm","passionate latin",
        "romantic latin","energetic latin","latin club","tropical vibes",
        "caribbean vibes","street latin","afrolatino","afrobeat",
        "afropop","amapiano","urban reggaeton","reggaeton trap",
        # Korean
        "라틴","라틴팝","라틴음악","남미","카리브","레게","살사","쿠바",
    ],

    "wide-open road anime noir": [
        # Country subgenres (Wikipedia complete)
        "alt-country","americana","cosmic country","cowpunk","gothic country",
        "roots rock","bluegrass","progressive bluegrass","traditional bluegrass",
        "blue yodeling","bro-country","cajun","bush band","bakersfield sound",
        "canadian country","christian country","classic country","country blues",
        "country folk","country pop","country rap","country rock","cowboy pop",
        "honky tonk","lubbock sound","nashville sound","countrypolitan",
        "neotraditional country","old-time","outlaw country","rockabilly",
        "psychobilly","singing cowboy","tejano","western swing","zydeco",
        "heartland rock","swamp rock","appalachian music","newgrass",
        "acoustic country","alt country indie","gothic western",
        "red dirt","texas country","southern rock","southern soul",
        # Folk subgenres
        "folk","indie folk","acoustic folk","singer-songwriter",
        "american folk revival","anti-folk","appalachian folk",
        "folk rock","folk metal","folk punk","folk pop","freak folk",
        "free folk","dark folk","neofolk","chamber folk","psychedelic folk",
        "progressive folk","protest folk","contemporary folk",
        "irish folk","scottish folk","celtic folk","british folk",
        "nordic folk","scandinavian folk","german folk","appalachian",
        "medieval folk","folktronica",
        # Instruments
        "fiddle","banjo","mandolin","harmonica","pedal steel guitar",
        "lap steel","resonator","dulcimer","autoharp","hammer dulcimer",
        "washboard","jaw harp","open tuning","fingerpicking","flatpicking",
        "acoustic guitar folk","dobro","upright bass",
        # Thematic keywords
        "road trip","open road","highway","freedom","wanderlust",
        "adventure","journey","travel","nomadic","wandering","drifting",
        "desert road","mountain road","countryside","heartland",
        "homecoming","homesick","rugged terrain","twangy","rustic",
        "organic acoustic","earthy","campfire","stargazing","wilderness",
        "wide open spaces","cross-country","open horizon",
        "storytelling","narrative","working-class","blue-collar",
        "rebellious","outlaw","heartbreak song","drinking song",
        # Korean
        "여행","로드트립","방랑","자유","떠남","길 위",
        "어쿠스틱포크","포크","컨트리",
    ],

    "pastel cyber anime pop": [
        # Indie pop subgenres
        "indie pop","bedroom pop","lo-fi pop","dream pop","chillwave",
        "hypnagogic pop","twee pop","indie electronic","lo-fi indie",
        "chill indie","soft indie","diy pop","confessional pop",
        "intimate pop","home recording","shoegaze","slowcore","sadcore",
        "ambient pop","cloud pop","cottagecore pop","fairy pop",
        "noise pop","sophisti-pop","chamber pop","baroque pop",
        "power pop","sunshine pop","art pop","psychedelic pop",
        "neo-psychedelia","indietronica","folktronica","space pop",
        "ethereal wave","dark pop","gloom pop","grunge pop","emo pop",
        "alternative pop","vapor pop","gauze pop","shimmer pop",
        "bow pop","candy pop","bubble pop","surf pop","beach pop",
        "jangle pop","gym pop","wonky pop","mall pop",
        # Production keywords
        "home recording","DIY production","bedroom recording",
        "lo-fi aesthetic","tape saturation","room reverb","intimate sound",
        "warm reverb","hazy","dreamy","fuzzy","washed-out","detuned",
        "layered vocals","whisper vocals","hushed delivery","airy vocals",
        "jangly guitar","clean guitar","delayed guitar","chorus-drenched",
        "simple drum machine","programmed drums","soft percussion",
        "vintage synthesizer","warm synth pad","moog bass","casio keyboard",
        "lo-fi piano","electric piano","mellotron","toy instruments",
        "vinyl crackle","tape hiss","analog warmth","bit-crushed",
        "pitch-slowed","warped sample",
        # Dream pop/shoegaze keywords
        "wall of sound","heavy reverb","swirling guitars","distorted layers",
        "feedback","tremolo","phaser","chorus pedal",
        "ethereal vocals","breathy vocals","unintelligible lyrics",
        "dense production","cavernous reverb","drowning in reverb",
        "psychedelic textures","surreal","weightless","floating",
        # J-pop/city pop connection
        "city pop","shibuya-kei","j-indie","japanese indie pop",
        "kawaii","kawaii pop","cute pop","pastel aesthetic","soft aesthetic",
        # Mood keywords
        "nostalgic","bittersweet","introspective","confessional","earnest",
        "vulnerable","authentic","coming-of-age","youthful","tender",
        "gentle","delicate","fragile","quirky","whimsical","offbeat",
        # Korean
        "인디팝","베드룸팝","감성팝","인디","인디음악","드림팝",
        "슈게이징","로파이팝","감성인디",
    ],

    "vivid idol anime pop": [
        # K-pop subgenres
        "k-pop","kpop","k-pop ballad","k-pop boy group","k-pop girl group",
        "k-pop hip-hop","k-pop dance pop","k-pop r&b","k-pop trap",
        "k-pop edm","k-pop future bass","k-pop synth pop","k-drama ost",
        "k-indie","korean pop","korean indie","korean r&b","korean hip-hop",
        "korean ballad","감성발라드","korean idol",
        # J-pop subgenres
        "j-pop","jpop","japanese pop","j-rock","j-indie",
        "anison","anime song","denpa song","enka","kayokyoku",
        "visual kei","kawaii metal","j-pop ballad","j-idol","akiba-kei",
        # Idol concepts
        "idol concept","girl crush concept","cute concept","bubbly concept",
        "teen crush","innocent concept","mature concept","school concept",
        "urban concept","fantasy concept","retro concept","vintage concept",
        "futuristic concept","hip-hop concept","street concept",
        "glamorous concept","storytelling concept","cinematic mv concept",
        "dark concept","bright concept","narrative concept",
        # Performance/production keywords
        "synchronized dance","choreography","formation change","point choreo",
        "comeback","debut","kpop style","jpop style","idol performance",
        "girlband","boyband","girl group","boy group","co-ed group",
        "sub-unit","world tour single","title track","b-side",
        "high-quality production","polished production","intricate arrangement",
        "layered harmonies","auto-tune","pitch correction",
        "melodic hook","catchy chorus","earworm melody","pre-chorus build",
        "bridge breakdown","rap verse","bilingual lyrics","produced beat",
        "future bass drop","edm drop","synth lead","808 bass drop",
        "bubblegum pop","dance pop","electropop","bright synth-pop",
        "idol dance","idol vocal","idol rap","tight harmony",
        # Asian pop broader
        "c-pop","mandopop","cantopop","taiwanese pop","thai pop",
        "vietnamese pop","indonesian pop","pinoy pop","p-pop",
        "fandom","fan chant","fandom name","lightstick","fan service",
        "photocard","teaser image","mv shoot","training system",
        # Korean keywords
        "아이돌","케이팝","제이팝","걸그룹","보이그룹",
        "아이돌팝","아이돌음악","컴백","데뷔","퍼포먼스",
        "댄스팝","팝","댄스","아이돌발라드",
        # Mood
        "youthful energy","vibrant pop","glamorous","polished","celebratory",
        "triumphant pop","confident","charismatic","empowering","inspiring",
        "infectious positivity","high-energy fun","party vibes",
    ],

    "quiet ambient anime drift": [
        # Ambient subgenres (Wikipedia)
        "dark ambient","ambient dub","ambient industrial","dungeon synth",
        "isolationism","dreampunk","illbient","new-age","neoclassical new-age",
        "space music","psybient","psydub","drone","drone ambient",
        "Berlin School","kosmische musik","ambient techno","ambient house",
        "ambient trance","space ambient","aquatic ambient","nature ambient",
        "binaural beats","healing frequencies","432hz","528hz",
        "lo-fi ambient","ambient jazz","ambient pop","glitch ambient",
        "post-rock ambient","shoegaze ambient","ambient electronic",
        # Lo-fi subgenres
        "lo-fi hip hop","lo-fi hip-hop","lofi","chill beats","study beats",
        "lofi beats","boom bap lo-fi","jazz lo-fi","soul lo-fi",
        "rainy day lo-fi","late night lo-fi","chillhop","chillstep",
        "chillwave","vaporwave","slushwave","future funk",
        # Electronic ambient-adjacent
        "idm","algorave","drill and bass","microsound","lowercase",
        "reductionism","glitch","glitch hop","witch house","wave",
        "dark wave","ethereal wave","cold wave",
        "phonk","drift phonk","slowed plus reverb","nightcore",
        # Production/sound design
        "analog synthesis","granular synthesis","wavetable synthesis",
        "modular synth","synthesizer","ambient pad","sustained tones",
        "drones","evolving soundscapes","layered textures","field recordings",
        "nature sounds","rain sounds","white noise","brown noise","pink noise",
        "binaural","reverb-heavy","echo-heavy","spacious production",
        "sparse arrangement","minimalist composition","repetitive patterns",
        "emotional tension","textural focus","shifting sounds","filters",
        # Instruments
        "piano ambient","guitar ambient","strings ambient",
        "electric piano","rhodes","mellotron","vibraphone",
        "bells","chimes","wind sounds","water sounds",
        "harp ambient","flute ambient","sine waves","pad synth",
        # Mood/use case
        "meditation","yoga","sleep music","study music","focus music",
        "background music","relaxing","spa music","healing music",
        "mindfulness","breathing","floating","drifting","immersive",
        "trance-like","hypnotic","timeless","enveloping","peaceful",
        "serene","solitary","introspective","contemplative",
        # Korean
        "힐링","명상","자연","공부","로파이","집중","수면",
        "공부할때","힐링음악","명상음악","자연의소리","잔잔한",
        "뉴에이지","앰비언트","이완","치유","수면음악",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. EMOTION ALIASES — Korean + extended English
# ─────────────────────────────────────────────────────────────────────────────
EMOTION_ALIASES_TO_ADD = {
    # 슬픔/외로움
    "쓸쓸":"lonely","쓸쓸한":"lonely","쓸쓸함":"lonely",
    "외로움":"lonely","외로운":"lonely","고독한":"lonely","고독":"lonely",
    "적막":"lonely","적막한":"lonely",
    "슬픔":"sad","슬픈":"sad","슬퍼":"sad",
    "우울":"sad","우울한":"sad","우울함":"sad",
    "서글픔":"sad","서글픈":"sad",
    "처연":"sad","처연한":"sad",
    "눈물":"sad","눈물나는":"sad",
    # 그리움/향수
    "그리움":"nostalgic","그리운":"nostalgic","그리워":"nostalgic",
    "노스탤지어":"nostalgic","향수":"nostalgic","추억":"nostalgic",
    "아련":"nostalgic","아련한":"nostalgic","빛바랜":"nostalgic",
    "향수적인":"nostalgic","센치한":"nostalgic","센치":"nostalgic",
    # 몽환/꿈
    "몽환":"dreamy","몽환적":"dreamy","몽환감":"dreamy",
    "꿈같은":"dreamy","환상적":"dreamy","신비로운":"dreamy",
    "신비":"dreamy",
    # 설렘/희망/기대
    "설렘":"hopeful","설레는":"hopeful","설레임":"hopeful","설레":"hopeful",
    "기대":"hopeful","희망":"hopeful","희망적":"hopeful",
    "두근":"romantic","두근두근":"romantic","두근거리는":"romantic",
    # 행복/신남
    "행복":"excited","행복한":"excited","행복감":"excited",
    "기쁨":"excited","기쁜":"excited",
    "신나":"excited","신나는":"excited","신남":"excited",
    "활기찬":"excited","활기":"excited","역동적":"excited",
    # 로맨틱
    "로맨틱":"romantic","낭만":"romantic","낭만적":"romantic",
    "사랑":"romantic","사랑스러운":"romantic",
    # 평온/힐링
    "평온":"peaceful","평온한":"peaceful","평화":"peaceful",
    "차분":"peaceful","차분한":"peaceful",
    "고요":"peaceful","고요한":"peaceful",
    "힐링":"peaceful","위로":"peaceful",
    "잔잔한":"peaceful","잔잔":"peaceful",
    "포근한":"peaceful","포근":"peaceful","따뜻한":"peaceful",
    # 긴장/불안
    "불안":"anxious","불안한":"anxious","불안감":"anxious",
    "긴장":"tense","긴장감":"tense","긴장된":"tense",
    # 분노/저항
    "분노":"angry","분노한":"angry","화남":"angry","화":"angry",
    "저항":"defiant","반항":"defiant","반항적":"defiant",
    # 쓴맛/감동
    "뭉클":"bittersweet","뭉클한":"bittersweet","뭉클함":"bittersweet",
    "감동":"bittersweet","감동적":"bittersweet","감동받은":"bittersweet",
    "간절":"longing","간절한":"longing","간절함":"longing",
    "애잔":"bittersweet","애잔한":"bittersweet",
    # 청량
    "청량":"hopeful","청량한":"hopeful","상큼":"hopeful","상큼한":"hopeful",
    "산뜻한":"hopeful","개운한":"hopeful",
    # 한국 특유 감정
    "한":"sad","서정적":"nostalgic","서정":"nostalgic",
    "애틋":"longing","애틋한":"longing",
    # 영어 추가 별칭
    "wistful":"nostalgic","forlorn":"lonely","desolate":"lonely",
    "yearning":"longing","aching":"longing","pining":"longing",
    "tender":"romantic","warm":"peaceful","serene":"peaceful",
    "tranquil":"peaceful","cozy":"peaceful","soothing":"peaceful",
    "intense":"tense","suspenseful":"tense","uneasy":"anxious",
    "eerie":"tense","haunting":"lonely","foreboding":"tense",
    "bitter":"bittersweet","poignant":"bittersweet","moving":"bittersweet",
    "triumphant":"excited","euphoric":"excited","uplifting":"hopeful",
    "gloomy":"sad","sorrowful":"sad","mournful":"sad","desolate":"sad",
    "enchanting":"dreamy","surreal":"dreamy","hypnotic":"dreamy",
    "tense":"tense","nervous":"anxious","restless":"anxious",
    "passionate":"romantic","intimate":"romantic","sensual":"romantic",
    "playful":"excited","joyful":"excited","celebratory":"excited",
    "inspiring":"hopeful","motivational":"hopeful","empowering":"hopeful",
    "contemplative":"peaceful","meditative":"peaceful","reflective":"peaceful",
    "dark":"sad","brooding":"sad","somber":"sad","heavy":"sad",
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. ATMOSPHERE — 계절 + 도시 키워드 확장
# ─────────────────────────────────────────────────────────────────────────────
SEASON_RULES_TO_ADD = [
    {"keys": ["봄","벚꽃","cherry blossom","spring morning","봄비","spring breeze","새싹"],
     "season": "spring awakening"},
    {"keys": ["여름","summer night","열대","humid","무더운","해변","beach summer","tropical summer"],
     "season": "summer nostalgia"},
    {"keys": ["가을","autumn","단풍","fall leaves","harvest","낙엽","가을비"],
     "season": "autumn melancholy"},
    {"keys": ["겨울","눈보라","눈","frost","snowfall","icy","frozen","겨울밤","blizzard"],
     "season": "winter stillness"},
    {"keys": ["비","rainy","빗소리","drizzle","thunder rain","폭우","장마","rain on glass"],
     "season": "rainy late spring night"},
    {"keys": ["새벽","dawn","early morning","sunrise","새벽 3시","3am","blue hour","pre-dawn"],
     "season": "pre-dawn blue hour"},
    {"keys": ["밤하늘","starry night","별빛","moonlight","달빛","야경","midnight sky"],
     "season": "midnight starry stillness"},
    {"keys": ["황혼","dusk","sunset","노을","golden hour","저녁놀","twilight"],
     "season": "twilight golden hour"},
]

URBAN_KEYWORDS_TO_ADD = [
    # 한국어 도시 키워드
    "도시","도시감성","야경","빌딩","지하철","역","버스","골목","한강","홍대","강남","신촌",
    "편의점","카페","재즈바","클럽","거리","도심","빌딩숲","아파트","옥상",
    # 영어 도시 키워드
    "downtown","metropolitan","city lights","night city","urban landscape",
    "apartment","high-rise","boulevard","alley","overpass","underpass",
    "convenience store","coffee shop","bar","club","parking garage",
    "han river","neon signs","traffic lights","crosswalk",
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. COLOR PALETTE — 장르별 색상 매핑 추가
# ─────────────────────────────────────────────────────────────────────────────
COLOR_RULES_TO_ADD = [
    # 재즈/블루스/소울 → amber gold (따뜻한 조명)
    {"keys": ["jazz","saxophone","bebop","blues","bluesy","soul","swing",
              "smoothjazz","재즈","재즈바","블루스","소울","스윙",
              "bourbon","smoky bar","candlelit"],
     "color": "amber gold"},
    # 라틴/카리브 → coral orange (열정적/열대)
    {"keys": ["latin","reggaeton","tropical","salsa","cumbia","bachata",
              "bossa nova","samba","merengue","mambo","soca","calypso",
              "라틴","라틴팝","남미","카리브","살사","레게톤","보사노바"],
     "color": "coral orange"},
    # 오케스트라/클래식/서사 → cold silver (웅장/서사)
    {"keys": ["orchestral","symphonic","epic","majestic","heroic","choir",
              "choral","classical","neoclassical","cinematic score","film score",
              "오케스트라","교향곡","웅장","장엄","클래식","합창"],
     "color": "cold silver"},
    # 아이돌/케이팝/제이팝 → soft violet (밝고 신비로운)
    {"keys": ["idol","k-pop","kpop","girl group","boy group","girlband","boyband",
              "아이돌","케이팝","걸그룹","보이그룹","아이돌팝"],
     "color": "soft violet"},
    # 인디팝/드림팝/베드룸팝 → soft violet
    {"keys": ["bedroom pop","indie pop","dream pop","chillwave","shoegaze",
              "twee pop","lo-fi pop","cloud pop","베드룸팝","인디팝","드림팝"],
     "color": "soft violet"},
    # 컨트리/포크/아메리카나 → amber gold (따뜻한 대지)
    {"keys": ["country","folk","americana","bluegrass","fiddle","harmonica",
              "alt-country","outlaw country","singer-songwriter","roots music",
              "컨트리","포크","어쿠스틱포크","여행","로드트립","방랑"],
     "color": "amber gold"},
    # 로맨틱/러브송 → rose gold
    {"keys": ["romantic","love song","tender","sensual","사랑","두근","로맨틱",
              "낭만","발라드","love","한국발라드","팝발라드","r&b ballad"],
     "color": "rose gold"},
    # 힐링/명상/자연/앰비언트 → jade green
    {"keys": ["healing","peaceful","meditation","ambient","nature","forest",
              "calm","spa","yoga","힐링","명상","자연","뉴에이지","잔잔한",
              "lo-fi ambient","new-age","psybient","space music"],
     "color": "jade green"},
    # 청량/밝음/팝/신나는 → electric blue
    {"keys": ["fresh","bright pop","happy","bubblegum","dance pop","electropop",
              "청량","설레","신나","경쾌","활기","청량한","상큼","개운"],
     "color": "electric blue"},
    # 새벽/밤/노스탤지어 감성 → neon magenta
    {"keys": ["새벽감성","late night","야간","after hours","night vibes",
              "새벽","퇴근길감성","밤감성","nocturnal","midnight lounge"],
     "color": "neon magenta"},
    # 록/메탈 → crimson red
    {"keys": ["metal","death metal","heavy metal","thrash","punk rock",
              "metalcore","post-hardcore","progressive metal","doom metal",
              "메탈","헤비메탈","하드록","펑크록"],
     "color": "crimson red"},
    # 전자음악/EDM/하우스/테크노 → electric blue
    {"keys": ["edm","house","techno","trance","electro","rave","club music",
              "synthwave","retrowave","electronic dance","하우스","테크노",
              "트랜스","전자음악","이디엠"],
     "color": "electric blue"},
    # 트로피칼/레게 → coral orange
    {"keys": ["reggae","dancehall","dub","ska","tropical house","moombahton",
              "레게","댄스홀","덥","열대","스카"],
     "color": "coral orange"},
]

# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────
def run():
    # ── genres.json ──────────────────────────────────────────────────────────
    with open(GENRES_PATH, encoding="utf-8") as f:
        genres = json.load(f)

    total_added = 0
    for genre in genres:
        name = genre.get("name", "")
        if name in GENRE_EXPANSIONS:
            existing = set(k.lower() for k in genre.get("keys", []))
            new_keys = [k for k in GENRE_EXPANSIONS[name]
                        if k.lower() not in existing]
            genre["keys"].extend(new_keys)
            total_added += len(new_keys)
            print(f"[genres] {name[:40]:40s}: +{len(new_keys):3d} -> 총 {len(genre['keys'])}개")

    with open(GENRES_PATH, "w", encoding="utf-8") as f:
        json.dump(genres, f, ensure_ascii=False, indent=2)
    print(f"\ngenres.json: 총 {total_added}개 키워드 추가 완료\n")

    # ── emotions.json ─────────────────────────────────────────────────────────
    with open(EMOTIONS_PATH, encoding="utf-8") as f:
        emotions = json.load(f)

    aliases = emotions.setdefault("aliases", {})
    emotion_keys = set(emotions.get("emotions", {}).keys())
    added_aliases = 0
    for alias, target in EMOTION_ALIASES_TO_ADD.items():
        if alias not in aliases and target in emotion_keys:
            aliases[alias] = target
            added_aliases += 1

    with open(EMOTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(emotions, f, ensure_ascii=False, indent=2)
    print(f"emotions.json: {added_aliases}개 별칭 추가 완료\n")

    # ── atmosphere_rules.json ─────────────────────────────────────────────────
    with open(ATMOSPHERE_PATH, encoding="utf-8") as f:
        atm = json.load(f)

    existing_season_keys = {
        k for rule in atm.get("season_rules", []) for k in rule.get("keys", [])
    }
    added_season = 0
    for rule in SEASON_RULES_TO_ADD:
        new_keys = [k for k in rule["keys"] if k not in existing_season_keys]
        if new_keys:
            matched = next(
                (r for r in atm["season_rules"] if r["season"] == rule["season"]), None
            )
            if matched:
                matched["keys"].extend(new_keys)
            else:
                atm["season_rules"].append({"keys": new_keys, "season": rule["season"]})
            existing_season_keys.update(new_keys)
            added_season += len(new_keys)

    existing_urban = set(atm.get("urban_keywords", []))
    new_urban = [k for k in URBAN_KEYWORDS_TO_ADD if k not in existing_urban]
    atm.setdefault("urban_keywords", []).extend(new_urban)

    with open(ATMOSPHERE_PATH, "w", encoding="utf-8") as f:
        json.dump(atm, f, ensure_ascii=False, indent=2)
    print(f"atmosphere_rules.json: 계절 +{added_season}개, 도시 +{len(new_urban)}개 추가 완료\n")

    # ── color_palette.json ────────────────────────────────────────────────────
    with open(COLOR_PATH, encoding="utf-8") as f:
        colors = json.load(f)

    existing_color_keys = {
        k for rule in colors.get("rules", []) for k in rule.get("keys", [])
    }
    added_colors = 0
    for rule in COLOR_RULES_TO_ADD:
        new_keys = [k for k in rule["keys"] if k not in existing_color_keys]
        if new_keys:
            colors["rules"].append({"keys": new_keys, "color": rule["color"]})
            existing_color_keys.update(new_keys)
            added_colors += len(new_keys)

    with open(COLOR_PATH, "w", encoding="utf-8") as f:
        json.dump(colors, f, ensure_ascii=False, indent=2)
    print(f"color_palette.json: {added_colors}개 색상 키워드 추가 완료\n")

    # ── 최종 통계 ─────────────────────────────────────────────────────────────
    with open(GENRES_PATH, encoding="utf-8") as f:
        genres_final = json.load(f)
    with open(EMOTIONS_PATH, encoding="utf-8") as f:
        emo_final = json.load(f)
    with open(COLOR_PATH, encoding="utf-8") as f:
        color_final = json.load(f)

    print("=== 최종 통계 ===")
    total_keys = sum(len(g.get("keys", [])) for g in genres_final)
    print(f"장르 프로필 수        : {len(genres_final)}개")
    print(f"장르 키워드 총합      : {total_keys}개")
    print(f"감정 별칭 수          : {len(emo_final.get('aliases', {}))}개")
    print(f"색상 키워드 총합      : {sum(len(r.get('keys',[])) for r in color_final.get('rules',[]))}개")
    print()
    for g in genres_final:
        print(f"  {g['name'][:40]:40s}: {len(g.get('keys', []))}개")


if __name__ == "__main__":
    run()
