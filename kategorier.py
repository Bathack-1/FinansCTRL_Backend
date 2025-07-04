from sqlite3 import OperationalError
from privat import _hent_rad_fra_tabell, _formater_svar, _finn_transaksjoner_på_id_liste
from retur_meldinger import *
from validering import *

class Kategorier:
    def __init__(self, database: Database):
        self.database = database

    def legg_til(self, kategori_navn):
        """Legge til en ny kategori i databasen"""
        if not er_gyldig_tekst(kategori_navn):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type str, fikk {kategori_navn} av typen {type(kategori_navn).__name__}")

        try:
            retur_verdi = self.database.execute("INSERT INTO kategorier(navn) VALUES (?) RETURNING *", (kategori_navn,), fetchone=True, commit=True)
            return _formater_svar(OPPRETTET_NY, retur_verdi, "suksess")

        except OperationalError as e:
            return _formater_svar(TABEL_FINNES_IKKE, [], f"Kunne ikke legge til kategori: {kategori_navn}, feilmelding {e}")


    def hent_på_id(self, iden: int) -> dict:
        """status: int, innhold: [{id, navn}], message: str"""
        if not er_helltall(iden):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type int, fikk {iden} av typen {type(iden).__name__}")

        return _hent_rad_fra_tabell(self.database, "kategorier", "id", iden, f"Fant ingen kategori med iden {iden}")


    def hent_på_navn(self, kategori_navn: str) -> dict:
        """status: int, innhold: [{id, navn}], message: str"""
        if not er_gyldig_tekst(kategori_navn):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type str, fikk {kategori_navn} av typen {type(kategori_navn).__name__}")

        return _hent_rad_fra_tabell(self.database, "kategorier", "navn", kategori_navn, f"Fant ingen kategori med navn {kategori_navn}")


    def hent_transaksjoner(self, kategori_id) -> dict:
        """status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""
        transaksjon_ider = self.database.execute("SELECT transaksjon_id FROM kategori_tag WHERE kategori_id = ?", (kategori_id,),
                                      fetchone=True)

        return _finn_transaksjoner_på_id_liste(self.database, transaksjon_ider)


    def oppdater_kategori(self, kategori_id, kategori_navn) -> dict:
        """status: int, innhold: [], message: str"""
        kategori = self.database.execute(
            "UPDATE kategorier SET navn = ? WHERE id = ? RETURNING *", (kategori_navn, kategori_id,),
            fetchone=True, commit=True)

        if not kategori:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "Tomme celler. Kan være feil kategori_id")

        return _formater_svar(SUKSESS, kategori, "suksess")

    def fjern_kategori(self, kategori_id) -> dict:
        """status: int, innhold: [], message: str"""
        self.database.execute("DELETE FROM kategorier WHERE id = ?", (kategori_id,), commit=True)
        self.database.execute("DELETE FROM kategori_tag WHERE kategori_id = ?", (kategori_id,), commit=True)
        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")


