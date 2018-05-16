import sys
import re
import estnltk

PROTSENT = 0.3

# lipuke
collect = 0
article = {}
sentence = {}

# lõigu nr
parnr = 0
# divi nr
divnr = 0
keywords = []
words = {}


# Meetod, mis algväärtustab analüüsiks vajalikud muutujad
def initiate_variables():
    global article
    global parnr
    global divnr
    global words
    article = {"wcount": 0,
               # laused
               "scount": 0,
               # lõigud
               "pcount": 0,
               # divid
               "divcount": 0,
               # pealkiri
               "title": "",
               # pikkus
               "tlength": 0,
               # artikli sisu
               "body": [],
               # sorteeritud artikli sisu
               "sort": []}
    parnr = 0
    divnr = 0
    words = {}


# Meetod, mis annab sisendfaili pealkirja sõnadele kõrgema algväärtuse
# Sisend: sisendfaili märgendatud pealkiri
def analyze_title(title):
    tc = 0
    article["title"] = title
    article["scount"] += 1

    # eemalda märgendid
    detagged_title = re.sub("<.*?>", "", title)

    # jaga sõnadeks
    title_words = estnltk.Text(re.sub("[\s,.!?;:\xAB\xBB\-\"()„’́'“«»]+", " ", detagged_title))

    title_lemmas = title_words.lemmas

    for lemma in title_lemmas:
        if len(lemma) > 0:

            if lemma.lower() not in words:
                words[lemma.lower()] = 0

            words[lemma.lower()] += 5
            tc += 1

    article["tlength"] = tc
    article["wcount"] += tc


def analyze_line(line):
    global sentence
    global parnr
    global divnr

    if bool(re.search("<p>", line)):
        article["pcount"] += 1
        parnr += 1
        return

    if bool(re.search('</p>', line)) or bool(re.search("</div", line)):
        return

    # lause informatsioon
    sentence = {"wcount": 0,
                "parnr": 0,
                "divnr": 0,
                "subhead": 0,
                "bibl": 0,
                "caption": 0,
                "possc": 0,
                "forsc": 0,
                "wrdsc": 0,
                "score": 0,
                "content": ""}

    if bool(re.search("<div", line)):

        if len(article["body"]) != 0:
            article["divcount"] += 1
            divnr += 1
        sentence["subhead"] = 1
        article["pcount"] += 1
        parnr += 1

        # eemaldame märgendused
        line = re.sub("<.*?>", "", line)

    if bool(re.search("<bibl>", line)):
        sentence["bibl"] = 1

    if bool(re.search("Pildi allkiri", line)):
        sentence["caption"] = 1

    sentence["content"] = line
    sentence["parnr"] = parnr
    sentence["divnr"] = divnr
    # eemaldame märgendid
    line = re.sub("<.*?>", "", line)
    # jagame sõnadeks
    line_words = estnltk.Text(re.sub("[\s,.!?;:\xAB\xBB\-\"()„’́'“«»]+", " ", line))

    line_lemmas = line_words.lemmas

    sentence["wcount"] += len(line_lemmas)
    weight = 1
    if sentence["subhead"] > 0:
        weight += 1

    for lemma in line_lemmas:
        lemma = lemma.lower()
        if lemma.isalpha():

            if lemma not in words:
                words[lemma] = 0

            words[lemma] += weight

    body = article["body"]
    body.append(sentence)
    article["body"] = body
    article["wcount"] += sentence["wcount"]


# Kokkuvõttete jaoks lausete valimine ja printime
def print_annotation():
    sum_length = calc_sum_length(article["wcount"])
    flag = False
    i = 1
    # Määrame lausetele kaalud
    weigh_sentences()
    sc = min_score(sum_length)
    a = 0
    lastpar = 0
    actuallength = article["tlength"]

    print("##########################")

    for elem in article["body"]:
        # valime sobivaid laused
        if elem["score"] + 0.00001 >= sc and actuallength <= sum_length:
            if elem["parnr"] > lastpar:
                if flag:
                    print("</p>\n<p>\n")
                    a += 1
                else:
                    print("<p>\n")
                    a -= 1
                lastpar = elem["parnr"]

            print("{0}. p={1} f={2} w={3} s={4}".format(i, elem["possc"], elem["forsc"], elem["wrdsc"], elem["score"]),
                  end="")

            print(elem["content"])
            actuallength += elem["wcount"]
            flag = True

        i += 1

    print("#########################")
    print("Kokkuvõte koosneb " + str(actuallength) + " sõnast.")
    print("Plaaniti " + str(sum_length) + " sõna.")
    print("Artiklis oli " + str(article["wcount"]))
    print("10 võtmesõna: ", end=" ")

    for i in range(10):
        print(keywords[i], end=" ")


