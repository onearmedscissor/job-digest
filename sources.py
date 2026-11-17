"""Additional job sources. Each function returns a list of job dicts:
source, title, url, company, location, model, date (ISO or ""), category, remote (bool), it (bool: IT-only source/category)."""
import datetime as dt, html, json, re, sys, time
import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"})

LINKEDIN_Q = ('developer OR software OR programador OR programação OR "back-end" OR backend OR junior OR ".NET" OR "C#" '
              'OR QA OR engineer OR engenheiro OR teste OR testing OR tester OR sistemas OR informação')
IEFP_CONCELHOS = ["COIMBRA", "CONDEIXA-A-NOVA", "MIRANDA DO CORVO", "PENACOVA", "VILA NOVA DE POIARES", "LOUSÃ", "MEALHADA"]


def get(url, method="GET", tries=3, **kw):
    for i in range(tries):
        try:
            r = S.request(method, url, timeout=40, **kw)
            if r.status_code == 429:
                time.sleep(10 * (i + 1)); continue
            r.raise_for_status()
            return r
        except Exception as e:
            if i == tries - 1:
                print(f"WARN {method} {url}: {e}", file=sys.stderr)
                return None
            time.sleep(3)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")).strip()


def job(source, title, url, company="", location="", model="", date="", category="", remote=False, it=False):
    return dict(source=source, title=clean(title), url=url, company=clean(company), location=clean(location), model=model,
                date=date, category=clean(category), remote=remote, it=it)


# ---------------- LinkedIn (guest job search) ----------------
def linkedin(since, today):
    out, days = [], (today - since).days
    searches = [("Coimbra", {"location": "Coimbra, Portugal", "distance": "25"}, False, 100),
                ("Remoto", {"location": "Portugal", "f_WT": "2"}, True, 700)]
    for _, params, remote, limit in searches:
        for start in range(0, limit, 10):
            r = get("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                    params={"keywords": LINKEDIN_Q, "f_TPR": f"r{days * 86400}", "start": start, **params})
            if not r or "base-card" not in r.text:
                break
            for card in r.text.split('<li')[1:]:
                t = re.search(r'base-search-card__title">(.*?)<', card, re.S)
                u = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?]+)', card)
                if not t or not u:
                    continue
                c = re.search(r'base-search-card__subtitle">(.*?)</h4>', card, re.S)
                loc = re.search(r'job-search-card__location">(.*?)<', card, re.S)
                d = re.search(r'datetime="([\d-]+)"', card)
                out.append(job("linkedin.com", t.group(1), u.group(1), c.group(1) if c else "", loc.group(1) if loc else "",
                               "Remoto" if remote else "", d.group(1) if d else "", remote=remote))
            time.sleep(1.5)
    return out


# ---------------- landing.jobs (public API) ----------------
def landingjobs(since, today):
    out = []
    for off in range(0, 1000, 50):
        r = get(f"https://landing.jobs/api/v1/jobs?limit=50&offset={off}")
        data = r.json() if r else []
        if not data:
            break
        for j in data:
            d = (j.get("published_at") or "")[:10]
            if d and d < since.isoformat():
                continue
            locs = ", ".join(l.get("city") or l.get("country_code") or "" for l in j.get("locations") or [])
            out.append(job("landing.jobs", j["title"], j["url"], (j.get("company") or {}).get("name", "") if isinstance(j.get("company"), dict) else "",
                           locs or ("Remoto" if j.get("remote") else ""), "Remoto" if j.get("remote") else "", d,
                           ", ".join(j.get("tags") or []), remote=bool(j.get("remote")), it=True))
    return out


# ---------------- cargadetrabalhos.pt (RSS) ----------------
def cargadetrabalhos(since, today):
    out = []
    r = get("https://cargadetrabalhos.pt/?feed=job_feed")
    if not r:
        return out
    for it in re.split(r"<(?:item|job-list-item)[\s>]", r.text)[1:]:
        f = lambda tag: (re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]{{1,2}}>)?</{tag}>", it, re.S) or [None, ""])[1]
        try:
            d = dt.datetime.strptime(" ".join(f("pubDate").split()[:3]), "%d %b %Y").date()
        except ValueError:
            d = None
        if d and d < since:
            continue
        addr, title = f("job_address"), f("title")
        remote = bool(re.search(r"remot|teletrabalho", (addr + " " + title).lower()))
        out.append(job("cargadetrabalhos.pt", title, f("link").strip(), f("company"), addr, "Remoto" if remote else "",
                       d.isoformat() if d else "", f("job_category"), remote=remote))
    return out


