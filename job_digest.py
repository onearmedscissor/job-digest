#!/usr/bin/env python3
"""Weekly job digest: Coimbra (<=20 km) or 100% remote offers matching IT keywords, from several Portuguese job sites."""
import argparse, datetime as dt, html, json, math, os, re, smtplib, ssl, sys, time, unicodedata, urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
COIMBRA = (40.2033, -8.4103)
MAX_KM = 20
TOWNS = {  # sede de concelho / localidades relevantes -> (lat, lon)
    "coimbra": (40.2033, -8.4103), "condeixa": (40.1130, -8.4970), "miranda do corvo": (40.0930, -8.3330),
    "penacova": (40.2700, -8.2810), "vila nova de poiares": (40.2110, -8.2580), "poiares": (40.2110, -8.2580),
    "lousa": (40.1120, -8.2470), "mealhada": (40.3780, -8.4490), "cantanhede": (40.3460, -8.5940),
    "montemor-o-velho": (40.1720, -8.6840), "penela": (39.9890, -8.3870), "soure": (40.0590, -8.6260),
    "figueira da foz": (40.1500, -8.8620), "mira": (40.4290, -8.7380), "mortagua": (40.3970, -8.2330),
    "anadia": (40.4370, -8.4350), "tabua": (40.3600, -8.0300), "arganil": (40.2180, -8.0540),
    "oliveira do hospital": (40.3600, -7.8620), "gois": (40.1560, -8.1110), "pampilhosa da serra": (40.0460, -7.9520),
    "pombal": (39.9160, -8.6280), "ansiao": (39.9110, -8.4350), "castanheira de pera": (40.0070, -8.2100),
    "pedrogao": (39.9170, -8.1450), "oliveira do bairro": (40.5150, -8.4930), "aveiro": (40.6405, -8.6538),
    "leiria": (39.7436, -8.8071), "viseu": (40.6566, -7.9125), "taveiro": (40.1880, -8.4800),
    "caldas da rainha": (39.4036, -9.1350), "lisboa": (38.7223, -9.1393), "porto": (41.1579, -8.6291),
    "braga": (41.5454, -8.4265), "algarve": (37.0194, -7.9304), "faro": (37.0194, -7.9304), "guarda": (40.5373, -7.2676),
    "castelo branco": (39.8222, -7.4909), "santarem": (39.2362, -8.6859), "tomar": (39.6017, -8.4092),
    "murtede": (40.3010, -8.5270), "arazede": (40.2830, -8.6530), "tocha": (40.3170, -8.7480), "eiras": (40.2300, -8.4200),
    "sao martinho do bispo": (40.2050, -8.4520), "ceira": (40.1830, -8.3830), "souselas": (40.2830, -8.4330),
    "lousã": (40.1120, -8.2470), "condeixa-a-nova": (40.1130, -8.4970), "sabugal": (40.3510, -7.0900),
    "ilhavo": (40.6000, -8.6670), "oeiras": (38.6970, -9.3100), "loures": (38.8310, -9.1680), "seixal": (38.6400, -9.1010),
    "palmela": (38.5690, -8.9010), "setubal": (38.5244, -8.8882), "almada": (38.6790, -9.1570), "sintra": (38.8029, -9.3817),
    "cascais": (38.6979, -9.4215), "amadora": (38.7538, -9.2308), "vila nova de gaia": (41.1239, -8.6118), "matosinhos": (41.1821, -8.6891),
    "maia": (41.2357, -8.6199), "guimaraes": (41.4425, -8.2918), "evora": (38.5714, -7.9135), "covilha": (40.2806, -7.5045),
    "viana do castelo": (41.6932, -8.8329), "vila real": (41.3006, -7.7441), "braganca": (41.8061, -6.7567), "beja": (38.0151, -7.8632),
    "portalegre": (39.2967, -7.4285), "madeira": (32.6669, -16.9241), "funchal": (32.6669, -16.9241), "acores": (37.7412, -25.6756),
    "ponta delgada": (37.7412, -25.6756), "lisbon": (38.7223, -9.1393), "oporto": (41.1579, -8.6291), "marinha grande": (39.7480, -8.9320),
    "ourem": (39.6580, -8.5770), "torres vedras": (39.0910, -9.2580), "alcobaca": (39.5520, -8.9770), "batalha": (39.6600, -8.8250),
}
KEYWORDS = [
    ("back-end", r"\bback[- ]?end\b"), ("programação", r"\bprograma(cao|dor|dora|dores)\b"),
    ("software", r"\bsoftware\b"), ("developer", r"\bdevelopers?\b"), ("junior", r"\bjunior\b"),
    (".NET", r"(?<![a-z0-9])\.net\b"), ("C#", r"(?<![a-z0-9])c#"), ("QA", r"\bqa\b"),
    ("engineer", r"\bengineer(s|ing)?\b"), ("teste", r"\btestes?\b"), ("testing", r"\btesting\b"),
    ("tester", r"\btesters?\b"), ("engenheiro", r"\bengenheir[oa]s?(\(a\))?\b|\beng\.?º?\s"),
    ("sistemas", r"\bsistemas?\b"), ("informação", r"\binformacao\b"),
]
ENG_KEYWORDS = {"engenheiro", "engineer"}  # only count these for IT/software offers
IT_CONTEXT = (r"informatic|software|\bti\b|\bit\b|\btic\b|tecnologias? d[ae] informacao|sistemas d[ae] informacao|\bdados\b|\bdata\b|devops|"
              r"cloud|\bqa\b|\btest|redes|network|ciberseg|cyber|security|\bsap\b|java|python|\.net|c#|\bweb\b|front[- ]?end|back[- ]?end|"
              r"full[- ]?stack|platform|plataforma|\bsre\b|reliability|machine learning|\bml\b|\bai\b|\bia\b|inteligencia artificial|"
              r"embedded|embebid|firmware|mobile|android|\bios\b|salesforce|kubernetes|\baws\b|azure|\bgcp\b|database|bases? de dados|"
              r"analytics|\bbi\b|developer|desenvolvi|programa|computa|automation engineer|test automation|integration|integracao de sistemas|"
              r"telecomunica|infraestrutura|infrastructure|sysadmin|administrador de sistemas|linux|windows|helpdesk|suporte informatico|\berp\b|\bcrm\b|"
              r"digital|tecnologi|technology|tech\b|it support|solutions? architect|arquitet[oa] de solucoes|scrum|agile|product owner|ux|ui\b")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def matched_keywords(text, it_source=False):
    t = norm(text)
    kws = [k for k, rx in KEYWORDS if re.search(rx, t)]
    if not it_source and not re.search(IT_CONTEXT, t):
        kws = [k for k in kws if k not in ENG_KEYWORDS]
    return kws


