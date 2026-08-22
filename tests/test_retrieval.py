import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from foodpharmer.retrieval import DocumentPage, LocalFssaiRetriever, chunk_document_pages, load_fssai_documents


def write_text_pdf(path: Path, pages: list[str]) -> None:
    """Create a tiny extractable PDF fixture without a PDF-generation dependency."""

    writer = PdfWriter()
    writer.add_metadata({"/Title": "FSSAI Claims Fixture"})
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = stream
    with path.open("wb") as output:
        writer.write(output)


class FssaiDocumentLoadingTests(unittest.TestCase):
    def test_loads_pdf_pages_with_document_and_page_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_text_pdf(root / "claims.pdf", ["PROTEIN SOURCE", "HIGH FIBRE"])

            pages = load_fssai_documents(root)

        self.assertEqual([page.page_number for page in pages], [1, 2])
        self.assertEqual([page.source for page in pages], ["claims.pdf", "claims.pdf"])
        self.assertTrue(all(page.document == "FSSAI Claims Fixture" for page in pages))
        self.assertEqual(pages[0].text, "PROTEIN SOURCE")

    def test_chunking_preserves_page_and_detected_section(self):
        pages = [
            DocumentPage(
                document="Claims",
                source="claims.pdf",
                page_number=7,
                text="SCHEDULE I\nProtein source claims require the stated amount.\n\n6. Non-addition claims\nNo added sugar has separate conditions.",
            )
        ]

        chunks = chunk_document_pages(pages, max_characters=70)

        self.assertEqual([chunk.page_number for chunk in chunks], [7, 7])
        self.assertEqual(chunks[0].section, "SCHEDULE I")
        self.assertEqual(chunks[1].section, "6. Non-addition claims")


class LocalRetrievalTests(unittest.TestCase):
    def setUp(self):
        pages = [
            DocumentPage(
                document="Claims",
                source="claims.pdf",
                page_number=3,
                text="SCHEDULE I\nA protein source claim requires the stated qualifying amount.",
            ),
            DocumentPage(
                document="Claims",
                source="claims.pdf",
                page_number=4,
                text="6. Non-addition claims\nConditions for no added sugar claims apply.",
            ),
        ]
        self.retriever = LocalFssaiRetriever(chunk_document_pages(pages))

    def test_retrieves_relevant_chunk_and_preserves_metadata(self):
        evidence = self.retriever.retrieve("PROTEIN SOURCE", "Protein: 10 g per 100 g")

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].document, "Claims")
        self.assertEqual(evidence[0].source, "claims.pdf")
        self.assertEqual(evidence[0].page_number, 3)
        self.assertIn("protein source", evidence[0].text.lower())

    def test_returns_no_evidence_when_no_rule_is_relevant(self):
        self.assertEqual(self.retriever.retrieve("MAGIC IMMUNITY BOOST", ""), [])


if __name__ == "__main__":
    unittest.main()
