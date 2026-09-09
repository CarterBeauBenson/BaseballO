"""Graph fixtures for independently querying and validating runner structure."""
from rdflib import Namespace, RDF, URIRef

BASE = Namespace('https://baseballontology.org/')
BFO = Namespace('http://purl.obolibrary.org/obo/')
CCO = Namespace('https://www.commoncoreontologies.org/')


def movement(g, rr, act, pa, runner=None, origin=None, destination=None):
    for triple in [(rr, RDF.type, BASE.RunnerResolutionProcess),
                   (rr, BFO.BFO_0000132, pa), (rr, BFO.BFO_0000062, act),
                   (act, RDF.type, BASE.BaserunningAct), (act, BFO.BFO_0000132, pa)]:
        g.add(triple)
    episode, judgment, decision = [URIRef(str(rr) + '/' + x) for x in ['episode', 'judgment', 'decision']]
    if runner:
        for triple in [(episode, RDF.type, BASE.RunnerResolutionEpisode),
                       (episode, BFO.BFO_0000132, pa), (episode, BFO.BFO_0000117, rr),
                       (episode, BFO.BFO_0000117, act), (act, CCO.ont00001833, runner),
                       (runner, RDF.type, CCO.ont00001262)]: g.add(triple)
    if origin:
        designation = URIRef(str(act) + '/origin-designation')
        for triple in [(designation, RDF.type, BASE.BaserunningSegmentOriginDesignation),
                       (designation, CCO.ont00001808, act), (designation, CCO.ont00001916, origin),
                       (origin, RDF.type, BASE.Base)]: g.add(triple)
    if destination:
        for triple in [(rr, RDF.type, BASE.SafeProcess), (rr, BFO.BFO_0000117, judgment),
                       (judgment, RDF.type, BASE.SafeJudgmentAct), (judgment, CCO.ont00001986, decision),
                       (judgment, BFO.BFO_0000132, rr), (decision, RDF.type, BASE.SafeDecisionICE),
                       (decision, CCO.ont00001808, rr), (decision, CCO.ont00001808, destination),
                       (destination, RDF.type, BASE.Base)]: g.add(triple)
    return episode, judgment, decision


def award(g, source, act, pa):
    rule = URIRef(str(source) + '/rule')
    for triple in [(source, RDF.type, BASE.WalkProcess), (source, BFO.BFO_0000132, pa),
                   (source, CCO.ont00001803, act), (rule, RDF.type, BASE.BaseballRule),
                   (rule, CCO.ont00001974, act), (act, CCO.ont00001807, rule)]: g.add(triple)
    return rule
