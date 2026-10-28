import re
import unicodedata

from app.models.document import (
    ClassificationStatus,
    DocumentClassification,
    DocumentType,
)


Rule = tuple[str, int, str]


RULES: dict[DocumentType, list[Rule]] = {
    DocumentType.DNI: [
        (r"documento nacional de identidad", 6, "Documento Nacional de Identidad"),
        (r"\bdni\b", 4, "DNI"),
        (r"\bnacionalidad\b", 2, "Nacionalidad"),
        (r"fecha de nacimiento", 2, "Fecha de nacimiento"),
        (r"\bapellidos\b", 1, "Apellidos"),
        (r"\bsexo\b", 1, "Sexo"),
        (r"\bvalidez\b", 1, "Validez"),
        (r"\b\d{8}\s*[a-z]\b", 6, "Formato de número DNI"),
        (r"\b[xyz]\d{7}\s*[a-z]\b", 6, "Formato de NIE"),
        (r"\bidesp\b", 6, "Código IDESP"),
        (r"\besp\b", 2, "Código de nacionalidad ESP"),
        (r"\b\d{2}[./-]\d{2}[./-]\d{4}\b", 1, "Formato de fecha"),
    ],
    DocumentType.INVOICE: [
        (r"\bfactura\b", 6, "Factura"),
        (r"\binvoice\b", 6, "Invoice"),
        (r"numero de factura", 4, "Número de factura"),
        (r"base imponible", 3, "Base imponible"),
        (r"\bemisor\b", 2, "Emisor"),
        (r"\breceptor\b", 2, "Receptor"),
        (r"\biva\b", 1, "IVA"),
        (r"\btotal\b", 1, "Total"),
    ],
    DocumentType.DELIVERY_NOTE: [
        (r"\balbaran\b", 6, "Albarán"),
        (r"delivery note", 6, "Delivery note"),
        (r"fecha de entrega", 3, "Fecha de entrega"),
        (r"recibido por", 3, "Recibido por"),
        (r"\bmercancia\b", 2, "Mercancía"),
        (r"\bpedido\b", 1, "Pedido"),
        (r"\bunidades\b", 1, "Unidades"),
    ],
    DocumentType.RECEIPT: [
        (r"\bticket\b", 6, "Ticket"),
        (r"gracias por su compra", 4, "Gracias por su compra"),
        (r"\befectivo\b", 2, "Efectivo"),
        (r"\bcambio\b", 2, "Cambio"),
        (r"\bcaja\b", 1, "Caja"),
        (r"\bdependiente\b", 1, "Dependiente"),
        (r"\btotal\b", 1, "Total"),
    ],
}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)

    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )

    normalized = without_accents.lower()

    return re.sub(r"\s+", " ", normalized).strip()


def classify_document(text: str) -> DocumentClassification:
    normalized_text = _normalize(text)

    results: list[tuple[DocumentType, int, list[str]]] = []

    for document_type, rules in RULES.items():
        score = 0
        evidence: list[str] = []

        for pattern, weight, label in rules:
            if re.search(pattern, normalized_text):
                score += weight
                evidence.append(label)

        results.append((document_type, score, evidence))

    results.sort(key=lambda result: result[1], reverse=True)

    best_type, best_score, best_evidence = results[0]
    second_score = results[1][1]

    if best_score == 0:
        return DocumentClassification(
            document_type=DocumentType.UNKNOWN,
            status=ClassificationStatus.UNKNOWN,
            score=0,
            evidence=[],
        )

    status = (
        ClassificationStatus.CONFIDENT
        if best_score >= 4 and best_score - second_score >= 2
        else ClassificationStatus.DOUBTFUL
    )

    return DocumentClassification(
        document_type=best_type,
        status=status,
        score=best_score,
        evidence=best_evidence,
    )