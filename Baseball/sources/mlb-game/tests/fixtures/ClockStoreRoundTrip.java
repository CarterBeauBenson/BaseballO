import java.nio.file.Files;
import java.nio.file.Path;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.query.ReadWrite;
import org.apache.jena.update.UpdateAction;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFParser;

class ClockStoreRoundTrip {
    public static void main(String[] args) throws Exception {
        var dataset = TDB2Factory.connectDataset(args[0]);
        try {
            dataset.begin(ReadWrite.WRITE);
            RDFParser.source(args[1]).lang(Lang.NTRIPLES).parse(dataset.getNamedModel("urn:game"));
            dataset.commit();
            dataset.end();
            dataset.begin(ReadWrite.WRITE);
            try {
                UpdateAction.parseExecute(Files.readString(Path.of(args[2])), dataset);
                dataset.commit();
            } finally { dataset.end(); }
            dataset.begin(ReadWrite.READ);
            try (var output = Files.newOutputStream(Path.of(args[3]))) {
                RDFDataMgr.write(output, dataset.getNamedModel("urn:game"), Lang.NTRIPLES);
            } finally { dataset.end(); }
        } finally { dataset.close(); }
    }
}