def towns_in(text):
    t = norm(text).replace("-", " ")
    return [n for n in TOWNS if re.search(r"\b" + re.escape(norm(n).replace("-", " ")) + r"\b", t)]


def in_area(location, title=""):
    """Location-based check for sources searched nationwide or by district: the specific place (first segment of the
    location) or the title must name a town within MAX_KM; unknown places are accepted only if they mention Coimbra."""
    loc = location or ""
    hierarchical = "·" in loc or re.search(r",\s*portugal\s*$", norm(loc))
    parts = [re.split(r"[·,]", loc)[0]] if hierarchical else re.split(r"[,/|;(]| - | ou | e ", loc)
    for p in parts:
        found = towns_in(p)
        if found and any(km(COIMBRA, TOWNS[n]) <= MAX_KM for n in found):
            return True
    if any(towns_in(p) for p in parts):
        return False
    found = towns_in(title)
    if found:
        return any(km(COIMBRA, TOWNS[n]) <= MAX_KM for n in found)
    return "coimbra" in norm(loc)


def near_coimbra(text):
    """True if no far town is mentioned, or at least one mentioned town is within MAX_KM."""
    found = towns_in(text)
    if not found:
        return True
    return any(km(COIMBRA, TOWNS[n]) <= MAX_KM for n in found)


