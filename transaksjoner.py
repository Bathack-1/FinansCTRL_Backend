import typing
from sqlite3 import OperationalError
from personer import Personer
from kategorier import Kategorier
from privat import _hent_rad_fra_tabell, _formater_svar, _str_til_str_list_parser, _filtrer_ut_tag_navn_fra_transaksjon
from retur_meldinger import *
from validering import *
import datetime
import csv

class Transaksjoner:
    def __init__(self, databse : Database, personer : Personer, kategorier : Kategorier):
        self.database = databse
        self.personer = personer
        self.kategorier = kategorier


    def skriv(self, beløp: int, handling: str, dato: datetime, beskrivelse: str = ""):

        validert = er_gyldig_transaksjon_input(beløp, handling, dato, beskrivelse)
        if validert.get("status") != SUKSESS_INGEN_INNHOLD:
            return _formater_svar(validert.get("status"), [], validert.get('melding'))

        if self._finnes_transaksjon_i_db({"pris": beløp, "type": handling, "dato": dato, "beskrivelse": beskrivelse}):
            return _formater_svar(KONFLIKT, [], "Transaksjonen finnes allerede i databasen")

        try:
            transaksjon = self.database.execute(
                "INSERT INTO transaksjoner (pris, type, dato, beskrivelse) VALUES (?, ?, ?, ?) RETURNING *",
                (beløp, handling, dato, beskrivelse), fetchone=True, commit=True)

            return _formater_svar(OPPRETTET_NY, transaksjon, "suksess")
        except OperationalError as e:
            return _formater_svar(TABEL_FINNES_IKKE, [], f"Kunne ikke legge til transaksjon: {e}")


    def skriv_kategori(self, transaksjon_id, kategori_id):
        """Lage en refferanse mellom transaksjonen og kategorien"""
        if not er_helltall(transaksjon_id):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type int, fikk {transaksjon_id} av typen {type(transaksjon_id).__name__}")

        if not er_helltall(kategori_id):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type int, fikk {kategori_id} av typen {type(kategori_id).__name__}")

        try:
            transaksjon = self.database.execute("SELECT * FROM transaksjoner WHERE id = ?", (transaksjon_id,), fetchone=True)
            kategori = self.database.execute("SELECT * FROM kategorier WHERE id = ?", (kategori_id,), fetchone=True)

            if not transaksjon:
               return _formater_svar(UGYLDIG_INPUT, [], f"{transaksjon_id} er ikke en gyldig transaksjon")

            if not kategori:
                return _formater_svar(UGYLDIG_INPUT, [], f"{kategori_id} er ikke en gyldig kategori")

            self.database.execute("INSERT INTO kategori_tag (transaksjon_id, kategori_id) VALUES (?, ?)",
                                  (transaksjon_id, kategori_id),
                                  commit=True)

            return _formater_svar(OPPRETTET_NY, [], "suksess")

        except OperationalError as e:
            return _formater_svar(TABEL_FINNES_IKKE, [], f"Kunne ikke legge til kategori: {kategori_id}, feilmelding: {e}")


    def skriv_person(self, transaksjon_id, person_id) -> dict:
        """Lage en refferanse mellom transaksjonen og personen"""

        for ide in [transaksjon_id, person_id]:
            if not er_helltall(ide):
                return _formater_svar(UGYLDIG_INPUT, [],
                                          f"forventet type int, fikk {ide} av typen {type(ide).__name__}")
        try:

            transaksjon = self.database.execute("SELECT * FROM transaksjoner WHERE id = ?", (transaksjon_id,), fetchone=True)
            person = self.database.execute("SELECT * FROM personer WHERE id = ?", (person_id,), fetchone=True)

            if not transaksjon:
                return _formater_svar(UGYLDIG_INPUT, [], f"{transaksjon_id} er ikke en gyldig transaksjon")

            if not person:
                return _formater_svar(UGYLDIG_INPUT, [], f"{person_id} er ikke en gyldig person")

            self.database.execute("INSERT INTO person_tag (transaksjon_id, person_id) VALUES (?, ?)", (transaksjon_id, person_id),
                       commit=True)

            return _formater_svar(OPPRETTET_NY, [], "suksess")

        except OperationalError as e:
            return _formater_svar(TABEL_FINNES_IKKE, [], f"Kunne ikke legge til person: {person_id}, feilmelding: {e}")


    def skriv_transaksjon_med_alt(self, beløp: int, handling: str, dato: datetime, beskrivelse: str, kategorier: list[str] = None,
                        personer: list[str] = None) -> dict:

        validert = er_gyldig_transaksjon_input(beløp, handling, dato, beskrivelse)
        if validert.get("status") == UGYLDIG_INPUT:
            return _formater_svar(UGYLDIG_INPUT, [], validert.get("melding"))

        if not kategorier:
            kategorier = [] #Skakke ha en mutable list som default-parameter, men da er det en fallback

        if not personer:
            personer = []

        person_ider = []
        for person in personer:
            denne_person = self.personer.hent_på_navn(person)
            if denne_person.get("status") == IKKE_FUNNET:
                denne_person = self.personer.legg_til(person)

            person_ider.append(denne_person.get("innhold").get("id"))

        kategori_ider = []
        for kategori in kategorier:
            denne_kategorien = self.kategorier.hent_på_navn(kategori)
            if denne_kategorien.get("status") == IKKE_FUNNET:
                denne_kategorien = self.kategorier.legg_til(kategori)

            kategori_ider.append(denne_kategorien.get("innhold").get("id"))

        transaksjon = self.skriv(beløp, handling, dato, beskrivelse)
        if transaksjon.get("status") != OPPRETTET_NY:
            return _formater_svar(transaksjon.get("status"), [], transaksjon.get("melding"))

        for person_id in person_ider:
            self.skriv_person(transaksjon.get("innhold").get("id"), person_id)

        for kategori_id in kategori_ider:
            self.skriv_kategori(transaksjon.get("innhold").get("id"), kategori_id)

        return _formater_svar(OPPRETTET_NY, transaksjon.get("innhold"), "suksess")


    def hent_på_id(self, iden: int) -> dict:
        """status: int, innhold: {id, beløp, type, dato, beskrivelse}, message: str"""

        if not er_helltall(iden):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet type int, fikk {iden} av typen {type(iden).__name__}")

        transaksjon = self.database.execute("SELECT * FROM transaksjoner WHERE id = ?", (iden,), fetchone=True)

        if not transaksjon:
            return _formater_svar(IKKE_FUNNET, transaksjon, "Fant ingen transaksjoner")

        return _formater_svar(SUKSESS, transaksjon, "suksess")


    def hent_transaksjoner_på_pris(self, mengde, beløp) -> dict:
        """status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""

        if not er_helltall(beløp):
            return _formater_svar(UGYLDIG_INPUT, [], f"Forventet typen int, fikk verdien {beløp} av typen {type(beløp).__name__}")

        mengder = {
            "større enn": ">",
            "mindre enn": "<",
            "lik": "=",
            "større eller lik": ">=",
            "mindre eller lik": "<=",
            "ikke lik": "!="
        }

        if mengde in mengder.keys():
            tegn = mengder[mengde]

        elif mengde in list(mengder.values()):
            tegn = mengde

        else:
            return _formater_svar(UGYLDIG_INPUT, [], f"Fant ikke tegn {mengde}")

        transaksjoner = self.database.execute(f"SELECT * FROM transaksjoner WHERE pris {tegn} ?", (beløp,), fetchall=True)

        if not transaksjoner:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, transaksjoner, "Fant ingen transaksjoner")

        return _formater_svar(SUKSESS, transaksjoner, "suksess")


    def hent_transaksjoner_på_type(self, handling) -> dict:
        """ "innskud" eller "uttak".
        status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""
        if not er_gyldig_handling(handling):
            return _formater_svar(UGYLDIG_INPUT, [], f'Feil type handling. forventet "innskudd", "uttak", "utlegg" eller "tilbakebetaling" fikk "{handling}", av typen {type(handling).__name__}')

        transaksjoner = self.database.execute("SELECT * FROM transaksjoner WHERE type = ?", (handling,), fetchall=True)

        if not transaksjoner:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, [], f"fant ingen transaksjon av typen {handling}")
        
        return _formater_svar(SUKSESS, transaksjoner, "suksess")


    def hent_transaksjoner_mellom_datoer(self, start_dato: str, slutt_dato: str) -> dict:
        """status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""
        if not er_gyldig_dato(start_dato):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet dato med iso-format. fikk {start_dato} av typen {type(start_dato).__name__}")

        if not er_gyldig_dato(slutt_dato):
            return _formater_svar(UGYLDIG_INPUT, [], f"forventet dato med iso-format. fikk {slutt_dato} av typen {type(slutt_dato).__name__}")

        transaksjon = self.database.execute("SELECT * FROM transaksjoner WHERE dato BETWEEN ? AND ?", (start_dato, slutt_dato),
                                            fetchall=True)

        if not transaksjon:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, transaksjon, "Fant ingen transaksjoner")

        return _formater_svar(SUKSESS, transaksjon, "suksess")


    def hent_transaksjoner_på_dato(self, dato) -> dict:
        """status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""
        return self.hent_transaksjoner_mellom_datoer(dato, dato)  # Finne på en dato, er det samme som mellom på samme dato


    def hent_transaksjoner_på_beskrivelse(self, beskrivelse: str) -> dict:
        if not er_gyldig_tekst(beskrivelse):
            return _formater_svar(UGYLDIG_INPUT, [], f"Forventet beskrivelse som tekst, ikke {beskrivelse}")

        transaksjoner = self.database.execute("SELECT * FROM transaksjoner WHERE beskrivelse Like ?", (f"%{beskrivelse}%",), fetchall=True)

        return _formater_svar(SUKSESS, transaksjoner, "suksess")


    def hent_personer(self, transaksjon_id) -> dict:
        """status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""
        person_ider = self.database.execute("SELECT person_id FROM person_tag WHERE transaksjon_id = ?", (transaksjon_id,),
                                 fetchall=True)

        if not person_ider:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, [], f"Fant ingen personer på transaksjon: {transaksjon_id}")

        ider = []
        for person_id in person_ider:
            person = self.database.execute("SELECT * FROM personer WHERE id = ?", (person_id.get("person_id"),), fetchone=True)
            ider.append(person)

        return _formater_svar(SUKSESS, ider, "suksess")

    def hent_kategorier(self, transaksjon_id) -> dict:
        """status: int, innhold: [{id, beløp, type, dato, beskrivelse}], message: str"""
        kategori_ider = self.database.execute("SELECT kategori_id FROM kategori_tag WHERE transaksjon_id = ?", (transaksjon_id,),
                                   fetchall=True)

        if not kategori_ider:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, [], f"Fant ingen personer på transaksjon: {transaksjon_id}")

        ider = []
        for kategori_id in kategori_ider:
            kategori = self.database.execute("SELECT * FROM kategorier WHERE id = ?", (kategori_id.get("kategori_id"),),
                                  fetchone=True)
            ider.append(kategori)

        return _formater_svar(SUKSESS, ider, "suksess")


    def hent_transaksjon_med_alt(self, transaksjon_id) -> dict:

        transaksjon = self.hent_på_id(transaksjon_id)

        if transaksjon.get("status") == IKKE_FUNNET:
            return _formater_svar(IKKE_FUNNET, [], f"Transaksjons-id {transaksjon_id} finnes ikke")
        elif transaksjon.get("status") == UGYLDIG_INPUT:
            return _formater_svar(UGYLDIG_INPUT, [], transaksjon.get("melding"))

        personer: list = self.hent_personer(transaksjon.get("innhold").get("id")).get("innhold")
        kategorier: list = self.hent_kategorier(transaksjon.get("innhold").get("id")).get("innhold")

        alle_navn = []
        for person in personer:
            alle_navn.append(person.get("navn"))

        alle_kategorier = []
        for kategori in kategorier:
            alle_kategorier.append(kategori.get("navn"))

        transaksjon.get("innhold")["personer"] = personer
        transaksjon.get("innhold")["kategorier"] = kategorier

        return _formater_svar(SUKSESS, transaksjon.get("innhold"), "suksess")


    def finn_transaksjoner_med_info(self, transaksjon_innhold) -> dict:

        filtere = []
        filter_verdier = []

        if transaksjon_innhold.get("pris"):
            filtere.append("pris = ?")
            filter_verdier.append(transaksjon_innhold.get("pris"))
        if transaksjon_innhold.get("type"):
            filtere.append("type = ?")
            filter_verdier.append(transaksjon_innhold.get("type"))
        if transaksjon_innhold.get("dato"):
            filtere.append("dato = ?")
            filter_verdier.append(transaksjon_innhold.get("dato"))
        if transaksjon_innhold.get("beskrivelse"):
            filtere.append("beskrivelse = ?")
            filter_verdier.append(transaksjon_innhold.get("beskrivelse"))

        filter_teskt = " AND ".join(filtere)

        funnet_transaksjon = self.database.execute(f"SELECT * FROM transaksjoner WHERE {filter_teskt}", tuple(filter_verdier), fetchall=True)

        if not funnet_transaksjon:
            return _formater_svar(IKKE_FUNNET, [], f"Fant ingen transaksjoner med innholdet {transaksjon_innhold}")

        return _formater_svar(SUKSESS, funnet_transaksjon, "suksess")


    def oppdater_transaksjon(self, transaksjon_id, beløp, handling, dato, beskrivelse) -> dict:

        if not er_helltall(transaksjon_id):
            return _formater_svar(UGYLDIG_INPUT, [], f'Forventet transaksjon_id av type int, fikk {transaksjon_id} av typen {type(transaksjon_id).__name__}')

        validering = er_gyldig_transaksjon_input(beløp, handling, dato, beskrivelse)
        if validering.get("status") != SUKSESS_INGEN_INNHOLD:
            return _formater_svar(validering.get("status"), [], validering.get("melding"))


        transaksjon = self.database.execute(
            "UPDATE transaksjoner SET pris = ?, type = ?, dato = ?, beskrivelse = ? WHERE id = ? RETURNING *",
            (beløp, handling, dato, beskrivelse, transaksjon_id,), fetchone=True, commit=True)

        if not transaksjon:
            return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "Tomme celler. Kan være feil transaksjon_id")

        return _formater_svar(SUKSESS, transaksjon, "suksess")
    
    def _oppdater_tag(self, table, transaksjon_id, gammel_tag_id, ny_tag_id):

        if f"{table}_tag" not in hent_tables(self.database):
            return _formater_svar(IKKE_FUNNET, [], f"{table}_tag finnes ikke i databasen")

        if not er_helltall(transaksjon_id):
            return _formater_svar(UGYLDIG_INPUT, [],
                                  f'Forventet transaksjon_id av type int, fikk {transaksjon_id} av typen {type(transaksjon_id).__name__}')

        if not er_helltall(gammel_tag_id):
            return _formater_svar(UGYLDIG_INPUT, [],
                                  f'Forventet gammel_{table}_id av type int, fikk {gammel_tag_id} av typen {type(gammel_tag_id).__name__}')

        if not er_helltall(ny_tag_id):
            return _formater_svar(UGYLDIG_INPUT, [],
                                  f'Forventet ny_{table}_id av type int, fikk {ny_tag_id} av typen {type(ny_tag_id).__name__}')

        self.database.execute(f"UPDATE {table}_tag SET {table}_id = ? WHERE transaksjon_id = ? AND {table}_id = ? ",
                   (ny_tag_id, transaksjon_id, gammel_tag_id,), commit=True)

        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")


    def oppdater_kategori_tag(self, transaksjon_id, gammel_kategori_id, ny_kategori_id) -> dict:
        return self._oppdater_tag("kategori", transaksjon_id, gammel_kategori_id, ny_kategori_id)


    def oppdater_person_tag(self, transaksjon_id, gammel_person_id, ny_person_id) -> dict:
        return self._oppdater_tag("person", transaksjon_id, gammel_person_id, ny_person_id)


    def fjern_transaksjon(self, transaksjon_id) -> dict:
        """status: int, innhold: [], message: str"""
        self.database.execute("DELETE FROM transaksjoner WHERE id = ?", (transaksjon_id,), commit=True)
        self.database.execute("DELETE FROM kategori_tag WHERE transaksjon_id = ?", (transaksjon_id,), commit=True)
        self.database.execute("DELETE FROM person_tag WHERE transaksjon_id = ?", (transaksjon_id,), commit=True)
        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")


    def fjern_transaksjons_kategori(self, transaksjon_id, kategori_id) -> dict:
        self.database.execute("DELETE FROM kategori_tag WHERE transaksjon_id = ? AND kategori_id = ?",
                   (transaksjon_id, kategori_id,), commit=True)
        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")


    def fjern_transaksjons_person(self, transaksjon_id, person_id) -> dict:
        self.database.execute("DELETE FROM person_tag WHERE transaksjon_id = ? AND person_id = ?", (transaksjon_id, person_id,),
                   commit=True)
        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")


    def eksporter_csv_fil(self, transaksjoner : list[dict], filnavn: str) -> dict:    #Kan være både en liste med transaksjoner og transaksjon_ider, så lenge den inneholder {"id": id}, så skal det gå
        """
        [{"id": id, "type": type, "dato": dato, "beskrivelse": beskrivelse}, {"id": id, "type": type, "dato": dato, "beskrivelse": beskrivelse}, {"id": id, "type": type, "dato": dato, "beskrivelse": beskrivelse}]
        [{"id": id}, {"id": id}, {"id": id}, {"id": id}]
        """
        funnnet_transaksjoner = []
        for transaksjon in transaksjoner:
            ide = transaksjon.get("id")
            if ide is None:
                return _formater_svar(IKKE_FUNNET, [], f"Fant ikke id-en i transaksjon {transaksjon}")

            if not er_helltall(ide):
                return _formater_svar(UGYLDIG_INPUT, [], f"ID-en er ikke et heltall. fikk ID-en {ide}")

            transaksjon_info = self.hent_transaksjon_med_alt(ide)
            if transaksjon_info.get("status") == IKKE_FUNNET:
                return _formater_svar(IKKE_FUNNET, [], f"Fant ingen transaksjon med id: {ide} i databasen")

            innhold = transaksjon_info.get("innhold")
            personer = []
            for person in innhold.get("personer"):
                personer.append(person.get("navn"))

            kategorier = []
            for kategori in innhold.get("kategorier"):
                kategorier.append(kategori.get("navn"))

            innhold["kategorier"] = kategorier
            innhold["personer"] = personer
            innhold.pop("id")

            funnnet_transaksjoner.append(innhold)

        with open(filnavn, "w", newline="") as csvfil:
            felt = ["pris", "type", "dato", "beskrivelse", "kategorier", "personer"]
            skriver = csv.DictWriter(csvfil, fieldnames=felt, delimiter=";")

            skriver.writeheader()
            skriver.writerows(funnnet_transaksjoner)


        return _formater_svar(SUKSESS_INGEN_INNHOLD, [], "suksess")


    def _finnes_transaksjon_i_db(self, input_transaksjon: dict) -> bool:
        """Bruker ikke en ekte transaksjon, men en input_transaksjon. det brukeren har skrevet inn, uten ID-er"""
        input_transaksjon["kategorier"] = sorted(input_transaksjon.get("kategorier", []))
        input_transaksjon["personer"] = sorted(input_transaksjon.get("personer", []))

        like_transaksjoner = self.finn_transaksjoner_med_info(input_transaksjon)
        if like_transaksjoner.get("status") == IKKE_FUNNET:
            return False

        transaksjoner_med_like_kategorier = []
        for lik_transaksjon in like_transaksjoner.get("innhold"):
            kategorier_i_transaksjon = sorted(_filtrer_ut_tag_navn_fra_transaksjon(self.hent_kategorier(lik_transaksjon.get("id"))))
            if input_transaksjon.get("kategorier") == kategorier_i_transaksjon:
                transaksjoner_med_like_kategorier.append(lik_transaksjon)

        for lik_transaksjon in transaksjoner_med_like_kategorier:
            personer_i_transaksjon = sorted(_filtrer_ut_tag_navn_fra_transaksjon(self.hent_kategorier(lik_transaksjon.get("id"))))
            if input_transaksjon.get("kategorier") == personer_i_transaksjon:
                return True

        return False


    def importer_csv_fil(self, filnavn: str) -> dict:
        retur_melding = ""
        with (open(filnavn, "r", newline="") as csvfil):
            leser = csv.DictReader(csvfil, delimiter=";")
            i = 0
            for transaksjon in leser:
                i += 1
                transaksjon["pris"] = int(transaksjon.get("pris"))  # Konvertere fra Str til Int
                csv_kategorier = sorted(_str_til_str_list_parser(transaksjon.get("kategorier")))
                csv_personer = sorted( _str_til_str_list_parser(transaksjon.get("personer")))

                transaksjon["kategorier"] = csv_kategorier
                transaksjon["personer"] = csv_personer

                validert = er_hentet_transaksjon_innhold_gyldig(transaksjon)
                if validert.get("status") == UGYLDIG_INPUT:
                    return _formater_svar(validert.get("status"), [], validert.get("melding"))


                if self._finnes_transaksjon_i_db(transaksjon):
                    continue

                self.skriv_transaksjon_med_alt(
                    transaksjon.get("pris"),
                    transaksjon.get("type"),
                    transaksjon.get("dato"),
                    transaksjon.get("beskrivelse"),
                    csv_kategorier,
                    csv_personer
                )

                retur_melding += f"La til transaksjonen {transaksjon}\n"

        status = OPPRETTET_NY
        if retur_melding == "":
            retur_melding = "suksess"
            status = SUKSESS_INGEN_INNHOLD

        return _formater_svar(status, [], retur_melding)
