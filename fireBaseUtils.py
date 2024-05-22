import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("assets/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://chess-6d839-default-rtdb.europe-west1.firebasedatabase.app/'
})

def check_username_in_documents(username):
    ref = db.reference('/')

    data = ref.get()

    for key, value in data.get('game_rooms', {}).get('matched_games', {}).items():
        if isinstance(value, dict) and ('player1' in value and value['player1'] == username) or ('player2' in value and value['player2'] == username):
            return True
    return False

def delete_document_by_name(name):
    if check_username_in_documents(name):
        ref = db.reference('/')

        ref.child('game_rooms/matched_games').child(name).delete()
        print(f"Document with name '{name}' deleted successfully.")
    else:
        print(f"No document found with username '{name}'.")

