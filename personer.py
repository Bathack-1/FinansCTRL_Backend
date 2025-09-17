from sqlite3 import OperationalError
from privat import _hent_rad_fra_tabel, _formater_svar, _finn_transaksjoner_på_id_liste
from retur_meldinger import *
from validering import *

class Personer:
    def __init__(self, database: Database):
        self.database = database

    def legg_til(self, navn : str):
        """Legge til en ny person i databasen"""
        if not er_gyldig_tekst(navn):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type str, fikk {navn} av typen {type(navn).__name__}")

        try:
            retur_verdi = self.database.execute("INSERT INTO personer(navn) VALUES (?) RETURNING *", (navn,), fetchone=True, commit=True)
            return _formater_svar(OPPRETTET_NY, retur_verdi, "suksess")

        except OperationalError as e:
            return _formater_svar(TABEL_FINNES_IKKE, [], f"Kunne ikke legge til personen: {navn}, feilmelding {e}")


    def hent_på_id(self, iden : int) -> dict:
        """status: int, innhold: [{id, navn}], message: str"""
        if not er_helltall(iden):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type int, fikk {iden} av typen {type(iden).__name__}")

        return _hent_rad_fra_tabel(self.database, "personer", "id", iden, f"Fant ingen personer med iden {iden}")


    def hent_på_navn(self, navn : str) -> dict:
        """status: int, innhold: [{id, navn}], message: str"""
        if not er_gyldig_tekst(navn):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type str, fikk {navn} av typen {type(navn).__name__}")

        return _hent_rad_fra_tabel(self.database, "personer", "navn", navn, f"Fant ingen personer med navn {navn}")


    def hent_transaksjoner(self, person_id) -> dict:
        """status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""
        transaksjon_ider = self.database.execute("SELECT transaksjon_id FROM person_tag WHERE person_id = ?",
                                      (person_id,), fetchone=True)

        return _finn_transaksjoner_på_id_liste(self.database, transaksjon_ider)


    def oppdater_person(self, person_id, person_navn) -> dict:
        """status: int, innhold: [], message: str"""
        person = self.database.execute(
            "UPDATE personer SET navn = ? WHERE id = ? RETURNING *", (person_navn, person_id,),
            fetchone=True, commit=True)

        if not person:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "Tomme celler. Kan være feil person_id")

        return _formater_svar(SUKSESS, person, "suksess")


    def fjern_person(self, person_id) -> dict:
        """status: int, innhold: [], message: str"""
        self.database.execute("DELETE FROM personer WHERE id = ?", (person_id,), commit=True)
        self.database.execute("DELETE FROM person_tag WHERE person_id = ?", (person_id,), commit=True)
        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")

