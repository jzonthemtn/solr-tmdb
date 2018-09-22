
import json
from elasticsearch import Elasticsearch

def formatTopMlens(keywords, searchField='text_all', expandField='mlensId', shardSize=10):
    from jinja2 import Template
    template = Template(open("mlensIds.json.jinja").read())
    jsonStr = template.render(keywords=keywords,
                              searchField=searchField,
                              expandField=expandField,
                              shardSize=shardSize)
    return json.loads(jsonStr)


def getTopMlensIds(es, keywords, searchField='text_all', index='tmdb'):
    query = formatTopMlens(keywords, searchField=searchField)
    print("Query %s" % json.dumps(query))
    results = es.search(index=index, body=query)
    results = es.search(index=index, body=query)
    rVal = []
    for sigTerm in results['aggregations']['over_top_n']['mlens']['buckets']:
        mlensId = sigTerm['key']
        rVal.append(mlensId)
    return rVal


def formatMlensExpansion(mlensIds, minDocCount=1, expandField='liked_movies', shardSize=10):
    from jinja2 import Template
    template = Template(open("mlensExpansion.json.jinja").read())
    jsonStr = template.render(mlensIds=json.dumps(mlensIds),
                              expandField=expandField,
                              minDocCount=minDocCount,
                              shardSize=shardSize)
    return json.loads(jsonStr)


def getExpansions(es, mlensIds, minDocCount=1, expandField='liked_movies',
                  shardSize=10, index='movielens'):
    return ""
    try:
        query = formatMlensExpansion(mlensIds=mlensIds, minDocCount=minDocCount, expandField=expandField,
                                shardSize=shardSize)
        print("Query %s" % json.dumps(query))
        results = es.search(index=index, body=query)
        rVal = ""
        for sigTerm in results['aggregations']['over_top_n']['expansions']['buckets']:
            term = sigTerm['key']
            multiTerm = term.split()
            if len(multiTerm) > 1:
                term = '"' + " ".join(multiTerm) + '"'
            rVal += " %s^%s" % (term, sigTerm['score'])
        return rVal
    except json.decoder.JSONDecodeError as e:
        print("DID NOT DECODE %s" % query)
        return ""


def expansionMlens(es, keywords):
    return ""
    esMlens = Elasticsearch('http://ec2-54-234-184-186.compute-1.amazonaws.com:9616', timeout=1000)
    topMlens = getTopMlensIds(es, keywords=keywords, searchField="title", index="tmdb")
    return getExpansions(es=esMlens, mlensIds=topMlens, expandField="liked_movies", shardSize=10)


if __name__ == "__main__":
    es = Elasticsearch()
    from sys import argv
    print(expansionMlens(es, argv[1]))