# Meetoid, mis määrab lausetele kaalu
def weigh_sentences():
    # Leiame laustele positsiooni, formaadi ja sõnasageduse skoori
    position_based_score()
    format_based_score()
    word_based_score()

    # Arvutame laustele kaalud
    for unweigheted_sentence in article["body"]:
        if unweigheted_sentence["subhead"] > 0:
            unweigheted_sentence["score"] = 0
        else:
            unweigheted_sentence["score"] = POSSC * unweigheted_sentence["possc"] + FORSC * unweigheted_sentence[
                "forsc"] + WRDSC * unweigheted_sentence["wrdsc"]


# Lausetele positsiooniskoori määramine
def position_based_score():
    sentencenr_in_article = 1
    sentencenr_in_paragraph = 1
    sentencenr_in_div = 1

    # viimane nähtud lõigu nr
    lastparnr = 0
    # viimane nähtud divi nr
    lastdivnr = -1

    # iga lause läbi vaatamine
    for elem in article["body"]:

        if elem["parnr"] > lastparnr:
            lastparnr = elem["parnr"]
            sentencenr_in_paragraph = 1

        if elem["divnr"] > lastdivnr:
            lastdivnr = elem["divnr"]
            sentencenr_in_div = 1

        if sentencenr_in_article == 1 and "Pildi allkiri" not in elem["content"]:
            elem["possc"] += 20

        if sentencenr_in_paragraph == 1 and elem["subhead"] == 0:
            elem["possc"] += 5

        if sentencenr_in_div == 2 and sentencenr_in_article != 2:
            elem["possc"] += 5

        if sentencenr_in_article == 2:
            elem["possc"] += 5

        if sentencenr_in_paragraph == 2:
            elem["possc"] += 2

        if sentencenr_in_paragraph == 3:
            elem["possc"] += 1

        sentencenr_in_article += 1
        sentencenr_in_paragraph += 1
        sentencenr_in_div += 1

    # positsiooniskoori normaliseerimine
    normalize_score("possc")


# Skooride normaliseerimne
# Sisend: String skooritüübist
def normalize_score(score_type):
    total = 0.0
    for elem in article["body"]:
        total += elem[score_type]

    if (score_type == "forsc" or score_type == "wrdsc") and total == 0:
        total += 1
    for elem in article["body"]:
        elem[score_type] = round(elem[score_type] * 100 / total, 6)


# Laustele formaadiskoori määramine
def format_based_score():
    # iga lause läbivaatamine
    for elem in article["body"]:
        elem["forsc"] = 5
        content = elem["content"]
        if bool(re.search("<s><hi .*</hi></s>", content)):
            elem["forsc"] += 8
        if bool(re.search("[!?]+</s>", content)):
            elem["forsc"] -= 5
        if bool(re.search("[!?]+</hi></s>", content)):
            elem["forsc"] -= 13
        if bool(re.search("[!?]+", content)):
            elem["forsc"] -= 5
        if bool(re.search('[„“«»"]', content)):
            elem["forsc"] -= 4
        if bool(re.search("[!?]+\"", content)):
            elem["forsc"] -= 13
        if elem["subhead"] != 0 or elem["bibl"] != 0 or elem["caption"] != 0:
            elem["forsc"] = 0
        if bool(re.search("<s>\xAB[^\xBB]*,\xBB", content)):
            elem["forsc"] -= 4
        if bool(re.search("<s>\xAB[^\xBB]*\xBB</s>", content)):
            elem["forsc"] -= 4
        if bool(re.search(": \xAB[^\xBB]*\xBB</s>", content)):
            elem["forsc"] -= 4

        if elem["forsc"] < 0:
            elem["forsc"] = 0
        if bool(re.search("<bibl>", content)):
            elem["forsc"] = 0
        if elem["wcount"] <= 3:
            elem["forsc"] = 0

    # formaadiskoori normaliseerimine
    normalize_score("forsc")


