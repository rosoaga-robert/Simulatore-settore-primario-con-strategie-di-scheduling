"""
PW-15 - Progetto di Laurea Triennale in Informatica (L-31)
Modellazione e simulazione dei processi produttivi nel settore primario: confronto tra strategie di scheduling sequenziale e concorrente.
"""

import random

# Parametri operativi aziendali
ORE_GIORNALIERE = 8.0           # Ore di lavoro giornaliere
TEMPO_SETUP_BASE = 6.0         # Ore di allestimento/lavaggio/sanificazione standard
TEMPO_SETUP_RIDOTTO = 2.0      # Ore con procedura ottimizzata (SMED)
SEED_CASUALE = 2              # Impostare a None per prove casuali


def check_parametri_globali():
    """
        Verifica la coerenza fisica dei parametri di configurazione del simulatore.
        Input: Nessuno (legge le costanti globali).
        Output: Nessuno.
        Solleva: ValueError se ORE_GIORNALIERE, TEMPO_SETUP_BASE o TEMPO_SETUP_RIDOTTO violano i vincoli fisici.
    """
    if ORE_GIORNALIERE <= 0:
        raise ValueError("Le ore lavorative giornaliere devono essere strettamente positive.")
    if TEMPO_SETUP_BASE < 0 or TEMPO_SETUP_RIDOTTO < 0:
        raise ValueError("I tempi di setup non possono essere negativi.")
    if TEMPO_SETUP_RIDOTTO > TEMPO_SETUP_BASE:
        raise ValueError("Il setup ottimizzato non può richiedere più tempo del setup standard.")


class Prodotto:
    """
        Rappresenta una coltura o produzione del catalogo con i relativi vincoli operativi.
        Input: Parametri identificativi(nome, comparto), vincoli tecnici (ore/unità, cap_max/giorno) e intervalli (superficie, resa).
        Output: Istanza validata della classe Prodotto.
        Solleva: ValueError per stringhe vuote, valori negativi o intervalli invertiti.
    """
    def __init__(self, nome, comparto, unita, risorsa, ore_unitarie, cap_max_giorno, sup_min, sup_max, resa_min, resa_max):

        campi_testo = {"nome": nome, "comparto": comparto, "unità": unita, "risorsa": risorsa}
        for campo, valore in campi_testo.items():
            if not isinstance(valore, str) or not valore.strip():
                raise ValueError(f"Il campo '{campo}' non può essere vuoto o non valido")

        if sup_min <= 0 or sup_max < sup_min:
            raise ValueError(f"Intervallo superficie non valido per {nome}")
        if resa_min <= 0 or resa_max < resa_min:
            raise ValueError(f"Intervallo resa non valido per {nome}")
        if ore_unitarie <= 0 or cap_max_giorno <= 0:
            raise ValueError(f"Tempi o capacità devono essere strettamente positivi per {nome}")

        self.nome = nome.strip()
        self.comparto = comparto.strip()
        self.unita = unita.strip()
        self.risorsa = risorsa.strip()
        self.ore_unitarie = ore_unitarie
        self.cap_max_giorno = cap_max_giorno
        self.sup_min = sup_min
        self.sup_max = sup_max
        self.resa_min = resa_min
        self.resa_max = resa_max


def carica_configurazione():
    """
        Inizializza l'elenco dei prodotti aziendali verificando l'assenza di duplicati.
        Input: Nessuno.
        Output: list[Prodotto] contenente le colture e gli allevamenti monitorati.
        Solleva: ValueError in presenza di nomi prodotto duplicati.
    """
    catalogo = [
        Prodotto("Olive da Olio", "Olivicolo", "kg", "Trattore con Scuotitore", 0.006, 1000.0, 2.0, 10.0, 2000.0, 5000.0),
        Prodotto("Nocciole", "Frutticolo", "kg", "Trattore con Scuotitore", 0.008, 800.0, 2.0, 5.0, 1000.0, 3000.0),
        Prodotto("Grano Duro", "Cerealicolo", "kg", "Mietitrebbiatrice", 0.0015, 5000.0, 8.0, 20.0, 2000.0, 7000.0),
        Prodotto("Latte Vaccino", "Zootecnico", "litri", "Impianto Mungitura", 0.003, 2200.0, 8.0, 15.0, 500.0, 750.0)
    ]

    nomi = [prodotto.nome for prodotto in catalogo]
    if len(nomi) != len(set(nomi)):
        raise ValueError("Sono presenti prodotti duplicati nel catalogo.")

    return catalogo


