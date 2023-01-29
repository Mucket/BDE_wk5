list_of_dicts = [
    {'name': 'Anna', 'age': 9},
    {'name': 'Bobs', 'age': 2},
    {'name': 'Jack', 'age': 5}
]

print(list_of_dicts)

for item in list_of_dicts:
    print(item)

print(min(item['age'] for item in list_of_dicts))