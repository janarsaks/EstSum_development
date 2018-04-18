import sys
import re
import estnltk

PROTSENT = 0.3 #mitu protsenti sisukokkuvõtja ekstraktib
POSSC = 0.2	#positsiooniskoori osakaal
FORSC = 0.3	#formaadiskoori osakaal
WRDSC = 0.5	#sõnade sageduse osakaal

collect = 0	#lipuke
article = {}
sentence = {}
parnr = 0	#lõigu nr
divnr = 0	#divi nr
keywords = []
words = {}


def init_article():
    global article
    global parnr
    global divnr
    global words
    article = {"wcount": 0,
               "scount": 0,	#laused
              "pcount": 0,	#lõigud
              "divcount": 0,	#divid
              "title": "",	#pealkiri
              "tlength": 0,	#pikkus
              "body": [],	#artikli sisu
              "sort": []}	#sorteeritult
    parnr = 0
    divnr = 0
    words = {}


def tiitel(title):
    tc = 0
    article["title"] = title
    article["scount"] += 1
    rida = title
    rida = re.sub("<.*?>", "", rida)

    tekst = estnltk.Text(re.sub("[\s,.!?;:\xAB\xBB\-\"()]+", " ", rida))

    tykid = tekst.lemmas

    for elem in tykid:
        if len(elem) > 0:
            if elem.lower() not in words:
                words[elem.lower()] = 0

            words[elem.lower()] += 5
            tc += 1
    article["tlength"] = tc
    article["wcount"] += tc #article["tlength"]


