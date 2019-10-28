_priority_to_group = {
    '': 'Event',
    'ASM': 'ASM',
    # 'ballista': 'Trap', <-- considerable fixes available, and it's short.
    # 'battleData': 'BattleData', <-- handle these manually.
    'coordList': 'CoordList', # ???
    # 'low': None, <-- system types.
    'main': 'EventTrigger',
    'moveManual': 'EventMovement',
    # 'pointer': None, <-- system types.
    'reinforcementData': 'EventReinforcements', # FE8 only.
    'shopList': 'EventItems',
    'unit': 'EventUnits'
}


def lookup(name):
    return _priority_to_group.get(name, None)
