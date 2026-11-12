# COSMIC Data Reference

## Scope and access

COSMIC (Catalogue Of Somatic Mutations In Cancer) is a curated resource describing somatic mutations and related cancer genomics data. Use the release-specific file descriptions supplied with each download as the authoritative schema reference.

Access is controlled:
- Non-commercial users must register and sign in before downloading.
- Commercial use requires the applicable commercial licence.
- The user is responsible for complying with the terms attached to their account and downloaded products.
- Do not redistribute downloaded datasets or credentials unless the governing licence explicitly permits it.

The download catalogue publishes release-specific products, genome assemblies, checksums, and file descriptions. Never hard-code a release number as "latest"; verify the selected release at download time.

## Common data families

| Data family | Typical use | Important checks |
|---|---|---|
| Coding mutations | Variant-level mutation analysis | Genome assembly, transcript, consequence, sample identifiers |
| VCF mutation files | Variant-tool interoperability | VCF version, reference assembly, normalization, contig names |
| Cancer Gene Census | Curated cancer gene evidence and roles | Release, gene identifier, role and evidence fields |
| Mutational signatures | Compare observed mutation patterns with signature profiles | Signature taxonomy, exposure units, sample context |
| Gene fusions and structural variants | Study rearrangements and fusion events | Breakpoint representation, partner genes, coordinate system |
| Copy-number alterations | Study gains, losses, and copy-number state | Segmentation, ploidy assumptions, genome build |
| Gene expression | Compare expression-related records | Quantification method, normalization, tissue and sample context |
| Resistance mutations | Explore resistance-associated variant annotations | Evidence level, drug context, release, and source notes |

These are conceptual data families. Exact product names, columns, and file availability vary by release and product.

## Genome assemblies

Two assemblies commonly encountered in COSMIC paths are:
- **GRCh38:** generally preferable for new analyses when the rest of the pipeline uses this assembly.
- **GRCh37:** retained for compatibility with legacy workflows.

Never combine coordinates from different assemblies without an explicit, validated conversion step. Record the assembly in every derived dataset and report.

## File formats

### TSV and CSV

- Read tab-separated files with a tab delimiter.
- Read comma-separated files with a comma delimiter.
- Preserve the original headers during initial ingestion.
- Use explicit data types for identifiers and coordinates.
- Treat empty values as missing only after checking the file description.
- Large compressed files should be streamed or processed in chunks where possible.

Example:

~~~python
import pandas as pd

df = pd.read_csv(
    "mutations.tsv.gz",
    sep="\\t",
    compression="gzip",
    low_memory=False,
)
~~~

### VCF

Use a VCF-aware parser for variant records. Do not parse complex VCF files using naive string splitting when header metadata, INFO fields, or genotype fields are required.

Check:
- VCF header and version;
- reference assembly;
- chromosome naming conventions;
- coordinate conventions;
- normalization and multi-allelic representation;
- INFO and FORMAT definitions.

### TAR and compressed downloads

The download portal may provide an archive containing the data file and a release-specific README or column description. Keep that documentation alongside the archived download and record the checksum before extracting or transforming files.

## Identifiers and fields

Do not assume field names are identical across product families or releases. Consult the file-specific description before mapping columns.

Common concepts include:
- gene symbols and stable gene identifiers;
- genome coordinates and reference alleles;
- alternate alleles and mutation descriptions;
- transcript identifiers and consequence annotations;
- sample or tumour identifiers;
- primary site and histology;
- publication or evidence references;
- release and genome-build metadata.

For every analysis, preserve original identifiers and source fields. Add normalized fields separately rather than silently overwriting source values.

## Data acquisition and reproducibility

For each downloaded product, record:
- product name;
- release version;
- genome assembly;
- source file name;
- download date;
- archive checksum;
- access/licence context;
- transformations and software versions.

The portal's scripted download option supplies release-specific instructions. Use an authenticated account to obtain an authorized download URL or command. A download helper should not attempt to bypass login or licensing controls.

## Quality control

Before analysis:
1. Verify the archive or file checksum when provided.
2. Confirm decompression completed successfully.
3. Inspect the file header and column description.
4. Count records and identify duplicate keys.
5. Check coordinate and identifier fields for missing or malformed values.
6. Confirm the genome assembly matches the analysis pipeline.
7. Record filtering and normalization choices.

Do not delete rows with missing annotations without understanding why they are missing. Missingness may be meaningful or product-specific.

## Citation and reporting

Follow the current citation instructions supplied by the data provider. In methods and outputs, record the product, release, genome assembly, access date, and any filtering or transformation performed.

COSMIC data are research resources. Their presence in this database is not, by itself, a clinical interpretation or treatment recommendation.
