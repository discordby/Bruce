import pyrebase, json

firebase_config = {
    "apiKey": "1:1062093995209:web:741493660fc266e0e0e118",
    "authDomain": "alert-result-315817.firebaseapp.com",
    "databaseURL": "https://alert-result-315817-default-rtdb.europe-west1.firebasedatabase.app",
    "storageBucket": "alert-result-315817.appspot.com",
    "serviceAccount": "serviceAccountKey.json"}
db = pyrebase.initialize_app(firebase_config).database()


now = 1626861208
xdd = {
    "GameStats": {
        "lastUpdate": {
            "R6Sv8": now,
        },
        "updateRequests": {
            "R6S": now,
        },
        "IDs": {
            210471447649320970: {
                "discordUsername": "ExampleUser#6969",
                "ubiID": "eXaMPLe7-uBIs-oFT6-USer-ID9a05926e77"
            }
        }
    },
    "serverTotals": {
        "levels": 0,
        "messages": 0,
        "reactionPoints": 0,
        "users": 0,
        "voice": 0,
        "xp": 0
    }
}

db.set(xdd)
