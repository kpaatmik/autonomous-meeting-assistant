from app.services.persistence import get_persistence

p = get_persistence()

p.save_segment("1", {
    "speaker": "Rahul",
    "start": 0,
    "end": 5,
    "text": "The project deadline is next Friday."
})

p.save_segment("1", {
    "speaker": "Anu",
    "start": 6,
    "end": 10,
    "text": "Testing must be completed before Wednesday."
})

p.save_segment("1", {
    "speaker": "Manager",
    "start": 11,
    "end": 15,
    "text": "Client demo will happen next week."
})

print("Inserted")
