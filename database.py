import sqlite3

class Database:
    def __init__(self, database):
        self.database = database

    def _koble_til(self):
        conn = sqlite3.connect(self.database)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        conn = self._koble_til()
        peker = conn.cursor()

        try:
            resultat = peker.execute(query, params)
            if fetchone:
                rad = peker.fetchone()
                resultat = dict(rad) if rad else None
            elif fetchall:
                rader = peker.fetchall()
                resultat = [dict(rad) for rad in rader]

            if commit:
                conn.commit()

            return resultat
        finally:
            conn.close()
