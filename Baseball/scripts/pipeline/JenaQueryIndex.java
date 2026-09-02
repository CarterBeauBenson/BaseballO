import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Stream;

import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;

/**
 * Execute the checked-in query-index CONSTRUCT components against one RDF
 * graph in an isolated in-memory Jena dataset.
 */
public final class JenaQueryIndex {
    private static final String SOURCE_PLACEHOLDER =
        "<urn:baseball:query-index:source-graph>";
    private static final String GAME_PLACEHOLDER =
        "<urn:baseball:query-index:game>";
    private static final String INDEX_PLACEHOLDER =
        "<urn:baseball:query-index:index-resource>";

    private JenaQueryIndex() {}

    public static void main(String[] args) throws Exception {
        if (args.length != 6) {
            throw new IllegalArgumentException(
                "expected: DATA SOURCE_GRAPH GAME INDEX_RESOURCE COMPONENT_ROOT OUTPUT_ROOT"
            );
        }
        Path data = Path.of(args[0]).toAbsolutePath().normalize();
        String sourceGraph = args[1];
        String game = args[2];
        String indexResource = args[3];
        Path componentRoot = Path.of(args[4]).toAbsolutePath().normalize();
        Path outputRoot = Path.of(args[5]).toAbsolutePath().normalize();
        if (!Files.isRegularFile(data) || !Files.isDirectory(componentRoot)) {
            throw new IllegalArgumentException("data file or component directory is missing");
        }
        Files.createDirectories(outputRoot);

        Dataset dataset = DatasetFactory.createTxnMem();
        try {
            Model source = dataset.getNamedModel(sourceGraph);
            RDFDataMgr.read(source, data.toUri().toString());
            List<Path> components;
            try (Stream<Path> stream = Files.list(componentRoot)) {
                components = stream
                    .filter(path -> Files.isRegularFile(path) && path.getFileName().toString().endsWith(".rq"))
                    .sorted(Comparator.comparing(path -> path.getFileName().toString()))
                    .toList();
            }
            if (components.isEmpty()) {
                throw new IllegalArgumentException("no query-index CONSTRUCT components found");
            }

            for (Path component : components) {
                String queryText = Files.readString(component, StandardCharsets.UTF_8)
                    .replace(SOURCE_PLACEHOLDER, "<" + sourceGraph + ">")
                    .replace(GAME_PLACEHOLDER, "<" + game + ">")
                    .replace(INDEX_PLACEHOLDER, "<" + indexResource + ">");
                if (queryText.contains("urn:baseball:query-index:")) {
                    throw new IllegalArgumentException(
                        "unresolved query-index placeholder in " + component.getFileName()
                    );
                }
                Query query = QueryFactory.create(queryText);
                if (!query.isConstructType()) {
                    throw new IllegalArgumentException(
                        "query-index component is not CONSTRUCT: " + component.getFileName()
                    );
                }
                Path output = outputRoot.resolve(
                    component.getFileName().toString().replaceFirst("\\.rq$", ".ttl")
                );
                try (
                    QueryExecution execution = QueryExecutionFactory.create(query, dataset);
                    OutputStream stream = Files.newOutputStream(output)
                ) {
                    Model result = execution.execConstruct();
                    RDFDataMgr.write(stream, result, Lang.TURTLE);
                }
            }
            System.out.println("Source triples: " + source.size());
            System.out.println("Components: " + components.size());
        } finally {
            dataset.close();
        }
    }
}