def fetch(url, encoding="utf-8", tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-PT,pt;q=0.9"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode(encoding, "replace")
        except Exception as e:
            if i == tries - 1:
                print(f"WARN fetch failed {url}: {e}", file=sys.stderr)
                return ""
            time.sleep(3)


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ").strip(" \t\r\n")


# ---------------- itjobs.pt ----------------
PT_MONTHS = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def itjobs(query, since, today):
    out, page = [], 1
    while page <= 30:
        h = fetch(f"https://www.itjobs.pt/emprego?{query}&page={page}")
        if not h:
            break
        # split into daily blocks
        blocks = re.split(r'<div class="d-d">', h)[1:]
        if not blocks:
            break
        stop = False
        for b in blocks:
            m = re.match(r"\s*(\d+)</div>\s*<div class=\"d-m\">(\w+)</div>", b)
            if not m:
                continue
            d, mon = int(m.group(1)), PT_MONTHS.get(m.group(2).lower()[:3], 1)
            year = today.year if (mon, d) <= (today.month, today.day) else today.year - 1
            date = dt.date(year, mon, d)
            if date < since:
                stop = True
                continue
            for li in re.findall(r"<li[^>]*>(.*?)</li>", b, re.S):
                t = re.search(r'class="title"[^>]*title="([^"]*)"[^>]*href="([^"]+)"', li)
                if not t:
                    continue
                comp = re.search(r'class="list-name"><a[^>]*title="([^"]*)"', li)
                det = re.search(r'class="list-details">(.*?)</div>', li, re.S)
                details = clean(re.sub(r"<!--.*?-->", "", det.group(1), flags=re.S)) if det else ""
                parts = [p.strip() for p in re.split(r"\s{2,}", details) if p.strip()]
                models = ("Remoto", "Híbrido", "Presencial")
                loc = next((p for p in parts if p not in models), "")
                model = next((p for p in parts if p in models), "")
                out.append(dict(source="itjobs.pt", title=html.unescape(t.group(1)), url="https://www.itjobs.pt" + t.group(2),
                                company=html.unescape(comp.group(1)) if comp else "", location=loc, model=model,
                                date=date.isoformat(), category="", it=True))
        if stop or f"page={page + 1}" not in h:
            break
        page += 1
        time.sleep(1)
    return out


# ---------------- net-empregos.com ----------------
def netempregos(params, since):
    out, page = [], 1
    while page <= 200:
        url = f"https://www.net-empregos.com/pesquisa-empregos.asp?page={page}&chaves=&{params}"
        for attempt in range(3):
            h = fetch(url, encoding="latin-1")
            items = re.split(r'<div class="job-item media">', h)[1:]
            if items or "pesquisa-empregos" not in h:  # real empty page vs. blocked/partial response
                break
            print(f"WARN net-empregos: sem ofertas na página {page}, nova tentativa", file=sys.stderr)
            time.sleep(15)
        if not items:
            break
        older = 0
        for it in items:
            t = re.search(r'<h2[^>]*>\s*<a[^>]*href=["\']?(/\d+/[^"\' >]+)["\']?[^>]*>(.*?)</a>', it, re.S)
            if not t:
                continue
            date_m = re.search(r"flaticon-calendar.*?</i>\s*(\d{2})-(\d{2})-(\d{4})", it, re.S)
            date = dt.date(int(date_m.group(3)), int(date_m.group(2)), int(date_m.group(1))) if date_m else None
            if date and date < since:
                older += 1
                continue
            loc = re.search(r"flaticon-pin.*?</i>([^<]*)", it, re.S)
            cat = re.search(r"fa-tags.*?</i>([^<]*)", it, re.S)
            comp = re.search(r"flaticon-work.*?</i>([^<]*)", it, re.S)
            out.append(dict(source="net-empregos.com", title=clean(t.group(2)), url="https://www.net-empregos.com" + t.group(1),
                            company=clean(comp.group(1)) if comp else "", location=clean(loc.group(1)) if loc else "",
                            model="", date=date.isoformat() if date else "", category=clean(cat.group(1)) if cat else ""))
        if older == len(items):
            break
        page += 1
        time.sleep(1)
    return out


def collect(days):
    today = dt.date.today()
    since = today - dt.timedelta(days=days)
    jobs = []
    # itjobs: distrito de Coimbra (qualquer modelo) + 100% remoto (qualquer local)
    for j in itjobs("location=8", since, today):
        if near_coimbra(j["location"] + " " + j["title"]) or j["model"] == "Remoto":
            j["reason"] = "Remoto" if j["model"] == "Remoto" else "Coimbra"
            jobs.append(j)
    for j in itjobs("work_model=1", since, today):
        j["reason"] = "Remoto"
        jobs.append(j)
    # net-empregos: zona Coimbra, Mealhada (zona Aveiro) e Teletrabalho (todas as zonas)
    for j in netempregos("cidade=&categoria=0&zona=9&tipo=0", since):
        if near_coimbra(j["title"]):
            j["reason"] = "Coimbra"
            jobs.append(j)
    for j in netempregos("cidade=Mealhada&categoria=0&zona=4&tipo=0", since):
        if "mealhada" in norm(j["title"]):
            j["reason"] = "Coimbra (Mealhada)"
            jobs.append(j)
    for j in netempregos("cidade=&categoria=0&zona=0&tipo=4", since):
        j["reason"] = "Teletrabalho"
        jobs.append(j)
    for src in ("itjobs.pt", "net-empregos.com"):
        n = sum(j["source"] == src for j in jobs)
        SOURCE_STATS[src] = (n, n, 0)
        if n == 0:
            print(f"WARN {src}: 0 ofertas", file=sys.stderr)
    jobs += collect_extra(since, today)
    seen, result = set(), []
    for j in jobs:
        kws = matched_keywords(j["title"] + " " + j["category"], j.get("it", False))
        dup = (norm(j["title"]), norm(j["company"]))
        if not kws or j["url"] in seen or (j["company"] and dup in seen):
            continue
        seen.update({j["url"], dup})
        j["keywords"] = kws
        result.append(j)
    result.sort(key=lambda j: (j["source"], j["date"]), reverse=True)
    return result, since, today


EXTRA_SOURCES = ["linkedin", "landingjobs", "sapo", "cargadetrabalhos", "tecnojobs", "teamlyzer", "ordemengenheiros",
                 "netemprego", "iefp", "bep", "portalemprego", "foundever", "ucapply"]
SOURCE_STATS = {}


def collect_extra(since, today):
    import sources
    out = []
    for name in EXTRA_SOURCES:
        t0 = time.time()
        try:
            got = getattr(sources, name)(since, today)
        except Exception as e:
            print(f"WARN {name} failed: {e}", file=sys.stderr)
            got = []
        kept = 0
        for j in got:
            if name in ("iefp", "ucapply"):
                ok, reason = True, ("Teletrabalho" if j["remote"] else "Coimbra")
            elif name == "bep":
                ok, reason = norm(j.get("district", "")) == "coimbra" and near_coimbra(j["company"]), "Coimbra"
            elif j["remote"]:
                ok, reason = True, "Remoto"
            else:
                ok, reason = in_area(j["location"], j["title"]), "Coimbra"
            if ok:
                j["reason"] = reason
                out.append(j); kept += 1
        SOURCE_STATS[name] = (len(got), kept, round(time.time() - t0))
        print(f"{name}: {len(got)} recolhidas, {kept} na zona/remotas ({time.time() - t0:.0f}s)", file=sys.stderr)
    return out


def render(jobs, since, today):
    subject = f"Ofertas de emprego Coimbra/Remoto — {since:%d/%m} a {today:%d/%m/%Y} ({len(jobs)})"
    rows_html, lines = [], [subject, ""]
    for src in sorted({j["source"] for j in jobs}):
        sj = [j for j in jobs if j["source"] == src]
        rows_html.append(f'<h3 style="margin:18px 0 6px">{html.escape(src)} ({len(sj)})</h3><table cellpadding="6" style="border-collapse:collapse;font:14px Arial,sans-serif;width:100%">'
                         '<tr style="background:#eee;text-align:left"><th>Data</th><th>Oferta</th><th>Empresa</th><th>Local</th><th>Palavras</th></tr>')
        lines.append(f"== {src} ({len(sj)}) ==")
        for j in sj:
            extra = [x for x in (j["model"], j["reason"]) if x and x not in j["location"]]
            loc = " · ".join(dict.fromkeys([j["location"]] + extra if j["location"] else extra))
            rows_html.append(f'<tr style="border-top:1px solid #ddd"><td style="white-space:nowrap">{html.escape(j["date"] or "destaque")}</td>'
                             f'<td><a href="{html.escape(j["url"])}">{html.escape(j["title"])}</a></td><td>{html.escape(j["company"])}</td>'
                             f'<td>{html.escape(loc)}</td><td>{html.escape(", ".join(j["keywords"]))}</td></tr>')
            lines.append(f"- [{j['date'] or 'destaque'}] {j['title']} — {j['company']} — {loc}\n  {j['url']}")
        rows_html.append("</table>")
        lines.append("")
    if not jobs:
        rows_html.append("<p>Sem ofertas novas esta semana.</p>")
        lines.append("Sem ofertas novas esta semana.")
    if SOURCE_STATS:
        stats = "; ".join(f"{n}: {got} recolhidas/{kept} na zona" + (" (FALHOU?)" if got == 0 else "") for n, (got, kept, _) in SOURCE_STATS.items())
        rows_html.append(f'<p style="color:#777;font-size:12px">Fontes — {html.escape(stats)}</p>')
        lines.append("Fontes — " + stats)
    body_html = (f'<div style="font:14px Arial,sans-serif"><h2>{html.escape(subject)}</h2>'
                 f'<p>Critérios: Coimbra (raio ≤ {MAX_KM} km) ou 100% remoto/teletrabalho, com pelo menos uma das palavras: '
                 f'{html.escape(", ".join(k for k, _ in KEYWORDS))}.</p>{"".join(rows_html)}</div>')
    return subject, body_html, "\n".join(lines)


def send_smtp(to, subject, body_html, body_text):
    host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "465"))
    user, pwd = os.environ["SMTP_USER"], os.environ["SMTP_PASS"]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ.get("SMTP_FROM", user), to
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=60) as s:
            s.login(user, pwd); s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=60) as s:
            s.starttls(context=ctx); s.login(user, pwd); s.send_message(msg)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--to", default="joaoandreferro@sapo.pt")
    ap.add_argument("--send", action="store_true", help="enviar por SMTP (SMTP_HOST/PORT/USER/PASS)")
    ap.add_argument("--out", default="digest")
    a = ap.parse_args()
    jobs, since, today = collect(a.days)
    subject, body_html, body_text = render(jobs, since, today)
    open(a.out + ".html", "w").write(body_html)
    open(a.out + ".txt", "w").write(body_text)
    json.dump(dict(subject=subject, count=len(jobs), jobs=jobs), open(a.out + ".json", "w"), ensure_ascii=False, indent=1)
    print(subject)
    if a.send:
        send_smtp(a.to, subject, body_html, body_text)
        print("Enviado para", a.to)
