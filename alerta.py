import os, json, requests, feedparser
from datetime import date, timedelta
from urllib.parse import quote

KEYWORDS = [
 "aeropuerto","aeródromo","aerodromo","aeroportuaria","pista de aterrizaje",
 "airport","aerodrome","airfield","runway","airside","terminal building","air traffic",
 "aeroporto","aéroport","flughafen","aeroportuale"]
SEEN_FILE = "seen.json"
primera_vez = not os.path.exists(SEEN_FILE)
seen = set(json.load(open(SEEN_FILE))) if not primera_vez else set()
nuevas, vistos_ahora = [], set()

def add(titulo, link, fuente):
    if link and link not in seen and link not in vistos_ahora:
        vistos_ahora.add(link)
        nuevas.append((f"[{fuente}] {titulo}", link))

QUERIES = [
 ("licitación aeropuerto","es"),("convocatoria obras aeropuerto","es"),("concurso licitación aeroportuaria","es"),
 ("airport tender","en"),("airport RFP procurement","en"),("airport construction bid","en"),
 ("appel d'offres aéroport","fr"),("licitação aeroporto","pt"),("Ausschreibung Flughafen","de")]
for q, lang in QUERIES:
    try:
        url = f"https://news.google.com/rss/search?q={quote(q)}+when:2d&hl={lang}"
        for e in feedparser.parse(url).entries:
            add(e.title, e.link, "Noticias")
    except Exception as ex: print("RSS:", ex)

try:
    r = requests.post("https://api.ted.europa.eu/v3/notices/search", timeout=30, json={
        "query": "FT~(airport OR aeropuerto OR aeroporto OR flughafen)",
        "fields": ["notice-title","publication-number"], "limit": 50})
    for n in r.json().get("notices", []):
        add(str(n.get("notice-title")), f"https://ted.europa.eu/en/notice/-/detail/{n['publication-number']}", "TED-UE")
except Exception as ex: print("TED:", ex)

try:
    r = requests.get("https://search.worldbank.org/api/v2/procnotices",
        params={"format":"json","qterm":"airport","rows":50,"srt":"submission_date","order":"desc"}, timeout=30)
    for k, v in r.json().get("procnotices", {}).items():
        add(v.get("bid_description") or v.get("project_name"),
            f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{v.get('id')}", "BancoMundial")
except Exception as ex: print("WB:", ex)

try:
    r = requests.get("https://www.datos.gov.co/resource/p6dx-8zbt.json",
        params={"$q":"aeropuerto","$limit":50}, timeout=30)
    for o in r.json():
        u = o.get("urlproceso"); u = u.get("url") if isinstance(u, dict) else u
        add(o.get("descripci_n_del_procedimiento") or o.get("nombre_del_procedimiento"), u, "SECOP-CO")
except Exception as ex: print("SECOP:", ex)

def avisar(texto, titulo):
    requests.post(f"https://ntfy.sh/{os.environ['NTFY_TOPIC']}",
                  data=texto.encode("utf-8"), headers={"Title": titulo.encode("utf-8")})

if primera_vez:
    avisar("Sistema activo. Desde ahora recibirás solo lo nuevo.", "Alerta de aeropuertos lista")
elif nuevas:
    msg = "\n\n".join(f"{t}\n{l}" for t, l in nuevas)
    for i in range(0, len(msg), 3500):
        avisar(msg[i:i+3500], f"{len(nuevas)} nuevas licitaciones de aeropuertos")

seen.update(vistos_ahora)
json.dump(list(seen), open(SEEN_FILE, "w"))
