import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.apache.jena.graph.Graph;
import org.apache.jena.riot.*;
import org.apache.jena.shacl.*;

/** One immutable data graph; independent shape graphs and reports per request. */
class ShaclSession {
    public static void main(String[] args) throws Exception {
        Graph data = RDFDataMgr.loadGraph(args[0]);
        System.out.println("READY\t" + data.size());
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String line;
        while ((line = input.readLine()) != null) {
            String shapeUri = new String(Base64.getDecoder().decode(line), StandardCharsets.UTF_8);
            Graph shapes = RDFDataMgr.loadGraph(shapeUri);
            ValidationReport report = ShaclValidator.get().validate(Shapes.parse(shapes), data);
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            RDFDataMgr.write(output, report.getModel(), Lang.TURTLE);
            System.out.println("REPORT\t" + report.conforms() + "\t" + shapes.size() + "\t" +
                Base64.getEncoder().encodeToString(output.toByteArray()));
            shapes.close();
        }
        data.close();
    }
}
