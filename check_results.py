import json
d = json.load(open('results.json'))
for mill in ['sm', 'lm']:
    print(f"\n{mill.upper()} Mill:")
    if d.get(mill) is None:
        print("  No results")
        continue
    for s in d[mill]['solutions']:
        o = s['objectives']
        print(f"  {s['label']:<30} SecCO={o.get('Sec CO cost (Rs)',0):>12,.0f}  "
              f"ThkCO={o.get('Thk CO cost (Rs)',0):>12,.0f}  "
              f"Late={o.get('Late (MT·days)',0):>10,.0f}  "
              f"StgMT={o.get('Storage (MT·days)',0):>8,.0f}  "
              f"StgD={o.get('Storage (days)',0):>6,.0f}")