"""
Metoda rezolucji dla logiki pierwszego rzedu.
Tylko biblioteka standardowa: re, itertools, dataclasses. Zero zaleznosci.

Wejscie w postaci klauzulowej. Aby udowodnic KB |= phi,
podaj klauzule KB razem z klauzulami ~phi; wyprowadzenie klauzuli pustej []
oznacza sprzecznosc zbioru, czyli KB |= phi.

Skladnia literalu / klauzuli (parser `clause`):
    Pred(t1, ..., tn)         literal pozytywny      np. Human(socrates)
    ~Pred(...) lub -Pred(...) literal negatywny      np. ~Mortal(x)
    a | b | c                 klauzula = alternatywa np. ~Human(x) | Mortal(x)
Termy:
    zmienna  : nazwa pasujaca do [uvwxyz][0-9]*  (konwencja konca alfabetu)
    stala    : inna nazwa bez argumentow         np. socrates, a, 0
    funkcja  : nazwa zastosowana do termow       np. f(x), succ(succ(0))
    predykat : najbardziej zewnetrzny symbol literalu
# zmienna = [uvwxyz]\\d*. trzeba rozszerzyc VAR_RE dla innych nazw.

Wczytywanie z pliku:
    - jedna klauzula na linie,
    - puste linie sa pomijane,
    - komentarze zaczynaja sie od '#' (dzialaja tez w linii)

Uzycie:
    # z linii polecen (wygodne wprowadzanie z pliku)
    python3 rezolucja.py klauzule.txt      # dowodzi klauzul z pliku
    python3 rezolucja.py                    # samokontrola + przyklad wbudowany

Przykladowy plik klauzul (KB + zanegowany cel ~phi):
    # Human(socrates), forall x Human(x)->Mortal(x)  |-  Mortal(socrates)
    Human(socrates)
    ~Human(x) | Mortal(x)
    ~Mortal(socrates)        # zanegowany cel
"""

import re
import itertools
from dataclasses import dataclass

# ---- termy ----
# zmienna  -> Var(name)
# reszta (stala / aplikacja funkcji / atom) -> krotka (symbol, *args)
# literal  -> (sign: bool, atom: krotka)        sign True = pozytywny
# klauzula -> frozenset literalow; pusty frozenset = []

@dataclass(frozen=True)
class Var:
    name: str

VAR_RE = re.compile(r'[uvwxyz]\d*$')

def is_var(t):
    return isinstance(t, Var)

# ---- parsowanie ----

def _tokens(s):
    return re.findall(r'\w+|[(),|~-]', s)   # \w obejmuje cyfry -> stale typu 0, 42

def _term(toks):
    name = toks.pop(0)
    if toks and toks[0] == '(':
        toks.pop(0)
        args = [_term(toks)]
        while toks[0] == ',':
            toks.pop(0)
            args.append(_term(toks))
        toks.pop(0)  # ')'
        return (name, *args)
    return Var(name) if VAR_RE.match(name) else (name,)

def _literal(toks):
    sign = True
    if toks and toks[0] in ('~', '-'):
        sign = False
        toks.pop(0)
    return (sign, _term(toks))

def clause(s):
    """Parsuje 'a | b | c' do klauzuli (frozenset)."""
    toks = _tokens(s)
    try:
        lits = [_literal(toks)]
        while toks and toks[0] == '|':
            toks.pop(0)
            lits.append(_literal(toks))
    except IndexError:
        raise ValueError(f"niepoprawna skladnia klauzuli: {s!r}") from None
    if toks:                                    # np. niezbalansowane nawiasy / smieci
        raise ValueError(f"nadmiarowe tokeny w {s!r}: {toks}")
    return frozenset(lits)

def load(path):
    """Wczytaj klauzule z pliku: jedna klauzula na linie.
    Puste linie i komentarze (od '#') sa pomijane. Zwraca liste klauzul
    gotowa do podania do prove(). Niepoprawna linia -> ValueError z numerem."""
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.split("#", 1)[0].strip()   # '#' nie wystepuje w klauzuli
            if line:
                try:
                    out.append(clause(line))
                except ValueError as e:
                    raise ValueError(f"{path}, linia {n}: {e}") from None
    return out

# ---- unifikacja ----

def walk(t, s):
    while is_var(t) and t in s:
        t = s[t]
    return t

