from rdflib import Graph, Namespace
from rdflib.namespace import OWL
from time import sleep
from sys import argv, exit
from SPARQLWrapper import SPARQLWrapper, XML

WIKIDATA_PROP = Namespace("http://www.wikidata.org/prop/direct/")
WIKIDATA_ENTITY = Namespace("http://www.wikidata.org/entity/")
SCHEMA = Namespace("https://schema.org/")
HOMEBREW = Namespace(
    "https://raw.githubusercontent.com/fdioguardi/"
    + "movies_ontology/master/movie.ttl#"
)


def load_input(input):
    g = Graph()
    g.parse(input, format="turtle", encoding="utf-8")
    return g


def get_persons(graph):
    return graph.query(
        """
        SELECT DISTINCT ?person ?name
        WHERE {
          ?person rdf:type schema:Person.
          ?person homebrew:name ?name .
        }
        """,
        initNs={"schema": SCHEMA, "homebrew": HOMEBREW},
    )


def request_query(url, query):
    sparql = SPARQLWrapper(url)
    sparql.setQuery(query)
    sparql.setReturnFormat(XML)
    return sparql.query().convert()


def query_wikidata(name):
    query = (
        """
    CONSTRUCT {
      ?person ?predicate ?object
    }
    WHERE {
      ?person wdt:P31|wdt:P279 wd:Q5;
              ?label "%s"@en;
              ?predicate ?object.
    }
    """
        % name
    )

    return request_query("https://query.wikidata.org/sparql", query)


def query_dbpedia(name):
    query = (
        """
    CONSTRUCT {
      ?person ?predicate ?object
    }
    WHERE {
      ?person rdf:type dbo:Person;
              dbo:birthName|foaf:name ?name;
              ?predicate ?object.
      FILTER(REGEX(?name, "%s"@en, "e")).
    }
    """
        % name
    )

    return request_query("http://dbpedia.org/sparql", query)


def get_subject(graph):
    query = graph.query(
        """
        SELECT DISTINCT ?subject
        WHERE {
          ?subject ?predicate ?object
        } LIMIT 1
        """
    )
    for subject in query:
        return subject[0]


def merge_graphs(graph, external_graph, person):
    if len(external_graph) > 0:
        graph += external_graph
        graph.add((get_subject(external_graph), OWL.sameAs, person))
    return graph


def query_academy_winners_wikidata(actor):
    query = """
    PREFIX homebrew: <https://raw.githubusercontent.com/fdioguardi/movies_ontology/master/movie.ttl#>
    CONSTRUCT {
      ?actor homebrew:wasDirectedByOscarWinner ?director
    }
    WHERE {
      ?director wdt:P106 wd:Q2526255; # is director
        (wdt:P166/(wdt:P31?)) wd:Q19020.# has oscar

      ?film wdt:P31 wd:Q11424; # is movie
        wdt:P57 ?director; # has director
        wdt:P161 ?actor. # has actor

      ?actor wdt:P106 wd:Q33999. # is an actor

      FILTER(?actor = "%s"@en)
    }
    """ % actor

    return request_query("https://query.wikidata.org/sparql", query)


def query_academy_winners_dbpedia(actor):
    query = """
    PREFIX homebrew: <https://raw.githubusercontent.com/fdioguardi/movies_ontology/master/movie.ttl#>
    CONSTRUCT {
      ?actor homebrew:wasDirectedByOscarWinner ?director
    }
    WHERE {
      ?director wdt:P106 wd:Q2526255; # is director
        (wdt:P166/(wdt:P31?)) wd:Q19020. # has oscar

      ?film wdt:P31 wd:Q11424; # is movie
        wdt:P57 ?director; # has director
        wdt:P161 ?actor. # has actor

      ?actor wdt:P106 wd:Q33999. # is an actor

      FILTER(?actor = "%s"@en)
    }
    """ % actor

    return request_query("http://dbpedia.org/sparql", query)


def main():
    if len(argv) != 2:
        print(
            "Argumentos inválidos. Ingrese path relativo al dataset original."
        )
        exit(22)

    output = load_input(argv[1])

    for person, name in get_persons(output):
        try:
            merge_graphs(
                output, query_wikidata(name.toPython()), person
            )
            merge_graphs(
                output, query_dbpedia(name.toPython()), person
            )
        except:
            sleep(120)
            merge_graphs(
                output, query_wikidata(name.toPython()), person
            )
            merge_graphs(
                output, query_dbpedia(name.toPython()), person
            )

    ###########################################################

    wiki_actors = output.subjects(predicate=WIKIDATA_PROP.P106, object=WIKIDATA_ENTITY.Q10800557)
    db_actors = output.subjects(predicate=WIKIDATA_PROP.P106, object=WIKIDATA_ENTITY.Q10800557)

    for actor in wiki_actors:
        try:
            output += query_academy_winners_wikidata(actor)
        except:
            sleep(120)
            output += query_academy_winners_wikidata(actor)

    for actor in db_actors:
        if not (actor, HOMEBREW.wasDirectedByOscarWinner, None) in output:
            try:
                output += query_academy_winners_dbpedia(actor)
            except:
                sleep(120)
                output += query_academy_winners_wikidata(actor)

    ###########################################################

    print(output.serialize(format="turtle").decode("utf-8"))


if __name__ == "__main__":
    main()
