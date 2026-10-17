"""Actualiza games.json con la API de Steam, SteamSpy y PCGamingWiki.

Lo lanza a mano la GitHub Action .github/workflows/update-catalog.yml.
Solo usa la librería estándar. Uso local:
  python scripts/update_catalog.py precios    # ~1 min: precios y ofertas del catálogo actual
  python scripts/update_catalog.py jugadores  # ~5 min: nº máximo de jugadores (PCGamingWiki) de los juegos que no lo tienen
  python scripts/update_catalog.py completo   # ~25 min: juegos nuevos, reseñas, etiquetas, precios y jugadores

Formato de cada juego en games.json:
  [appid, nombre, descripción, temáticas, modo, gratis, precio, % positivas, nº reseñas, géneros, máx. jugadores (0 = sin dato)]
"""
import html, json, os, re, sys, threading, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "games.json")
CANDIDATES = 600      # juegos multijugador más reseñados que se consultan
MAX_GAMES = 500       # tope del catálogo final
MIN_GAMES = 200       # por debajo de esto se asume fallo de la API y no se sobrescribe nada

MULTI_TAGS = ["Co-op", "Online Co-Op", "Multiplayer", "PvP", "Online PvP",
              "Local Multiplayer", "Party Game", "Massively Multiplayer", "4 Player Local"]

THEMES = [
  ("terror", "Terror", ["Horror", "Psychological Horror", "Survival Horror"]),
  ("superv", "Supervivencia", ["Survival", "Open World Survival Craft", "Crafting"]),
  ("shooter", "Shooter", ["FPS", "Shooter", "Third-Person Shooter", "Looter Shooter", "Hero Shooter", "Arena Shooter"]),
  ("br", "Battle royale", ["Battle Royale"]),
  ("tactico", "Táctico y militar", ["Tactical", "Military", "Realistic", "War"]),
  ("estrat", "Estrategia", ["Strategy", "RTS", "4X", "Turn-Based Strategy", "Grand Strategy", "Tower Defense", "Real Time Tactics"]),
  ("rpg", "Rol (RPG)", ["RPG", "Action RPG", "CRPG", "JRPG", "MMORPG", "Party-Based RPG"]),
  ("fiesta", "Fiesta y risas", ["Party Game", "Party", "Funny", "Comedy", "Mini Golf"]),
  ("puzles", "Puzles", ["Puzzle", "Puzzle Platformer", "Logic"]),
  ("sandbox", "Construcción y sandbox", ["Sandbox", "Building", "Base Building", "Automation", "City Builder", "Colony Sim"]),
  ("carreras", "Carreras y deportes", ["Racing", "Sports", "Driving", "Football (Soccer)", "Basketball", "Golf", "Automobile Sim"]),
  ("lucha", "Lucha", ["Fighting", "Beat 'em up", "Martial Arts", "2D Fighter", "3D Fighter"]),
  ("simul", "Simulación y gestión", ["Simulation", "Management", "Life Sim", "Job Simulator"]),
  ("relax", "Relax y cozy", ["Relaxing", "Cozy", "Casual", "Farming Sim", "Cute", "Wholesome"]),
  ("scifi", "Ciencia ficción", ["Sci-fi", "Space", "Cyberpunk", "Aliens"]),
  ("fantasia", "Fantasía", ["Fantasy", "Dark Fantasy", "Medieval", "Magic"]),
  ("zombis", "Zombis", ["Zombies"]),
  ("mundo", "Mundo abierto", ["Open World", "Exploration"]),
  ("rogue", "Roguelike", ["Roguelike", "Roguelite", "Action Roguelike"]),
  ("moba", "MOBA", ["MOBA"]),
  ("mesa", "Cartas y mesa", ["Card Game", "Board Game", "Deckbuilding", "Tabletop", "Card Battler"]),
  ("atracos", "Sigilo y atracos", ["Heist", "Stealth"]),
  ("deduccion", "Deducción social", ["Social Deduction"]),
  ("plataf", "Plataformas", ["Platformer", "2D Platformer", "3D Platformer"]),
  ("anime", "Anime", ["Anime"]),
  ("souls", "Souls y desafío", ["Souls-like", "Difficult"]),
]
NSFW_ANY = {"Hentai", "NSFW"}            # en las 15 etiquetas principales
NSFW_TOP = {"Sexual Content", "Nudity"}  # en las 5 principales
COOP = {9, 38, 48, 39}
PVP = {49, 36, 47, 37, 20}
ONLINE = {36, 38, 20, 44}  # PvP online, coop online, MMO, Remote Play Together