# ---------------- tecnojobs.pt ----------------
def tecnojobs(since, today):
    out = []
    for page in range(1, 2):  # site ignores ?page=N (always returns the latest 50)
        r = get(f"http://tecnojobs.pt/default.asp?page={page}")
        if not r:
            break
        h = r.content.decode("latin-1", "replace")
        items = re.findall(r'href="(/\d+/[^"]+/)">([^<]+)</a>.*?Data:</font><font[^>]*>([\d-]+)</font>.*?Local:</font><font[^>]*>([^<]*)</font>'
                           r'.*?Empresa:</font><font[^>]*>(.*?)<br>', h, re.S)
        if not items:
            break
        older = 0
        for href, title, d, loc, comp in items:
            d = dt.datetime.strptime(d, "%d-%m-%Y").date()
            if d < since:
                older += 1; continue
            remote = bool(re.search(r"remot|teletrabalho", (loc + " " + title).lower()))
            out.append(job("tecnojobs.pt", title, "http://tecnojobs.pt" + href, comp, loc, "Remoto" if remote else "",
                           d.isoformat(), remote=remote, it=True))
        if older == len(items):
            break
        time.sleep(1)
    return out


# ---------------- pt.teamlyzer.com ----------------
def _rel_days(s):
    s = s.lower()
    if re.search(r"hoje|hora|minuto|agora", s):
        return 0
    m = re.search(r"(\d+|um|uma)\s+(dia|semana|m[eê]s|ano)", s)
    if not m:
        return 999
    n = 1 if m.group(1) in ("um", "uma") else int(m.group(1))
    return n * {"dia": 1, "semana": 7, "mes": 30, "mês": 30, "ano": 365}[m.group(2)]


def teamlyzer(since, today):
    out, days = [], (today - since).days
    for q, remote in (("address=coimbra", False), ("work_model=remote-first", False)):
        for page in range(1, 10):
            r = get(f"https://pt.teamlyzer.com/companies/jobs?{q}&page={page}")
            if not r:
                break
            cards = r.text.split('class="panel jobcard"')[1:]
            if not cards:
                break
            for c in cards:
                t = re.search(r'jobcard__title-link" href="([^"]+)">(.*?)</a>', c, re.S)
                if not t:
                    continue
                age = re.search(r'jobcard__on-site"[^>]*>([^<]*)', c)
                ago = _rel_days(age.group(1)) if age else 999
                if ago > days:
                    continue
                comp = re.search(r'jobcard__company"[^>]*>(.*?)</a>', c, re.S)
                loc = re.search(r'jobcard__location">(.*?)</span>', c, re.S)
                loc = clean(loc.group(1)) if loc else ""
                rem = bool(re.search(r"regime: remot", loc.lower()))  # "Remote first" is not 100% remote
                out.append(job("teamlyzer.com", t.group(2), "https://pt.teamlyzer.com" + t.group(1), comp.group(1) if comp else "", loc,
                               "Remoto" if rem else "", (today - dt.timedelta(days=ago)).isoformat(), remote=rem, it=True))
            if f"page={page + 1}" not in r.text:
                break
            time.sleep(1)
    return out


# ---------------- Bolsa de Emprego da Ordem dos Engenheiros (área Informática) ----------------
def ordemengenheiros(since, today):
    out, base = [], "https://bolsaemprego.ordemdosengenheiros.pt"
    s = requests.Session(); s.headers.update(S.headers)
    try:
        h = s.post(base + "/pt/procurar-emprego-publico/", data={"areas[]": "7", "q": ""}, timeout=40).text
        for page in range(1, 20):
            for blk in h.split('class="offer-tablet-desktop"')[1:]:
                f = lambda cls: (re.search(rf'<div class="{cls}">(.*?)</div>', blk.split('class="offer-details"', 1)[-1], re.S) or [None, ""])[1]
                u = re.search(r'href="(/pt/procurar-emprego-publico/[^"]+-ref-[^"]+)"', blk)
                if not u:
                    continue
                loc, title = clean(f("city")), f("name")
                remote = bool(re.search(r"remot|teletrabalho", (loc + " " + title).lower()))
                out.append(job("ordemengenheiros.pt", title, base + u.group(1), f("employer"), loc, "Remoto" if remote else "",
                               "", "Informática; validade " + clean(f("expiration")), remote=remote, it=True))
            if f"pagina-{page + 1}/" not in h:
                break
            h = s.get(f"{base}/pt/procurar-emprego-publico/pagina-{page + 1}/", timeout=40).text
            time.sleep(1)
    except Exception as e:
        print("WARN ordemengenheiros:", e, file=sys.stderr)
    return out


