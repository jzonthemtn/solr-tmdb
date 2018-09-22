import os
from collectFeatures import logFeatures, buildFeaturesJudgmentsFile
from loadFeatures import eachFeature


def trainModel(trainingData, testData, modelOutput, whichModel=8):
    # java -jar RankLib-2.6.jar -metric2t NDCG@4 -ranker 6 -kcv -train osc_judgments_wfeatures_train.txt -test osc_judgments_wfeatures_test.txt -save model.txt

    # For random forest
    # - bags of LambdaMART models
    #  - each is trained against a proportion of the training data (-srate)
    #  - each is trained using a subset of the features (-frate)
    #  - each can be either a MART or LambdaMART model (-rtype 6 lambda mart)
    cmd = "java -jar RankyMcRankFace.jar -gmax 20 -metric2t DCG@5 -bag 4 -srate 0.6 -frate 0.6 -rtype 6 -shrinkage 0.1 -tree 10 -ranker %s -train %s -test %s -save %s -feature features.txt" % (whichModel, trainingData, testData, modelOutput)
    print("*********************************************************************")
    print("*********************************************************************")
    print("Running %s" % cmd)
    os.system(cmd)
    pass


def partitionJudgments(judgments, testProportion=0.1):
    testJudgments = {}
    trainJudgments = {}
    from random import random
    for qid, judgment in judgments.items():
        draw = random()
        if draw <= testProportion:
            testJudgments[qid] = judgment
        else:
            trainJudgments[qid] = judgment

    return (trainJudgments, testJudgments)



def saveModel(esHost, scriptName, featureSet, modelFname):
    """ Save the ranklib model in Elasticsearch """
    import requests
    import json
    from urllib.parse import urljoin
    modelPayload = {
        "model": {
            "name": scriptName,
            "model": {
                "type": "model/ranklib",
                "definition": {
                }
            }
        }
    }

    # Force the model cache to rebuild
    path = "_ltr/_clearcache"
    fullPath = urljoin(esHost, path)
    print("POST %s" % fullPath)
    resp = requests.post(fullPath)
    if (resp.status_code >= 300):
        print(resp.text)

    with open(modelFname) as modelFile:
        modelContent = modelFile.read()
        path = "_ltr/_featureset/%s/_createmodel" % featureSet
        fullPath = urljoin(esHost, path)
        modelPayload['model']['model']['definition'] = modelContent
        print("POST %s" % fullPath)
        resp = requests.post(fullPath, json.dumps(modelPayload))
        print(resp.status_code)
        if (resp.status_code >= 300):
            print(resp.text)





if __name__ == "__main__":

    HUMAN_JUDGMENTS = 'movie_judgments.txt'
    TRAIN_JUDGMENTS = 'movie_judgments_wfeatures_train.txt'
    TEST_JUDGMENTS = 'movie_judgments_wfeatures_test.txt'

    #HUMAN_JUDGMENTS = 'synth_judg.txt'
    #TRAIN_JUDGMENTS = 'synth_judg_wfeatures_train.txt'
    #TEST_JUDGMENTS = 'synth_judg_wfeatures_test.txt'

    import configparser
    from solr import SolrColl
    from judgments import judgmentsFromFile, judgmentsByQid, duplicateJudgmentsByWeight

    config = configparser.ConfigParser()
    config.read('settings.cfg')
    solrUrl = config['DEFAULT']['SolrColl']

    solrColl = SolrColl(solrUrl)


    # Load features into Elasticsearch
    solrColl.reloadFeatures(features=eachFeature())
    # Parse a judgments
    print("-Parse judgments...")
    movieJudgments = judgmentsByQid(judgmentsFromFile(filename=HUMAN_JUDGMENTS))
    print("-Dup judgments by weight...")
    movieJudgments = duplicateJudgmentsByWeight(movieJudgments)
    print("-Train test split")
    trainJudgments, testJudgments = partitionJudgments(movieJudgments, testProportion=0.1)

    # Use proposed Elasticsearch queries (1.json.jinja ... N.json.jinja) to generate a training set
    # output as "sample_judgments_wfeatures.txt"
    print("-Log Features")
    logFeatures(solrColl, judgmentsByQid=movieJudgments)

    print("-Build training")
    buildFeaturesJudgmentsFile(trainJudgments, filename=TRAIN_JUDGMENTS)
    buildFeaturesJudgmentsFile(testJudgments, filename=TEST_JUDGMENTS)

    # Train each ranklib model type
    for modelType in [6,8]:
        # 0, MART
        # 1, RankNet
        # 2, RankBoost
        # 3, AdaRank
        # 4, coord Ascent
        # 6, LambdaMART
        # 7, ListNET
        # 8, Random Forests
        # 9, Linear Regression
        print("*** Training %s " % modelType)
        trainModel(trainingData=TRAIN_JUDGMENTS, testData=TEST_JUDGMENTS, modelOutput='model.txt', whichModel=modelType)
        # saveModel(esHost=esUrl, scriptName="test_%s" % modelType, featureSet='movie_features', modelFname='model.txt')
