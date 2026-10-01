import json, re, sys

import os
slides_path = sys.argv[1] if len(sys.argv) > 1 else 'slides.json'
d = json.load(open(slides_path))
# column.txt: second argument, else next to the slides file, else the working directory
col_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(slides_path)), 'column.txt')
if not os.path.exists(col_path):
    col_path = 'column.txt'
col = open(col_path).read()
col_norm = col.replace('’', "'").replace('“', '"').replace('”', '"')

def slide_text(s):
    parts = []
    for k in ('lines', 'items'):
        parts += s.get(k, [])
    for k in ('headline', 'deck', 'quote', 'lead', 'text', 'tail', 'big', 'question', 'footer'):
        if s.get(k):
            parts.append(s[k])
    return ' '.join(parts).replace('[[', '').replace(']]', '')

BANNED = """juncture delve revolutionize game-changing cusp hurdles bustling harnessing demystify
insurmountable new era poised unravel entanglement unprecedented eerie connection unliving beacon
unleash enrich multifaceted elevate supercharge unlock elegant ever-evolving pride meticulously
grappling weighing architect adventure journey embark navigate dazzle tapestry testament in conclusion
sharp sharper sharpest stuck struck landscape ecosystem seismic pivotal robust leverage dive in
double down stark the takeaway let that sink in big if true the real question the real issue
the real problem the real opportunity here's why that matters""".split('\n')
banned = []
for line in BANNED:
    banned += [w.strip() for w in re.split(r'\s{2,}|(?<=[a-z])\s(?=[a-z]+\s)', line) if w.strip()]
# simpler: explicit list
banned = ['juncture','delve','revolutionize','game-changing','cusp','hurdles','bustling','harnessing',
 'demystify','insurmountable','new era','poised','unravel','entanglement','unprecedented','eerie',
 'connection','unliving','beacon','unleash','enrich','multifaceted','elevate','supercharge','unlock',
 'elegant','ever-evolving','pride','meticulously','grappling','weighing','architect','adventure',
 'journey','embark','navigate','dazzle','tapestry','testament','in conclusion','sharp','stuck','struck',
 'landscape','ecosystem','seismic','pivotal','robust','leverage','dive in','double down','stark',
 'the takeaway','let that sink in','big if true','the real question','the real issue','the real problem',
 'the real opportunity',"here's why that matters"]

names = ['Nursing Times','Skift','Ask Skift','Rafat Ali','Lenny','Texas Tribune','Agência Mural','São Paulo',
 'NLW','AI Daily Brief','Claude','ChatGPT','Politico','WhatsApp','Pete Pachal','UNC','North Carolina']

ok = True
for i, s in enumerate(d['slides'], 1):
    t = slide_text(s)
    tn = t.replace('’', "'").replace('“', '"').replace('”', '"')
    words = len(re.findall(r"[\w'%$,.-]+", tn))
    print(f"\n--- Slide {i} ({s['type']}, {words} words)")
    # numbers
    for num in re.findall(r"\$?\d[\d,.]*%?", tn):
        n = num.rstrip('.,')
        found = n in col_norm
        print(f"  number {n!r}: {'OK' if found else 'NOT IN COLUMN'}")
        ok &= found
    # names
    for nm in names:
        if nm in t:
            found = nm in col
            print(f"  name {nm!r}: {'OK' if found else 'NOT IN COLUMN'}")
            ok &= found
    # banned
    low = ' ' + tn.lower() + ' '
    for b in banned:
        if re.search(r'\b' + re.escape(b) + r'\b', low):
            print(f"  BANNED WORD: {b}")
            ok = False
    if '—' in t or '–' in t:
        print('  EM/EN DASH PRESENT'); ok = False
    if '!' in t:
        print('  EXCLAMATION PRESENT'); ok = False
    if re.search(r"\b(it's|it is|this isn't|this is not|isn't|is not) (about )?\w[^.]*, (it's|it is) ", low):
        print("  POSSIBLE 'not X, it's Y' construction");
    for sent in re.split(r'(?<=[.?!:])\s+', tn):
        wc = len(sent.split())
        if wc > 25:
            print(f"  long sentence ({wc} words): {sent[:60]}...")

# verbatim quote check
for s_ in d['slides']:
    if s_['type'] == 'quote':
        qn = s_['quote'].replace('\u201c','').replace('\u201d','').replace('\u2019',"'").rstrip('.,;:!?')
        hit = qn in col_norm
        print('\nQuote verbatim in column:', repr(qn), hit); ok &= hit

# caption checks
for ch, cap in d['captions'].items():
    low = cap.lower()
    for b in banned:
        if re.search(r'\b' + re.escape(b) + r'\b', low):
            print(f"caption {ch} BANNED WORD: {b}"); ok = False
    tags = len(re.findall(r'#\w+', cap))
    print(f"caption {ch}: {len(cap.split())} words, hashtags={tags}")

print('\nALL CHECKS PASS' if ok else '\nCHECK FAILURES ABOVE')
