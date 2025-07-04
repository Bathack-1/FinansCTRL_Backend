import json

from database import Database
import datetime
from retur_meldinger import SUKSESS_INGEN_INNHOLD, SUKSESS

def _formater_svar(status: int, innhold: dict or list, melding: str) -> dict:
    return {
        "status": status,
        "innhold": innhold,
        "melding": melding
    }

def _hent_key_med_value_fra_dict(dictionary: dict, value) -> str:
    try:
        mengde = list(dictionary.keys())[list(dictionary.values()).index(value)]
    except ValueError:
        return ""

    return mengde

def _hent_rad_fra_tabell(database: Database, tabellnavn : str, kolonnenavn : str, verdi : str or int, feilmelding: str) -> dict:
    rad = database.execute(f"SELECT * FROM {tabellnavn} WHERE {kolonnenavn} = ?", (verdi,), fetchone=True)

    if not rad:
        return _formater_svar(404, [], feilmelding)

    return _formater_svar(200, rad, "suksess")


def _finn_transaksjoner_på_id_liste(database: Database, transaksjon_ider: dict) -> dict:
    #transaksjon_ider = {"transaksjon_id": id}
    if not transaksjon_ider:
        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "Fant ingen")

    id_liste = list(transaksjon_ider.values())

    spørsmålstegn_tekst = ",".join(["?"] * len(id_liste))

    query = f"SELECT * FROM transaksjoner WHERE id in ({spørsmålstegn_tekst})"
    transaksjoner = database.execute(query, id_liste, fetchall=True)

    return _formater_svar(SUKSESS, transaksjoner, "suksess")


def _str_til_str_list_parser(tekst: str) -> list:
    """Gjør om en str av en liste til en liste feks '["båb","kåre", "baconost"]' -> ["båb","kåre", "baconost"] """

    try:
        tekst_liste = json.loads(tekst)

    except json.decoder.JSONDecodeError:

        tekst_deler = tekst.strip("[").strip("]").replace("'", "").split(",")

        tekst_liste = []
        for delen in tekst_deler:
            tekst_liste.append(delen.strip())

    return tekst_liste


def _filtrer_ut_tag_navn_fra_transaksjon(transaksjon) -> list[str]:
    alle_navn = []
    navn_i_transaksjon = transaksjon.get("innhold")
    for navn_gruppe in navn_i_transaksjon:
        alle_navn.append(navn_gruppe.get("navn"))

    return alle_navn