# Laustele sõnasageduse põhise skoori määramine
def word_based_score():
    norm_word_weights()
    for elem in article["body"]:
        content = elem["content"]
        # eemaldame märgendid
        content = re.sub("<.*?>", "", content)
        # jagame sõnadeks
        content_words = estnltk.Text(re.sub("[\s,.!?;:\xAB\xBB\-\"()„’́'“«»]+", " ", content))
        # lemmastame
        content_lemmas = content_words.lemmas

        for lemma in content_lemmas:

            lemma = lemma.lower()
            if lemma in words:
                elem["wrdsc"] += words[lemma]

        if elem["wcount"] != 0:
            elem["wrdsc"] /= elem["wcount"]
        else:
            elem["wrdsc"] = 0

    # normaliseerime lausete sõnasageduse põhise skoori
    normalize_score("wrdsc")


# Muudame sõnade skoori vastavalt, kas sõna sagedane või tegemist stoppsõnaga
# Leiame 10 tähtsamat võtmesõna
def norm_word_weights():
    with open('lemmasagedused.txt', encoding="utf-8") as f:
        lines = f.readlines()
    # sagedased lemmad
    freq_lemmas = {}

    for freq_lemma in lines:
        lemma_and_freq = freq_lemma.split("\t")

        if lemma_and_freq[0].lower() not in freq_lemmas:
            # lisa sagedaste lemmade sageudsed
            freq_lemmas[lemma_and_freq[0].lower()] = float(lemma_and_freq[1])

    with open('stoppsonad.txt', encoding="utf-8") as f:
        lines = f.readlines()

    # stoppsõnad
    stopwords = {}

    for stopword in lines:

        if stopword not in stopwords:
            stopwords[stopword] = 0

        stopwords[stopword] += 1

    global words
    x = 10000 / article["wcount"]

    # Muudame sõna skoori 0, kui tegemist on stoppsõnaga
    # Vähendame sõna sagedust, kui sagedane
    for word in words:

        if word in stopwords:
            words[word] = 0
            continue
        if bool(re.search("\s+", word)):
            words[word] = 0
            continue
        words[word] = round(words[word] * x, 2)
        if word in freq_lemmas:
            if words[word] - freq_lemmas[word] > 0:
                words[word] -= freq_lemmas[word]
            else:
                words[word] = 0

    # Leiame võtmesõnad
    global keywords
    keywords = sorted(words, key=words.get, reverse=True)


# Meetod, mis arutab miinimum skoori
# Sisend: kokkuvõtte sihtpikkust
# Väljund: miinimum lause kaal
def min_score(summary_length):
    sl = summary_length
    sl -= article["tlength"]
    sl += 10

    if sl < 0:
        return 10000

    minimum = 10000
    scores = {}

    for elem in article["body"]:
        if elem["score"] not in scores:
            scores[elem["score"]] = 0

        scores[elem["score"]] += elem["wcount"]

    for elem in sorted(scores.keys(), reverse=True):

        if scores[elem] < sl:
            minimum = elem
            sl -= scores[elem]
        else:
            break

    print("Min score. " + str(minimum))

    return minimum


# Arvuta kokkuvõtte sihtpikkus
# Sisend: sõnade arv artiklis
# Väljund: kokkuvõtte sihtpikkus
def calc_sum_length(words_in_article):
    return int(PROTSENT * words_in_article)


if __name__ == '__main__':

    # Märgendatud faili asukoht
    tagged_file_loc = sys.argv[1]

    # Positsiooniskoori, formaadipõhise skoori ja sõnasageduste põhise skoori osakaalud lause kaalu valemis
    POSSC = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4
    FORSC = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
    WRDSC = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2

    with open(tagged_file_loc, encoding="utf-8-sig") as tagged_file:
        tagged_file_lines = tagged_file.readlines()

    for tagged_file_line in tagged_file_lines:
        tagged_file_line = tagged_file_line.strip()

        # Artikli pealkiri
        if bool(re.search("<div0", tagged_file_line)):
            # Algväärtustamine
            initiate_variables()

            # Pealkirja analüüs
            analyze_title(tagged_file_line)

            # Hakka lauseid koguma
            collect = 1
            continue

        # Artikli lõpp
        if bool(re.search("</div0", tagged_file_line)):
            collect = 0
            # Trüki kokkuvõte
            print_annotation()
            continue

        # Artikli sees
        if collect != 0:
            # Rea töötlemine
            analyze_line(tagged_file_line)
