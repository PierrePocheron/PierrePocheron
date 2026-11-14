"""Génère assets/card-dark.svg et assets/card-light.svg : carte style neofetch avec tes stats GitHub en direct.

Lancé chaque nuit par .github/workflows/update-card.yml. Bibliothèque standard uniquement.
Le portrait ASCII est lu dans card/art.txt (généré par card/ascii_portrait.py).

Depuis la racine du repo :
    python3 card/update_profile.py --preview                       aperçu sans token ni réseau (card/preview_*.svg)
    GITHUB_TOKEN=$(gh auth token) python3 card/update_profile.py   vraies stats, écrit assets/card-*.svg
"""
import html
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

# ------------------------------------------------------------------ ce que tu modifies
USER = "PierrePocheron"
BIRTH_YEAR = 2000  # sert à calculer l'Uptime (année seule : l'âge affiché change au 1er janvier)

SYSTEM = {
    "OS": "Debian 13, macOS",
    "Uptime": "{uptime}",
    "Host": "Lyon, France",
    "Kernel": "Full-stack Developer",
    "Job": "Cybersecurity by day, entrepreneur by night",
    "IDE": "VS Code, Claude Code",
}
SKILLS = {
    "Languages.Programming": "TypeScript, Go, Java, Python",
    "Stack.Web": "Next.js, Svelte, Astro, Node.js, Tailwind",
    "Stack.Back": "Spring Boot, PostgreSQL, Docker",
    "Projects": "Hoome.dev, ERP Freelance, Reps",
    "Hobbies": "Dev, Weightlifting, Surf, Drone",
}
CONTACT = {
    "Email": "pierre.pocheron@gmail.com",
    "Website": "hoome.dev",
    "LinkedIn": "in/pierre-pocheron",
}
# ------------------------------------------------------------------

HERE = Path(__file__).resolve().parent  # dossier card/
ASSETS = HERE.parent / "assets"  # là où le README va chercher les SVG
W = 56  # largeur de la colonne d'infos, en caractères (clé + points + valeur)
RAMP = " .:-=+*#%@"  # même échelle que ascii_portrait.py, du vide au dense
ART_FONT, ART_LINE = 10, 11  # portrait plus fin que le texte (px) pour garder les détails du visage

# ACCESS_TOKEN (secret optionnel : token perso en lecture seule) voit aussi tes repos privés.
# Sinon le GITHUB_TOKEN fourni par Actions suffit pour tout ce qui est public.
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

PALETTES = {  # couleurs des thèmes GitHub ; art_lo / art / art_hi = 3 nuances du portrait
    "dark": {"bg": "#0d1117", "border": "#30363d", "art_lo": "#3d444d", "art": "#8b949e", "art_hi": "#c9d1d9",
             "h": "#58a6ff", "k": "#ffa657", "v": "#c9d1d9", "d": "#484f58", "g": "#3fb950", "r": "#f85149"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "art_lo": "#afb8c1", "art": "#57606a", "art_hi": "#24292f",
              "h": "#0969da", "k": "#953800", "v": "#24292f", "d": "#afb8c1", "g": "#1a7f37", "r": "#cf222e"},
}


# ------------------------------------------------------------------ stats GitHub
def gql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    if resp.get("errors"):
        raise RuntimeError(resp["errors"])
    return resp["data"]


REPOS_QUERY = """
query($login: String!, $cursor: String) { user(login: $login) {
  repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
    totalCount pageInfo { hasNextPage endCursor }
    nodes { name isFork stargazerCount }
  }
} }"""

LOC_QUERY = """
query($owner: String!, $name: String!, $id: ID!, $cursor: String) {
  repository(owner: $owner, name: $name) { defaultBranchRef { target { ... on Commit {
    history(first: 100, after: $cursor, author: {id: $id}) {
      pageInfo { hasNextPage endCursor }
      nodes { additions deletions }
    }
  } } } }
}"""


