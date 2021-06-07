from rdflib import Graph, Namespace
from rdflib.namespace import OWL
from sys import argv, exit
from SPARQLWrapper import SPARQLWrapper, XML

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
              ?label "%s";
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
      FILTER(REGEX(?name, "%s", "e")).
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
          ?subject?predicate ?object
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


def main():
    if len(argv) != 2:
        print(
            "Argumentos inválidos. Ingrese path relativo al dataset original."
        )
        exit(22)

    output = load_input(argv[1])

    for person, name in get_persons(output):
        graph = merge_graphs(output, query_wikidata(name.toPython()), person)
        graph = merge_graphs(output, query_dbpedia(name.toPython()), person)

    print(output.serialize(format="turtle").decode("utf-8"))


if __name__ == "__main__":
    main()
