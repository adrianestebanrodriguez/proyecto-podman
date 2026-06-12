from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

creds = Credentials.from_authorized_user_file('token.json')
service = build('calendar', 'v3', credentials=creds)

# Listamos TODOS los calendarios que tienes
print("--- Tus calendarios disponibles ---")
calendar_list = service.calendarList().list().execute()
for cal in calendar_list.get('items', []):
    print(f"ID: {cal['id']} | Resumen: {cal['summary']}")

print("\n--- Buscando eventos en el calendario 'primary' ---")
# Buscamos eventos sin límite de fecha para estar seguros
events_result = service.events().list(calendarId='primary', singleEvents=True).execute()
events = events_result.get('items', [])

if not events:
    print("No se encontraron eventos en el calendario 'primary'.")
else:
    for event in events:
        print(f"- {event.get('summary', 'Sin nombre')} | Inicio: {event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))}")