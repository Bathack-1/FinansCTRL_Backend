import datetime
from transaksjoner import Transaksjoner, Database
from personer import Personer
from kategorier import Kategorier

def dagen_idag():
    return datetime.datetime.now().date().isoformat()


db = Database("database.db")

personer = Personer(db)
kategorier = Kategorier(db)
transaksjoner = Transaksjoner(db, personer, kategorier)