# ---------------- netemprego.com ----------------
def netemprego(since, today):
    out = []
    for q, remote in (("distrito=8", False), ("q=teletrabalho", True), ("q=remoto", True)):
        for page in range(1, 40):
            r = get(f"http://netemprego.com/pesquisa/?{q}&ordem=recentes&pagina={page}")
            if not r:
                break
            cards = r.text.split('<article class="ne-job-card">')[1:]
            if not cards:
                break
            older = 0
            for c in cards:
                d = re.search(r'<time datetime="([\d-]+)"', c)
                t = re.search(r'<h3><a href="([^"]+)">(.*?)</a>', c, re.S)
                if not t:
                    continue
                if d and d.group(1) < since.isoformat():
                    older += 1; continue
                cat = re.search(r'ne-job-meta">\s*<a[^>]*>(.*?)</a>', c, re.S)
                comp = re.search(r'ne-company">\s*(?:<a[^>]*>)?(.*?)(?:</a>)?\s*<span>', c, re.S)
                loc = re.search(r'ne-company">.*?<span>(.*?)</span>', c, re.S)
                out.append(job("netemprego.com", t.group(2), t.group(1), comp.group(1) if comp else "", loc.group(1) if loc else "",
                               "Teletrabalho" if remote else "", d.group(1) if d else "", cat.group(1) if cat else "", remote=remote))
            if older == len(cards):
                break
            time.sleep(1)
    return out


# ---------------- IEFP (iefponline) ----------------
def iefp(since, today):
    out = []
    queries = [({"concelho_facet": c}, False) for c in IEFP_CONCELHOS] + [({"prestacao_trabalho": "Teletrabalho"}, True)]
    for extra, remote in queries:
        r = get("https://iefponline.iefp.pt/IEFP/pesquisas/search.do", method="POST",
                data={"cat": "ofertaEmprego", "action": "search", "submissao": "Semana", "resultsPerPage": "200", **extra})
        if not r:
            continue
        for c in r.text.split('<article class="card')[1:]:
            idm = re.search(r"ID:\s*(\d+)", c)
            t = re.search(r'<strong>([^<]+)</strong></div>\s*</div>\s*<div class="card-body', c)
            loc = re.search(r"Localização e Horário</div>\s*<div><strong>(.*?)</strong>", c, re.S)
            mode = re.search(r"Forma de prestação de trabalho</div>\s*<div>\s*(?:<strong>)?([^<]+)", c)
            if not idm or not t:
                continue
            mode = clean(mode.group(1)) if mode else ""
            rem = remote or mode.lower().startswith("teletrabalho")
            out.append(job("iefponline.iefp.pt", t.group(1).title(), f"https://iefponline.iefp.pt/IEFP/pesquisas/detalheOfertas2.do?idOferta={idm.group(1)}",
                           "", clean(loc.group(1)).split("|")[0].strip().title() if loc else "", mode, "", "publicada esta semana", remote=rem))
        time.sleep(1)
    return out


# ---------------- BEP - Bolsa de Emprego Público ----------------
def bep(since, today):
    out, u = [], "https://www.bep.gov.pt/pages/oferta/Oferta_Pesquisa_basica.aspx"
    p = "ctl00$ctl00$FormMasterContentPlaceHolder$ContentPlaceHolder1$"
    for term in ("informática", "sistemas", "software", "programador", "tecnologias de informação", "engenheiro informático"):
        s = requests.Session(); s.headers.update(S.headers)
        try:
            h = s.get(u, timeout=40).text
            data = dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', h))
            data.update({p + "txtValor": term, p + "ucSearch": "Pesquisar"})
            h = s.post(u, data=data, timeout=40).text
        except Exception as e:
            print("WARN bep:", e, file=sys.stderr); continue
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
            cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) < 9 or not re.match(r"OE\d{6}/\d+", cells[0]):
                continue
            code, _tipo, _vinc, carreira, categoria, distrito, organismo, _hab, limite = cells[:9]
            out.append(job("bep.gov.pt", f"{categoria or carreira} ({code})", f"https://www.bep.gov.pt/pages/oferta/Oferta_Pesquisa_basica.aspx#{code}",
                           organismo, f"{organismo} · {distrito}", "", "", f"{carreira}; pesquisa '{term}'; data limite {limite}"))
            out[-1]["district"] = distrito
        time.sleep(1)
    return out


# ---------------- portalemprego.pt ----------------
def portalemprego(since, today):
    out = []
    for page in range(1, 90):
        r = get(f"https://www.portalemprego.pt/anuncios/emprego/mostrar-20/pagina-{page}/")
        if not r:
            break
        items = re.findall(r'<a class="d-flex" href="([^"]+)"[^>]*>.*?<h5>(.*?)</h5>.*?postedDate">.*?</i>([\d-]+)</span>'
                           r'.*?company">.*?</i>(.*?)</span>.*?city">.*?</i>(.*?)</span>', r.text, re.S)
        if not items:
            break
        older = 0
        for href, title, d, comp, city in items:
            if d < since.isoformat():
                older += 1; continue
            remote = bool(re.search(r"remot|teletrabalho", (city + " " + title).lower()))
            out.append(job("portalemprego.pt", title, "https://www.portalemprego.pt" + href, comp, city, "Remoto" if remote else "", d, remote=remote))
        if older >= len(items) - 3:  # featured offers keep appearing at the top
            break
        time.sleep(1)
    return out