def simula_lotti(catalogo):
    """
        Genera stocasticamente i volumi dei lotti e ne calcola la durata applicando il vincolo doppio.
        Input: catalogo (list[Prodotto]) - Lista delle configurazioni dei prodotti.
        Output: list[dict] - Dati quantitativi e fabbisogni temporali (ore, giorni) per ogni lotto.
        Solleva: ValueError se il catalogo in ingresso è vuoto.
    """
    if not catalogo:
        raise ValueError("Il catalogo dei prodotti non può essere vuoto.")

    lotti = []
    for prodotto in catalogo:
        ettari = round(random.uniform(prodotto.sup_min, prodotto.sup_max), 2)
        resa = round(random.uniform(prodotto.resa_min, prodotto.resa_max), 2)
        quantita_totale = round(ettari * resa, 2)

        # Calcolo dei tempi con vincolo doppio
        ore_teoriche = quantita_totale * prodotto.ore_unitarie
        giorni_limite = quantita_totale / prodotto.cap_max_giorno
        giorni_reali = max(ore_teoriche / ORE_GIORNALIERE, giorni_limite)
        ore_totali = round(giorni_reali * ORE_GIORNALIERE, 2)

        lotti.append({
            "nome": prodotto.nome,
            "risorsa": prodotto.risorsa,
            "unita": prodotto.unita,
            "ettari": ettari,
            "quantita": quantita_totale,
            "ore": ore_totali,
            "giorni": round(giorni_reali, 1)
        })
    return lotti


def calcola_strategie(lotti):
    """
        Confronta tre strategie di scheduling (Seriale, Parallela, Parallela SPT/SMED) e individua il collo di bottiglia.
        Input: lotti (list[dict]) - Lotti generati dalla simulazione con relativi tempi.
        Output: dict - Indicatori di performance: ore totali per strategia, carichi per risorsa, sequenze SPT, primo output disponibile e bottleneck.
        Solleva: ValueError se la lista dei lotti è vuota.
    """
    if not lotti:
        raise ValueError("Impossibile calcolare strategie su una lista lotti vuota.")

    # Raggruppamento per macchinario
    mappa_risorse = {}
    for lotto in lotti:
        risorsa = lotto["risorsa"]
        if risorsa not in mappa_risorse:
            mappa_risorse[risorsa] = []
        mappa_risorse[risorsa].append(lotto)

    # Calcolo Sequenziale: somma di tutte le lavorazioni + setup tra cambi
    setup_totali_sequenziale = 0
    for risorsa in mappa_risorse:
        num_prodotti = len(mappa_risorse[risorsa])
        if num_prodotti > 1:
            setup_totali_sequenziale += (num_prodotti - 1) * TEMPO_SETUP_BASE

    ore_seq1 = sum(lotto["ore"] for lotto in lotti) + setup_totali_sequenziale

    # Calcolo Parallelo Standard
    carichi_seq2 = {}
    for risorsa, lista_lotti in mappa_risorse.items():
        somma_ore = sum(lotto["ore"] for lotto in lista_lotti)
        setup = (len(lista_lotti) - 1) * TEMPO_SETUP_BASE
        carichi_seq2[risorsa] = round(somma_ore + setup, 2)

    ore_seq2 = max(carichi_seq2.values()) if carichi_seq2 else 0.0

    # Calcolo Parallelo Ottimizzato (con regola Shortest Processing Time sui lotti condivisi)
    carichi_seq3 = {}
    ordine_lavorazioni = {}
    primo_lotto_liberato = {}

    for risorsa, lista_lotti in mappa_risorse.items():
        if len(lista_lotti) > 1:
            # Ordinamento con Shortest Processing Time su risorse condivise
            lista_spt = sorted(lista_lotti, key=lambda lotto: lotto["ore"])
            ordine_lavorazioni[risorsa] = " -> ".join(lotto["nome"] for lotto in lista_spt)
            primo_lotto_liberato[risorsa] = f"{lista_spt[0]['nome']} ({lista_spt[0]['ore']}h)"

            somma_ore = sum(lotto["ore"] for lotto in lista_spt)
            setup = (len(lista_spt) - 1) * TEMPO_SETUP_RIDOTTO
            carichi_seq3[risorsa] = round(somma_ore + setup, 2)
        else:
            # Risorsa dedicata (un solo prodotto associato)
            lotto_singolo = lista_lotti[0]
            ordine_lavorazioni[risorsa] = lotto_singolo["nome"]
            primo_lotto_liberato[risorsa] = f"{lotto_singolo['nome']} ({lotto_singolo['ore']}h)"
            carichi_seq3[risorsa] = round(lotto_singolo["ore"], 2)

    ore_seq3 = max(carichi_seq3.values()) if carichi_seq3 else 0.0

    # Individuazione dinamica del collo di bottiglia
    bottleneck = max(carichi_seq3, key=carichi_seq3.get) if carichi_seq3 else "Nessuna risorsa"

    return {
        "ore_seq1": ore_seq1,
        "ore_seq2": ore_seq2,
        "ore_seq3": ore_seq3,
        "carichi": carichi_seq3,
        "ordini": ordine_lavorazioni,
        "primi_output": primo_lotto_liberato,
        "bottleneck": bottleneck,
        "risorse_condivise": [risorsa for risorsa, lista in mappa_risorse.items() if len(lista) > 1]
    }