def fetch_stats():
    u = gql("""query($login: String!) { user(login: $login) {
        id createdAt followers { totalCount }
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
    } }""", login=USER)["user"]

    repos, cursor = [], None
    while True:
        page = gql(REPOS_QUERY, login=USER, cursor=cursor)["user"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    # commits : une fenêtre par année civile (l'API refuse plus d'un an), depuis la création du compte
    now = datetime.now(timezone.utc)
    windows = {
        y: (f"{y}-01-01T00:00:00Z", now.strftime("%Y-%m-%dT%H:%M:%SZ") if y == now.year else f"{y}-12-31T23:59:59Z")
        for y in range(int(u["createdAt"][:4]), now.year + 1)
    }
    fields = " ".join(
        f'y{y}: contributionsCollection(from: "{start}", to: "{end}")'
        " { totalCommitContributions restrictedContributionsCount }"
        for y, (start, end) in windows.items()
    )
    per_year = gql(f"query($login: String!) {{ user(login: $login) {{ {fields} }} }}", login=USER)["user"]
    commits = sum(v["totalCommitContributions"] + v["restrictedContributionsCount"] for v in per_year.values())

    # lignes de code : tes commits sur la branche par défaut de chacun de tes repos (hors forks)
    add = rem = 0
    for repo in (r for r in repos if not r["isFork"]):
        cursor = None
        try:
            while True:
                ref = gql(LOC_QUERY, owner=USER, name=repo["name"], id=u["id"], cursor=cursor)["repository"]["defaultBranchRef"]
                if ref is None:  # repo vide
                    break
                h = ref["target"]["history"]
                add += sum(n["additions"] for n in h["nodes"])
                rem += sum(n["deletions"] for n in h["nodes"])
                if not h["pageInfo"]["hasNextPage"]:
                    break
                cursor = h["pageInfo"]["endCursor"]
        except Exception as e:  # un repo illisible ne doit pas casser toute la carte
            print(f"LOC {repo['name']} : {e}")

    return {
        "repos": len(repos),
        "contributed": u["repositoriesContributedTo"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "followers": u["followers"]["totalCount"],
        "commits": commits,
        "loc": add - rem, "loc_add": add, "loc_del": rem,
    }


# ------------------------------------------------------------------ mise en page
def uptime(today):
    years = today.year - BIRTH_YEAR
    return f"{years} year{'s' if years != 1 else ''}"


def fmt(x):
    return f"{x:,}" if isinstance(x, int) else str(x)


def kv(key, val, width=W):
    dots = "." * max(width - len(key) - len(val) - 3, 1)
    return [(f"{key}: ", "k"), (dots + " ", "d"), (val, "v")]


def kv2(k1, v1, k2, v2):
    return kv(k1, v1, 30) + [(" | ", "d")] + kv(k2, v2, W - 33)


def rule(title):
    label = f"─ {title} "
    return [(label, "h"), ("─" * (W - len(label)), "d")]


def info_lines(s):
    up = uptime(date.today())
    block = lambda d: [kv(k, v.replace("{uptime}", up)) for k, v in d.items()]
    return [
        [(f"{USER.lower()}@github ", "h"), ("─" * (W - len(USER) - 8), "d")],
        [],
        *block(SYSTEM),
        [],
        *block(SKILLS),
        [],
        rule("Contact"),
        *block(CONTACT),
        [],
        rule("GitHub Stats"),
        kv2("Repos", f"{fmt(s['repos'])} {{Contributed: {fmt(s['contributed'])}}}", "Stars", fmt(s["stars"])),
        kv2("Commits", fmt(s["commits"]), "Followers", fmt(s["followers"])),
        [("Lines of Code: ", "k"), (fmt(s["loc"]), "v"), (" ( ", "d"),
         (fmt(s["loc_add"]) + "++", "g"), (", ", "d"), (fmt(s["loc_del"]) + "--", "r"), (" )", "d")],
    ]


def load_art():
    path = HERE / "art.txt"
    if not path.exists():
        print("card/art.txt introuvable : génère-le avec  python3 card/ascii_portrait.py ta_photo.png")
        return []
    return path.read_text(encoding="utf-8").strip("\n").split("\n")


def invert(line):
    # thème clair : caractères sombres sur fond blanc, on inverse les densités pour garder une image "positive"
    return line.translate(str.maketrans(RAMP[1:], RAMP[1:][::-1]))


def art_spans(line, p):
    # 3 nuances selon la densité du caractère : le visage gagne en relief
    def tone(ch):
        return ("art_lo", "art", "art_hi")[(RAMP.index(ch) - 1) // 3] if ch in RAMP[1:] else "art"

    runs, cur, buf = [], None, ""
    for ch in line:
        t = cur if ch == " " and cur else tone(ch)  # les espaces suivent la nuance en cours
        if t != cur and buf:
            runs.append((cur, buf))
            buf = ""
        cur, buf = t, buf + ch
    if buf:
        runs.append((cur, buf))
    return "".join(f'<tspan fill="{p[t]}">{html.escape(s)}</tspan>' for t, s in runs)


def render(mode, art, stats):
    p = PALETTES[mode]
    lines = info_lines(stats)
    height = max(500, 21 * len(lines) + 59, ART_LINE * len(art) + 70)
    art_top = (height - ART_LINE * len(art)) // 2 + ART_LINE - 2  # portrait centré verticalement
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="{height}" viewBox="0 0 840 {height}" '
        'font-family="Consolas, Menlo, monospace" font-size="13px">',
        f'<rect x="0.5" y="0.5" width="839" height="{height - 1}" rx="10" fill="{p["bg"]}" stroke="{p["border"]}"/>',
        f'<g font-size="{ART_FONT}px" fill="{p["art"]}">',
    ]
    for i, line in enumerate(art):
        line = invert(line) if mode == "light" else line
        out.append(f'<text x="25" y="{art_top + i * ART_LINE}" xml:space="preserve">{art_spans(line, p)}</text>')
    out.append("</g>")
    for i, segs in enumerate(lines):
        if segs:
            spans = "".join(f'<tspan fill="{p[c]}">{html.escape(t)}</tspan>' for t, c in segs)
            out.append(f'<text x="390" y="{45 + i * 21}" xml:space="preserve">{spans}</text>')
    out.append("</svg>")
    return "\n".join(out)


def selfcheck():
    assert uptime(date(BIRTH_YEAR + 26, 1, 1)) == "26 years"
    assert uptime(date(BIRTH_YEAR + 1, 12, 31)) == "1 year"
    assert invert("@%#*+=-:. ") == ".:-=+*#%@ "
    p = {"art_lo": "L", "art": "M", "art_hi": "H"}
    assert art_spans("  .:@@ +", p) == '<tspan fill="M">  </tspan><tspan fill="L">.:</tspan><tspan fill="H">@@ </tspan><tspan fill="M">+</tspan>'
    too_long = [k for d in (SYSTEM, SKILLS, CONTACT) for k, v in d.items() if len(k) + len(v) + 4 > W]
    assert not too_long, f"valeur trop longue pour la carte : {too_long}"


if __name__ == "__main__":
    selfcheck()
    preview = "--preview" in sys.argv
    stats = dict.fromkeys(["repos", "contributed", "stars", "followers", "commits", "loc", "loc_add", "loc_del"], "?") \
        if preview else fetch_stats()
    print("stats :", stats)
    art = load_art()
    ASSETS.mkdir(exist_ok=True)
    for mode in PALETTES:
        path = HERE / f"preview_{mode}.svg" if preview else ASSETS / f"card-{mode}.svg"
        path.write_text(render(mode, art, stats), encoding="utf-8")
        print("écrit :", path.relative_to(HERE.parent))
