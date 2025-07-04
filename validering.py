import datetime
from database import Database
from privat import _formater_svar
from retur_meldinger import UGYLDIG_INPUT, SUKSESS_INGEN_INNHOLD


def er_gyldig_dato(dato: str) -> bool:
    try:
        datetime.datetime.fromisoformat(dato)
        return True
    except ValueError:
        return False

def er_helltall(tall: int) -> bool:
    if not isinstance(tall, int):
        return False
    return True

def er_gyldig_handling(handling: str) -> bool:
    if handling.lower() not in ("innskudd", "uttak", "utlegg", "tilbakebetaling"):
        return False
    return True

def er_gyldig_tekst(tekst: str) -> bool:
    if not isinstance(tekst, str):
        return False
    return True


def er_gyldig_transaksjon_input(beløp: int, handling: str, dato: datetime, beskrivelse: str) -> dict:
    if not er_helltall(beløp):
        return _formater_svar(UGYLDIG_INPUT, [],
                              f'Feil type beløp. forventet int fikk "{beløp}", av typen {type(beløp).__name__}')

    if not er_gyldig_handling(handling):
        return _formater_svar(UGYLDIG_INPUT, [],
                              f'Feil type handling. forventet "innskudd", "uttak", "utlegg" eller "tilbakebetaling" fikk "{handling}", av typen {type(handling).__name__}')

    if not er_gyldig_dato(dato):
        return _formater_svar(UGYLDIG_INPUT, [], f'Feil type dato. forventet dato med isoformat fikk "{dato}", av typen {type(dato).__name__}')

    if beskrivelse:
        if not er_gyldig_tekst(beskrivelse):
            return _formater_svar(UGYLDIG_INPUT, [], f'Feil type beskrivelse. forventet str fikk "{beskrivelse}", av typen {type(beskrivelse).__name__}')

    return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")


def er_hentet_transaksjon_innhold_gyldig(transaksjon_innhold: dict) -> dict:
    pris = transaksjon_innhold.get("pris")
    handling = transaksjon_innhold.get("type")
    dato = transaksjon_innhold.get("dato")
    beskrivelse = transaksjon_innhold.get("beskrivelse")
    return er_gyldig_transaksjon_input(pris, handling, dato, beskrivelse)


def hent_tables(database: Database) -> list:
    return database.execute(".tables", fetchall=True)