def stampa_report(lotti, risultati):
    """
        Formatta e visualizza a video il report decisionale per il management aziendale.
        Input: lotti (list[dict]) - Dati dei lotti; risultati (dict) - Metriche di scheduling calcolate.
        Output: Nessuno (stampa formattata a terminale).
    """
    if not lotti or not risultati:
        print("[Avviso] Nessun dato da mostrare.")
        return

    print("\n" + "=" * 65)
    print("      REPORT OPERATIVO PRODUZIONE AGRICOLA")
    print("=" * 65)

    print("\n1. LOTTI STIMATI E FABBISOGNO ORE")
    print("-" * 65)
    for lotto in lotti:
        ettari = round(lotto["ettari"], 1)
        quantita = int(lotto["quantita"])
        ore = round(lotto["ore"], 1)
        giorni = round(lotto["giorni"], 1)
        print(f" - {lotto['nome']} ({ettari} ha) | {quantita} {lotto['unita']} -> {giorni} gg ({ore} h)")

    print("\n2. CONFRONTO STRATEGIE DI PIANIFICAZIONE")
    print("-" * 65)
    tempo_seq1 = round(risultati["ore_seq1"], 1)
    tempo_seq2 = round(risultati["ore_seq2"], 1)
    tempo_seq3 = round(risultati["ore_seq3"], 1)

    giorni_seq1 = round(tempo_seq1 / ORE_GIORNALIERE, 1)
    giorni_seq2 = round(tempo_seq2 / ORE_GIORNALIERE, 1)
    giorni_seq3 = round(tempo_seq3 / ORE_GIORNALIERE, 1)

    # Calcolo percentuali di risparmio con protezione da divisione per zero
    if tempo_seq1 > 0:
        risparmio_seq2 = round(((tempo_seq1 - tempo_seq2) / tempo_seq1) * 100, 1)
        risparmio_seq3 = round(((tempo_seq1 - tempo_seq3) / tempo_seq1) * 100, 1)
    else:
        risparmio_seq2 = 0.0
        risparmio_seq3 = 0.0

    print(f" - Sequenziale pura    : {tempo_seq1} h ({giorni_seq1} gg) | Base di confronto")
    print(f" - Parallela standard   : {tempo_seq2} h ({giorni_seq2} gg) | -{risparmio_seq2}% di tempo")
    print(f" - Parallela ottimizzata: {tempo_seq3} h ({giorni_seq3} gg) | -{risparmio_seq3}% di tempo")

    print("\n3. SATURAZIONE MACCHINARI (Scenario Ottimizzato)")
    print("-" * 65)
    for risorsa, ore in risultati["carichi"].items():
        ore_arrotondate = round(ore, 1)
        if tempo_seq3 > 0:
            saturazione = round((ore / tempo_seq3) * 100, 1)
        else:
            saturazione = 0.0
        print(f" - {risorsa}: {ore_arrotondate} h ({saturazione}%)")

    print("\n4. ANALISI SHORTEST PROCESSING TIME SULLE RISORSE CONDIVISE")
    print("-" * 65)
    if not risultati["risorse_condivise"]:
        print(" - Tutte le linee sono dedicate: nessun conflitto di sequenza da gestire.")
    else:
        for risorsa in risultati["risorse_condivise"]:
            print(f" - Sequenza su {risorsa}: {risultati['ordini'][risorsa]}")
            print(f" - Vantaggio Shortest Processing Time: primo lotto completato -> {risultati['primi_output'][risorsa]}")

    print("\n5. INDICAZIONI PER IL MANAGEMENT")
    print("-" * 65)
    bottleneck = risultati["bottleneck"]
    carico_bottleneck = round(risultati["carichi"].get(bottleneck, 0.0), 1)
    print(f" - Percorso critico (Bottleneck): {bottleneck} ({carico_bottleneck} ore)")

    if bottleneck in risultati["risorse_condivise"]:
        print(" - Diagnosi: Il ritardo complessivo e causato dall'alternanza sul macchinario.")
        print(" - Azione: Dare priorità a procedure di setup rapido o valutare noleggio di più unità.")
    else:
        print(" - Diagnosi: Il vincolo principale e dovuto alla saturazione del macchinario dedicato.")
        print(" - Azione: Considerare turni extra per assorbire il carico di lavoro.")
    print("=" * 65 + "\n")


def main():
    check_parametri_globali()

    if SEED_CASUALE is not None:
        random.seed(SEED_CASUALE)
        print(f"[Simulazione] Modalità deterministica con Seed = {SEED_CASUALE}")
    else:
        random.seed()
        print("[Simulazione] Modalità stocastica libera (Seed casuale)")

    catalogo = carica_configurazione()
    lotti = simula_lotti(catalogo)
    risultati = calcola_strategie(lotti)
    stampa_report(lotti, risultati)


if __name__ == "__main__":
    main()