def occurs(v, t, s):
    t = walk(t, s)
    if t == v:
        return True
    return isinstance(t, tuple) and any(occurs(v, a, s) for a in t[1:])

def unify(x, y, s):
    if s is None:
        return None
    x, y = walk(x, s), walk(y, s)
    if x == y:
        return s
    if is_var(x):
        return None if occurs(x, y, s) else {**s, x: y}
    if is_var(y):
        return None if occurs(y, x, s) else {**s, y: x}
    if isinstance(x, tuple) and isinstance(y, tuple) and x[0] == y[0] and len(x) == len(y):
        for a, b in zip(x[1:], y[1:]):
            s = unify(a, b, s)
            if s is None:
                return None
        return s
    return None

def apply_sub(t, s):
    t = walk(t, s)
    if isinstance(t, tuple):
        return (t[0], *(apply_sub(a, s) for a in t[1:]))
    return t

# ---- reguly wnioskowania ----

_fresh = itertools.count()

def rename(c):
    """Standaryzacja klauzuli: kazdej zmiennej nadaj globalnie swieza nazwe."""
    m = {}
    def rt(t):
        if is_var(t):
            if t not in m:
                m[t] = Var(f"{t.name}@{next(_fresh)}")
            return m[t]
        if isinstance(t, tuple):
            return (t[0], *(rt(a) for a in t[1:]))
        return t
    return frozenset((sg, rt(a)) for sg, a in c)

def resolve(c1, c2):
    """Wszystkie rezolwenty binarne c1 i c2 (c2 standaryzowana wzgl. c1)."""
    c2 = rename(c2)
    out = []
    for (s1, a1) in c1:
        for (s2, a2) in c2:
            if s1 != s2 and a1[0] == a2[0]:          # przeciwne, ten sam predykat
                mgu = unify(a1, a2, {})
                if mgu is not None:
                    rest = (c1 - {(s1, a1)}) | (c2 - {(s2, a2)})
                    out.append(frozenset((s, apply_sub(a, mgu)) for (s, a) in rest))
    return out

def factors(c):
    """Sklejenie dwoch literalow tego samego znaku, ktore sie unifikuja
    (potrzebne dla zupelnosci refutacyjnej)."""
    out = []
    lits = list(c)
    for i in range(len(lits)):
        for j in range(i + 1, len(lits)):
            (s1, a1), (s2, a2) = lits[i], lits[j]
            if s1 == s2 and a1[0] == a2[0]:
                mgu = unify(a1, a2, {})
                if mgu is not None:
                    out.append(frozenset((s, apply_sub(a, mgu)) for (s, a) in c))
    return out

def is_tautology(c):
    pos = {a for (s, a) in c if s}
    neg = {a for (s, a) in c if not s}
    return bool(pos & neg)

# ---- petla glowna ----

EMPTY = frozenset()

def prove(clauses, max_steps=100000):
    """
    Probuje wyprowadzic [] ze zbioru `clauses` (kazda to frozenset z `clause`).
    Zwraca dowod (lista (n, str_klauzuli, uzasadnienie)) gdy sprzeczny,
    False gdy zbior sie nasyca (brak dowodu), None gdy przekroczono max_steps.
    """
    just, order = {}, []
    def reg(c, j):
        if c not in just:
            just[c] = j
            order.append(c)

    queue = []
    for c in clauses:
        if not is_tautology(c):
            reg(c, ('input',))
            queue.append(c)
    if EMPTY in just:
        return _proof(just, order)

    kept, steps = [], 0
    while queue:
        if steps >= max_steps:
            return None
        given = queue.pop(0)
        derived = [(r, ('factor', given)) for r in factors(given)]
        for k in kept + [given]:                      # rezolucja z kept + sobą
            derived += [(r, ('resolve', given, k)) for r in resolve(given, k)]
        kept.append(given)
        for r, j in derived:
            steps += 1
            if is_tautology(r) or r in just:
                continue
            reg(r, j)
            if r == EMPTY:
                return _proof(just, order)
            queue.append(r)
    return False
# Deduplikacja tylko skladniowa (warianty alfa nie sa scalane), brak subsumpcji
# Problemy nierozstrzygalne sa ograniczone przez max_steps -> None.