# ---------------- Foundever (RSS) ----------------
def foundever(since, today):
    out = []
    r = get("https://jobs.foundever.com/services/rss/job/?locale=pt_PT&keywords=&location=Portugal")
    if not r:
        return out
    for it in re.split(r"<item[\s>]", r.text)[1:]:
        f = lambda tag: (re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", it, re.S) or [None, ""])[1]
        title = clean(f("title"))
        try:
            d = dt.datetime.strptime(f("pubDate")[5:16], "%d %b %Y").date()
        except ValueError:
            d = None
        if d and d < since:
            continue
        loc = re.search(r"\(([^()]*)\)\s*$", title)
        remote = bool(re.search(r"remot|teletrabalho|work from home|home ?based|casa", title.lower()))
        out.append(job("foundever.com", title, f("link").strip(), "Foundever", loc.group(1) if loc else "Portugal",
                       "Remoto" if remote else "", d.isoformat() if d else "", remote=remote))
    return out


# ---------------- UC Apply (Universidade de Coimbra) ----------------
def ucapply(since, today):
    out = []
    for page in range(1, 20):
        r = get("https://applynext.fw.uc.pt/v1/search", method="POST",
                json={"items": {"pagination": {"current_page": page, "active_limit": 100}, "filters": []}})
        if not r:
            break
        d = r.json()["items"]
        for p in d["items"]:
            if p.get("applications_status") != "open":
                continue
            area = (p.get("area") or {}).get("pt", "")
            sub = (p.get("sub_area") or {}).get("pt", "")
            cat = (p.get("professional_category_key") or p.get("type_key") or "").replace("_", " ")
            out.append(job("apply.uc.pt", f"{p.get('prefix', '')}{p.get('code', '')} — {cat}: {area}" + (f" / {sub}" if sub and sub != "N/A" else ""),
                           f"https://www.apply.uc.pt/procedure/{p['key']}", "Universidade de Coimbra", "Coimbra", "",
                           p.get("publish_date") or "", f"candidaturas até {p.get('applications_end')}"))
        if page >= d["pagination"]["total_pages"]:
            break
    return out


# ---------------- SAPO Emprego (needs a real browser: Chrome via CDP) ----------------
def sapo(since, today, cdp="http://localhost:29229"):
    out = []
    try:
        import asyncio
        from playwright.async_api import async_playwright
    except ImportError:
        print("WARN sapo: playwright not installed", file=sys.stderr)
        return out

    async def run():
        async with async_playwright() as p:
            b = await p.chromium.connect_over_cdp(cdp)
            ctx = b.contexts[0] if b.contexts else await b.new_context()
            pg = await ctx.new_page()
            for url, remote in SAPO_URLS:
                try:
                    await pg.goto(url, timeout=45000)
                    await pg.wait_for_timeout(6000)
                    h = await pg.content()
                except Exception as e:
                    print("WARN sapo:", url, e, file=sys.stderr); continue
                for art in h.split("<article")[1:]:
                    t = re.search(r'<h3[^>]*>\s*<a[^>]*href="(https://emprego\.sapo\.pt/offers/[^"]+)"[^>]*>(.*?)</a>', art, re.S)
                    if not t:
                        continue
                    comp = re.search(r'class="name"><a[^>]*>(.*?)</a>', art, re.S)
                    loc = re.search(r'class="location">(.*?)</li>', art, re.S)
                    when = re.search(r'class="date">(.*?)</li>', art, re.S)
                    when = clean(when.group(1)) if when else ""
                    ago = _rel_days(when.replace("Últimas 24 horas", "hoje").replace("Últimos", "").replace("Ontem", "1 dia"))
                    if ago != 999 and ago > (today - since).days:
                        continue
                    out.append(job("emprego.sapo.pt", t.group(2), html.unescape(t.group(1)), comp.group(1) if comp else "",
                                   loc.group(1) if loc else "", "Teletrabalho" if remote else "",
                                   (today - dt.timedelta(days=ago)).isoformat() if ago != 999 else "", when, remote=remote))
            await pg.close()

    try:
        asyncio.run(run())
    except Exception as e:
        print("WARN sapo:", e, file=sys.stderr)
    return out


SAPO_URLS = [("https://emprego.sapo.pt/offers?local=coimbra&categoria=informatica-tecnologias", False),
             ("https://emprego.sapo.pt/offers?local=coimbra&categoria=engenharia", False)]