def put_line(line):
    global sentence
    global parnr
    global divnr


    if bool(re.search("<p>", line)):
        article["pcount"] += 1
        parnr += 1
        return

    if bool(re.search('</p>', line)) or bool(re.search("</div", line)):
        return

    sentence = {"wcount": 0,  # init lause
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

        #line = line.replace("<div\d[^>]*><head>(.*)</head>", "") ####??????????????????????????????????????????????
        line = re.sub("<.*?>", "", line)

    if bool(re.search("<bibl>", line)):
        sentence["bibl"] = 1

    if bool(re.search("Pildi allkiri", line)):
        sentence["caption"] = 1

    sentence["content"] = line
    sentence["parnr"] = parnr
    sentence["divnr"] = divnr
    line = re.sub("<.*?>", "", line)
    line = re.sub("[„’́'“]", "", line)
    tekst = estnltk.Text(re.sub("[\s,.!?;:\xAB\xBB\-\"()]+", " ", line))

    tykid = tekst.lemmas
    #print(len(tykid))
    #print(tykid)
    sentence["wcount"] += len(tykid)
    weight = 1
    if sentence["subhead"] > 0:
        weight += 1
    for elem in tykid:
        ele = elem.lower()
        if ele.isalpha():

            if ele not in words:
                words[ele] = 0

            words[ele] += weight

        #else:
        #    print(elem)
    body = article["body"]
    body.append(sentence)
    article["body"] = body
    article["wcount"] += sentence["wcount"]


def print_annotation():
    summlength = calc_sum_length(article["wcount"])
    lipp = False
    i = 1
    score()
    sc = min_score(summlength)
    a = 0
    lastpar = 0
    actuallength = article["tlength"]
    #print("##########################")
    for elem in article["body"]:
        if elem["score"] + 0.00001 >= sc and actuallength <= summlength:
            if elem["parnr"] > lastpar:
                if lipp:
                    #print("</p>\n<p>\n")
                    a+=1
                else:
                    #print("<p>\n")
                    a-=1
                lastpar = elem["parnr"]



            #print("{0}. p={1} f={2} w={3} s={4}".format(i, elem["possc"], elem["forsc"], elem["wrdsc"], elem["score"]), end="")

            print(str(elem["wcount"])+"\t"+elem["content"])
            #print(elem["content"])
            actuallength += elem["wcount"]
            lipp = True

        i += 1

    #print("#########################")
    #print("Kokkuvõte koosneb " + str(actuallength) + " sõnast.")
    #print("Plaaniti " + str(summlength) + " sõna.")
    #print("Artiklis oli " + str(article["wcount"]))
    #print("10 võtmesõna: ", end=" ")

    #for i in range(10):
    #    print(keywords[i], end=" ")


def score():
    position_based_score()
    #for ele in article["body"]:
    #    print(ele["content"], end=" ")
    #    print(ele["possc"])
    format_based_score()
    word_based_score()

    for elem in article["body"]:
        if elem["subhead"] > 0:
            elem["score"] = 0
        else:
            elem["score"] = POSSC * elem["possc"] + FORSC * elem["forsc"] + WRDSC * elem["wrdsc"]


def position_based_score():
    i = 1 # number of sentence in the article
    j = 1 # number of sentence in the paragraph
    k = 1 # number of sentence in div
    lastparnr = 0 # last observed paragraph number
    lastdivnr = -1 # last observed division number

    for elem in article["body"]:
        if elem["parnr"] > lastparnr:
            lastparnr = elem["parnr"]
            j = 1
        if elem["divnr"] > lastdivnr:
            lastdivnr = elem["divnr"]
            k = 1
        if i == 1 and "Pildi allkiri" not in elem["content"]:
            elem["possc"] += 20
        if j == 1 and elem["subhead"] == 0:
            elem["possc"] += 5
        if k == 2 and i != 2:
            elem["possc"] += 5
        if i == 2:
            elem["possc"] += 5
        if j == 2:
            elem["possc"] += 2
        if j == 3:
            elem["possc"] += 1

        i += 1
        j += 1
        k += 1
    norm_score("possc")

def norm_score(score_type):
    total = 0.0
    for elem in article["body"]:
        total += elem[score_type]

    if (score_type == "forsc" or score_type == "wrdsc") and total == 0:
        total += 1
    for elem in article["body"]:
        elem[score_type] = round(elem[score_type] * 100 / total, 6)



def format_based_score():

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
        if bool(re.search('"', content)):
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

    norm_score("forsc")


def word_based_score():

    norm_word_weights()
    for elem in article["body"]:
        rida = elem["content"]
        rida = re.sub("<.*?>", "", rida)

        tekst = estnltk.Text(re.sub("[\s,.!?;:\xAB\xBB\-\"()]+", " ", rida))

        abi = tekst.lemmas

        for el in abi:

            el = el.lower()
            if el in words:
                elem["wrdsc"] += words[el]


        if elem["wcount"] != 0:
            elem["wrdsc"] /= elem["wcount"]
        else:
            elem["wrdsc"] = 0


    norm_score("wrdsc")


def norm_word_weights():
    with open('sagedusedlemma.txt', encoding="utf8") as f:
        lines = f.readlines()
    f.close()

    nwords = {}
    for rida in lines:
        tykid = estnltk.Text(rida).lemmas

        if rida.startswith("m/s"):
            tykid = rida.split()
        if tykid[0].lower() not in nwords:

            nwords[tykid[0].lower()] = float(tykid[1])

    with open('blacklistlemma.txt', encoding="utf8") as f:
        lines = f.readlines()
    f.close()
    blacklist = {}
    #print(lines)
    for rida in lines:
        rida = estnltk.Text(rida).lemmas[0]
        if rida not in blacklist:
            blacklist[rida] = 0

        blacklist[rida] += 1



    global words
    x = 10000/article["wcount"]
    for word in words:

        if word in blacklist:
            words[word] = 0
            continue
        if bool(re.search("\s+", word)):
            words[word] = 0
            continue
        words[word] = round(words[word] * x, 2)
        if word in nwords:
            if words[word] - nwords[word] > 0:
                words[word] -= nwords[word]
            else:
                words[word] = 0

    global keywords
    keywords = sorted(words, key=words.get, reverse=True)


def min_score(a):
    sl = a
    sl -= article["tlength"]

    sl += 10
    if sl < 0:
        return 10000

    min = 10000
    scores = {}

    for elem in article["body"]:
        if elem["score"] not in scores:
            scores[elem["score"]] = 0

        scores[elem["score"]] += elem["wcount"]

    for elem in sorted(scores.keys(), reverse=True):

        if scores[elem] < sl:
            min = elem
            sl -= scores[elem]
        else:
            break

    #print("Min score. " + str(min))

    return min


def calc_sum_length(a):
    return int(PROTSENT * a)






#if len(sys.args) > 0:
#    PROTSENT = sys.args[0] / 100.0
#    print(PROTSENT)
#else:
#    raise Exception('Jama')

#PROTSENT = 0.64

with open('sirp5.txt', encoding="utf8") as f:
    lines = f.readlines()
f.close()


for rawline in lines:
    rawline = rawline.strip()


    if bool(re.search("<div0", rawline)):  # artikli pealkiri
        init_article()  # algväärtustamine

        tiitel(rawline)  # pealkirjast sõnade uurimine #kuidas saada?
        print()
        collect = 1  # hakka lauseid koguma
        continue

    if bool(re.search("</div0", rawline)):  # artikli lõpp
        collect = 0

        print_annotation()  # trüki kokkuvõte
        print()
        continue

    if collect != 0:  # artikli sees
        put_line(rawline)  # töötle rida   ###kuidas rida saada
        continue

#print(article)
#print(words)
#print(keywords)




















