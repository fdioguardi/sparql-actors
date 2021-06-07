from rdflib import Graph, Namespace
from sys import argv, exit
from SPARQLWrapper import SPARQLWrapper

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
    return sparql.query().convert()


def query_wikidata(name):
    query = """
    SELECT DISTINCT ?person ?predicate ?object
    WHERE {
       ?person wdt:P31|wdt:P279 wd:Q5;
              ?label "{}".
       ?person ?predicate ?object.
    } LIMIT 1
    """

    return Graph().parse(
        data=request_query("https://query.wikidata.org/sparql", query.format(name)))


def main():
    if len(argv) != 2:
        print(
            "Argumentos inválidos. Ingrese path relativo al dataset original."
        )
        exit(22)

    output = load_input(argv[1])

    for person, name in get_persons(output):
        output += query_wikidata(name.toPython())
            # + query_dbpedia(name.toPython())

    print(output.serialize(format="turtle").decode("utf-8"))


if __name__ == "__main__":
    main()