# ---- ladne wypisywanie ----

def term_str(t):
    if is_var(t):
        return t.name
    return t[0] if len(t) == 1 else f"{t[0]}({', '.join(map(term_str, t[1:]))})"

def lit_str(l):
    s, a = l
    return ('' if s else '¬') + term_str(a)

def clause_str(c):
    return '[]' if not c else ' ∨ '.join(sorted(lit_str(l) for l in c))

def _proof(just, order):
    need, stack = set(), [EMPTY]
    while stack:
        c = stack.pop()
        if c in need:
            continue
        need.add(c)
        j = just[c]
        if j[0] in ('resolve', 'factor'):
            stack += list(j[1:])
    seq = [c for c in order if c in need]
    idx = {c: i + 1 for i, c in enumerate(seq)}
    rows = []
    for c in seq:
        j = just[c]
        if j[0] == 'input':
            why = 'wejscie'
        elif j[0] == 'factor':
            why = f'faktor z {idx[j[1]]}'
        else:
            why = f'rezolucja({idx[j[1]]}, {idx[j[2]]})'
        rows.append((idx[c], clause_str(c), why))
    return rows

def print_proof(result):
    if result is None:
        print("NIEROZSTRZYGNIETE (osiagnieto limit krokow)"); return
    if result is False:
        print("NIEDOWODLIWE (zbior klauzul jest spelnialny / nasycony)"); return
    print("UDOWODNIONO — znaleziono refutacje:")
    w = max(len(cs) for _, cs, _ in result)
    for n, cs, why in result:
        print(f"  {n:>3}.  {cs:<{w}}   [{why}]")

# ---- samokontrola ----------------------------------------------------------

def _demo():
    # unifikacja
    assert unify(('P', Var('x')), ('P', ('a',)), {}) is not None   # P(x) ~ P(a)
    assert unify(Var('x'), ('f', Var('x')), {}) is None            # occurs-check
    assert unify(('P', ('a',)), ('Q', ('a',)), {}) is None         # rozne predykaty

    # 1) sylogizm: Human(socrates), forall x Human(x)->Mortal(x) |- Mortal(socrates)
    kb = [clause("Human(socrates)"),
          clause("~Human(x) | Mortal(x)"),
          clause("~Mortal(socrates)")]            # zanegowany cel
    assert prove(kb)

    # 2) lancuch z funkcja: forall x P(x)->P(f(x)), P(a) |- P(f(f(a)))
    kb2 = [clause("~P(x) | P(f(x))"),
           clause("P(a)"),
           clause("~P(f(f(a)))")]                 # zanegowany cel
    assert prove(kb2)

    # 3) zbior spelnialny NIE moze byc udowodniony (brak falszywych trafien)
    assert prove([clause("P(a)"), clause("~Q(a)")]) is False

    # 4) stala liczbowa + funkcja (Peano): Num(0), forall x Num(x)->Num(s(x)) |- Num(s(s(0)))
    peano = [clause("Num(0)"), clause("~Num(x) | Num(s(x))"), clause("~Num(s(s(0)))")]
    assert prove(peano)

    # 5) niepoprawne wejscie daje czytelny ValueError, nie IndexError
    for bad in ("Num(", "Num(0))", "P(a) b"):
        try:
            clause(bad); raise AssertionError(f"oczekiwano bledu dla {bad!r}")
        except ValueError:
            pass

    # 6) wczytywanie z pliku: komentarze + puste linie + dowod
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# baza wiedzy\n"
                "Human(socrates)   # stala\n"
                "\n"
                "~Human(x) | Mortal(x)\n"
                "~Mortal(socrates)  # zanegowany cel\n")
    loaded = load(path)
    os.remove(path)
    assert len(loaded) == 3 and prove(loaded)
    print("samokontrola OK\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:                       # python3 rezolucja.py plik.txt
        print_proof(prove(load(sys.argv[1])))
    else:
        _demo()
        kb = [clause("Human(socrates)"),
              clause("~Human(x) | Mortal(x)"),
              clause("~Mortal(socrates)")]
        print("Przyklad: KB = { Human(socrates), forall x Human(x)->Mortal(x) }, cel = Mortal(socrates)")
        print("(cel zanegowany i dodany jako ~Mortal(socrates))\n")
        print_proof(prove(kb))
