from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF
from time import sleep
from sys import argv, exit
from SPARQLWrapper import SPARQLWrapper, XML

DBO = Namespace("http://dbpedia.org/ontology/")
SCHEMA = Namespace("https://schema.org/")
WD = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")
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
    try:
        return sparql.query().convert()
    except:
        sleep(120)
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


def query_academy_winners_wikidata():
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
    }
    """

    return request_query("https://query.wikidata.org/sparql", query)


def query_academy_winners_dbpedia():
    query = """
    PREFIX homebrew: <https://raw.githubusercontent.com/fdioguardi/movies_ontology/master/movie.ttl#>
    CONSTRUCT {
      ?actor homebrew:wasDirectedByOscarWinner ?director
    }
    WHERE {
        ?movie dbo:director ?director;
                    dbo:starring ?actor;
                    rdf:type dbo:Film.

        ?director dct:subject ?subject.
       FILTER(REGEX(?subject, "Academy_Award_winners", "i"))
    }
    """

    return request_query("http://dbpedia.org/sparql", query)


def main():
    if len(argv) != 2:
        print(
            "Argumentos inválidos. Ingrese path relativo al dataset original."
        )
        exit(22)

    output = load_input(argv[1])

    for person, name in get_persons(output):
        merge_graphs(output, query_wikidata(name.toPython()), person)
        merge_graphs(output, query_dbpedia(name.toPython()), person)

    ###########################################################

    if (
        HOMEBREW["wasDirectedByOscarWinner"],
        RDF.type,
        OWL.ObjectProperty,
    ) not in output:
        output.add(
            (
                HOMEBREW["wasDirectedByOscarWinner"],
                RDF.type,
                OWL.ObjectProperty,
            )
        )

    # el tamaño del grafo es manejable, no se necesitan varias consultas
    stellar_graph = (
        query_academy_winners_dbpedia() + query_academy_winners_wikidata()
    )

    subjects = (
        list(output.subjects(predicate=WDT.P31, object=WD.Q5))
        + list(output.subjects(predicate=WDT.P279, object=WD.Q5))
        + list(output.subjects(predicate=RDF.type, object=DBO.Person))
    )

    for actor, _, director in stellar_graph:
        if (actor in subjects) and (director in subjects):
            output.add((actor, HOMEBREW.wasDirectedByOscarWinner, director))

    ###########################################################

    print(output.serialize(format="turtle").decode("utf-8"))


if __name__ == "__main__":
    main()
