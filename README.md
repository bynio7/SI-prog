# Sztuczna inteligencja - zadania programistyczne

### zadanie 15 c) z listy 5
Prover9 miał olbrzymie problemy z wyprowadzeniem c + d = c, nawet pomimo użycia podpowiedzi w postaci klauzul z dowodu McCune'a

Wszelkie współczesne pomoce również okazały się niewystarczające

Postanowiłem odtworzyć dowód McCune'a jego programem EQP

Zależności: 
```
apt install build-essential gcc make libc6-dev git
```

Źródło programu: https://github.com/theoremprover-museum/EQP
```
git clone https://github.com/theoremprover-museum/EQP
```

Moje środowisko: Linux Mint 22.2 (Ubuntu)

Procesor Ryzen 5 7500f (taktowanie ~5GHz, L3: 32MB)

Prędkość RAM 4800 MT/s

Zbudowałem program z kodu znajdującego się w katalogu eqp-09e

korekta Makefile dla gcc 10+:
```
sed -i 's/^CFLAGS = -O \$(DFLAGS)/CFLAGS = -O $(DFLAGS) -fcommon/' Makefile
```

następnie
`make eqp`

w katalogu examples/robbins/ znajduje się plik eqp-lemma3.in
`./eqp09e < examples/robbins/eqp-lemma3.in`

Dowód od zera zajął około 37 minut (niestety potem program się zapętlił, bo max_proofs był ustawiony na 500)

Wykorzystałem także wcześniej zebrane klauzule do szybszego dowodu: dowod3.in
`./eqp09e < dowod3.in`

Oczywiście po udowodnieniu istnienia elementu neutralnego dodawania bardzo łatwo jest wyprowadzić równanie Huntingtona w proverze, nawet bez hintów (~20 sekund):

```
% Prover9
assign(max_weight, 35).
assign(max_seconds, 600).

formulas(assumptions).
  x + y = y + x.
  (x + y) + z = x + (y + z).
  n(n(n(y) + x) + n(x + y)) = x.
  c + d = c.
end_of_list.

formulas(goals).
  n(n(x) + y) + n(n(x) + n(y)) = x.
end_of_list.
```

Z czego wynika, że algebra Robbinsa jest de facto algebrą Boole'a. (Na podstawie zadania 14 z listy 5)

### metoda rezolucji dla predykatów (logika pierwszego rzędu) (PYTHON 3.12.3)

skrypt w pythonie `rezolucja.py`

brak zewnętrznych bibliotek, zbiór klauzul podaje się jako plik tekstowy (zgodnie z wymaganiami)
```
python3 rezolucja.py
```

W repozytorium są również różne przykłady, również te pokazujące ograniczenia programu np.:
```
python3 rezolucja.py rez_przyklady/zly_przyklad2.txt
```
