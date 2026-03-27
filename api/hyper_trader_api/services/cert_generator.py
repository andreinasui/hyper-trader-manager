"""Self-signed certificate generator."""

import ipaddress
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)


class CertGeneratorError(Exception):
    """Certificate generation error."""

    pass


def generate_self_signed_cert(
    cert_path: Path,
    key_path: Path,
    common_name: str = "HyperTrader",
    days_valid: int = 365 * 10,  # 10 years
) -> None:
    """Generate a self-signed certificate and private key.

    Args:
        cert_path: Path to write certificate PEM file
        key_path: Path to write private key PEM file
        common_name: Certificate common name
        days_valid: Certificate validity in days

    Raises:
        CertGeneratorError: If certificate generation fails
    """
    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Build certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "HyperTrader Self-Hosted"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC))
            .not_valid_after(datetime.now(UTC) + timedelta(days=days_valid))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Ensure directories exist
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.parent.mkdir(parents=True, exist_ok=True)

        # Write private key
        key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

        # Write certificate
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        logger.info(f"Generated self-signed certificate: {cert_path}")

    except CertGeneratorError:
        raise
    except Exception as e:
        logger.error(f"Failed to generate certificate: {e}")
        raise CertGeneratorError(f"Certificate generation failed: {e}") from e
