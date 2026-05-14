import json

d = json.load(open('changeover_data.json'))

print("SM Thickness CO costs (sample):")
for e in d['thk_co_cost_SM'][:15]:
    print(f"  {e['from']} -> {e['to']}: {e['cost']:,.0f} Rs")

print(f"\nTotal SM entries: {len(d['thk_co_cost_SM'])}")
print(f"Min cost: {min(e['cost'] for e in d['thk_co_cost_SM']):,.0f}")
print(f"Max cost: {max(e['cost'] for e in d['thk_co_cost_SM']):,.0f}")