def get_json(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "a-que-jugamos-catalog/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            time.sleep(60 if e.code in (403, 429) else 5)
        except Exception:
            time.sleep(5)
    return None


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= 260 else s[:257].rsplit(" ", 1)[0] + "…"


def format_price(is_free, po):
    if is_free:
        return "Gratis"
    if po.get("discount_percent"):
        return f"{po.get('final_formatted', '')} (-{po['discount_percent']}%)"
    return po.get("final_formatted", "")


PCGW = "https://www.pcgamingwiki.com"
PLAYER_FIELDS = re.compile(r"^\|\s*(?:online|lan|local) play (?:players|notes)\s*=\s*(.*)$", re.M)
# Frases inequívocas en la descripción de Steam («hasta 4 jugadores», «up to 8 players», «4-player co-op»).
DESC_PLAYERS = [re.compile(r"(?:hasta|up to)\s*(\d{1,3})\s*(?:jugadores|players|personas|amigos|friends)"),
                re.compile(r"(\d{1,2})[- ](?:player|jugadores)\s*(?:co-?op|cooperativ)")]


def wiki_players(page):
    d = get_json(f"{PCGW}/w/api.php?action=parse&prop=wikitext&format=json&formatversion=2&redirects=1&page="
                 + urllib.parse.quote(page), tries=2)
    wikitext = ((d or {}).get("parse") or {}).get("wikitext", "")
    nums = [int(n) for v in PLAYER_FIELDS.findall(wikitext) for n in re.findall(r"\d+", v.split("<")[0])]
    nums = [n for n in nums if 1 < n <= 1000]
    return max(nums) if nums else 0


def max_players(appid, name, description=""):
    """Máximo de jugadores (online, LAN o local). Busca en PCGamingWiki por ID de Steam y, si el ID es ambiguo
    o la ficha está vacía, por nombre; como último recurso, en la descripción de Steam. 0 si no hay dato."""
    try:
        req = urllib.request.Request(f"{PCGW}/api/appid.php?appid={appid}", method="HEAD",
                                     headers={"User-Agent": "a-que-jugamos-catalog/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            url = r.geturl()
    except Exception:
        url = ""
    n = 0
    if "/wiki/" in url:
        n = wiki_players(urllib.parse.unquote(url.rsplit("/wiki/", 1)[1]).replace("_", " "))
    if not n:
        time.sleep(0.3)
        n = wiki_players(re.sub(r"[™®©]", "", name).strip())
    if not n and description:
        text = html.unescape(re.sub(r"<[^>]+>", " ", description)).lower()
        found = [int(m.group(1)) for p in DESC_PLAYERS for m in p.finditer(text)]
        found = [x for x in found if 2 <= x <= 100]
        n = max(found) if found else 0
    return n


def fill_players(games, known, descriptions=None):
    """Pone el nº de jugadores (posición 10) reutilizando los ya conocidos y consultando solo los que faltan."""
    missing = 0
    for g in games:
        while len(g) < 11:
            g.append(0)
        if known.get(g[0]):
            g[10] = known[g[0]]
            continue
        g[10] = max_players(g[0], g[1], (descriptions or {}).get(g[0], ""))
        missing += 1
        time.sleep(0.4)
    print(f"jugadores consultados: {missing} · con dato: {sum(1 for g in games if g[10])} de {len(games)}", flush=True)


def load_catalog():
    with open(OUT, encoding="utf-8") as f:
        return json.load(f)


def save_catalog(cat):
    cat["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, separators=(",", ":"))


def update_players():
    cat = load_catalog()
    fill_players(cat["games"], {g[0]: g[10] for g in cat["games"] if len(g) > 10 and g[10]})
    save_catalog(cat)


def update_prices():
    cat = load_catalog()
    games, changed = cat["games"], 0
    for i in range(0, len(games), 50):
        batch = games[i:i + 50]
        ids = ",".join(str(g[0]) for g in batch)
        d = get_json(f"https://store.steampowered.com/api/appdetails?appids={ids}&cc=es&filters=price_overview") or {}
        for g in batch:
            info = d.get(str(g[0])) or {}
            data = info.get("data")
            if not info.get("success") or g[5]:  # sin datos o juego gratuito: se deja como estaba
                continue
            po = data.get("price_overview") if isinstance(data, dict) else None
            if po:
                price = format_price(False, po)
                if price and price != g[6]:
                    g[6], changed = price, changed + 1
        time.sleep(1.5)
    save_catalog(cat)
    print(f"precios cambiados: {changed} de {len(games)}")


def main():
    mode = (sys.argv[1:] or ["precios"])[0]
    if mode == "precios":
        return update_prices()
    if mode == "jugadores":
        return update_players()
    pool = {}
    for tag in MULTI_TAGS:
        d = get_json("https://steamspy.com/api.php?request=tag&tag=" + urllib.parse.quote(tag))
        if isinstance(d, dict):
            pool.update(d)
        time.sleep(1.1)
    cands = [g for g in pool.values() if g.get("positive", 0) >= 3000
             and g["positive"] / max(1, g["positive"] + g["negative"]) >= 0.75]
    cands.sort(key=lambda g: -g["positive"])
    cands = cands[:CANDIDATES]
    print(f"candidatos: {len(cands)}", flush=True)

    spy, store = {}, {}

    def fetch_spy():
        for g in cands:
            spy[g["appid"]] = get_json(f"https://steamspy.com/api.php?request=appdetails&appid={g['appid']}")
            time.sleep(1.1)

    def fetch_store():
        for i, g in enumerate(cands):
            d = get_json(f"https://store.steampowered.com/api/appdetails?appids={g['appid']}"
                         "&l=spanish&cc=es&filters=basic,categories,genres,price_overview")
            store[g["appid"]] = (d or {}).get(str(g["appid"]))
            if i % 100 == 0:
                print(f"tienda: {i}/{len(cands)}", flush=True)
            time.sleep(1.6)

    threads = [threading.Thread(target=fetch_spy), threading.Thread(target=fetch_store)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    games = []
    for c in cands:
        appid = c["appid"]
        sp, st = spy.get(appid), store.get(appid)
        if not sp or not st or not st.get("success"):
            continue
        d = st["data"]
        if d.get("type") != "game":
            continue
        tags = sp.get("tags") or {}
        if isinstance(tags, list):
            continue
        top = list(tags)
        if NSFW_ANY & set(top[:15]) or NSFW_TOP & set(top[:5]):
            continue
        cats = {x["id"] for x in d.get("categories", [])}
        if not (cats & ONLINE or (1 in cats and not cats & {24, 37, 39})):
            continue
        po = d.get("price_overview") or {}
        if not d.get("is_free") and not po:
            continue  # ya no se vende en España
        coop, pvp = bool(cats & COOP), bool(cats & PVP)
        mode = "a" if coop and pvp else "c" if coop else "p" if pvp else "a"
        themes = [i for i, (_, _, ts) in enumerate(THEMES) if set(ts) & set(top[:15])]
        price = format_price(d.get("is_free"), po)
        pos, neg = sp["positive"], sp["negative"]
        games.append([appid, d["name"].strip(), clean(d.get("short_description")), themes, mode,
                      1 if d.get("is_free") else 0, price, round(100 * pos / (pos + neg)), pos + neg,
                      ", ".join(x["description"] for x in d.get("genres", [])[:3])])

    games.sort(key=lambda g: -g[8])
    games = games[:MAX_GAMES]
    print(f"juegos válidos: {len(games)}", flush=True)
    if len(games) < MIN_GAMES:
        print("Demasiado pocos juegos: probablemente la API ha fallado. No se toca games.json.")
        sys.exit(1)
    try:  # el nº de jugadores casi nunca cambia: se reutiliza y solo se consultan los juegos nuevos
        known = {g[0]: g[10] for g in load_catalog()["games"] if len(g) > 10 and g[10]}
    except Exception:
        known = {}
    descriptions = {a: (s or {}).get("data", {}).get("detailed_description", "") for a, s in store.items() if s}
    fill_players(games, known, descriptions)
    save_catalog({"themes": [[k, label] for k, label, _ in THEMES], "games": games})


if __name__ == "__main__":
    main()
