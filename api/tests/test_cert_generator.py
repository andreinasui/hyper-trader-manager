"""
Tests for self-signed certificate generator.

Covers:
- generate_self_signed_cert: creates cert + key PEM files
- CertGeneratorError: raised on failure
- Certificate properties: SANs, validity, key type
"""

import ipaddress
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa

from hyper_trader_api.services.cert_generator import (
    CertGeneratorError,
    generate_self_signed_cert,
)


class TestGenerateSelfSignedCert:
    """Tests for generate_self_signed_cert function."""

    def test_creates_cert_and_key_files(self, tmp_path: Path):
        """generate_self_signed_cert writes both cert and key PEM files."""
        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        assert cert_path.exists(), "cert.pem should be created"
        assert key_path.exists(), "key.pem should be created"

    def test_cert_file_is_valid_pem(self, tmp_path: Path):
        """cert.pem file contains a valid PEM-encoded X.509 certificate."""
        from cryptography.x509 import load_pem_x509_certificate

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        assert isinstance(cert, x509.Certificate)

    def test_key_file_is_valid_pem(self, tmp_path: Path):
        """key.pem file contains a valid PEM-encoded RSA private key."""
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        private_key = load_pem_private_key(key_path.read_bytes(), password=None)
        assert isinstance(private_key, rsa.RSAPrivateKey)

    def test_rsa_key_is_2048_bits(self, tmp_path: Path):
        """Private key uses 2048-bit RSA."""
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        private_key = load_pem_private_key(key_path.read_bytes(), password=None)
        assert isinstance(private_key, rsa.RSAPrivateKey)
        assert private_key.key_size == 2048

    def test_cert_has_localhost_san(self, tmp_path: Path):
        """Certificate includes 'localhost' as a DNS Subject Alternative Name."""
        from cryptography.x509 import load_pem_x509_certificate

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        dns_names = san.value.get_values_for_type(x509.DNSName)
        assert "localhost" in dns_names

    def test_cert_has_127_0_0_1_san(self, tmp_path: Path):
        """Certificate includes 127.0.0.1 as an IP Subject Alternative Name."""
        from cryptography.x509 import load_pem_x509_certificate

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        ip_addresses = san.value.get_values_for_type(x509.IPAddress)
        assert ipaddress.IPv4Address("127.0.0.1") in ip_addresses

    def test_cert_validity_defaults_to_10_years(self, tmp_path: Path):
        """Certificate validity period is approximately 10 years by default."""
        from cryptography.x509 import load_pem_x509_certificate

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        validity_days = (cert.not_valid_after_utc - cert.not_valid_before_utc).days
        # 10 years = 3650 days; allow ±2 days tolerance for leap years
        assert abs(validity_days - 3650) <= 2

    def test_cert_custom_validity_days(self, tmp_path: Path):
        """Certificate validity period respects the days_valid argument."""
        from cryptography.x509 import load_pem_x509_certificate

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path, days_valid=30)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        validity_days = (cert.not_valid_after_utc - cert.not_valid_before_utc).days
        assert validity_days == 30

    def test_cert_common_name_default(self, tmp_path: Path):
        """Certificate CN defaults to 'HyperTrader'."""
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.x509.oid import NameOID

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "HyperTrader"

    def test_cert_custom_common_name(self, tmp_path: Path):
        """Certificate CN respects the common_name argument."""
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.x509.oid import NameOID

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path, common_name="MyApp")

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "MyApp"

    def test_cert_is_self_signed(self, tmp_path: Path):
        """Certificate subject and issuer are the same (self-signed)."""
        from cryptography.x509 import load_pem_x509_certificate

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        assert cert.subject == cert.issuer

    def test_cert_not_valid_before_is_utc_now(self, tmp_path: Path):
        """Certificate not_valid_before is approximately now (UTC).

        X.509 timestamps have second-level precision, so we truncate microseconds
        from the before/after bounds when comparing.
        """
        from cryptography.x509 import load_pem_x509_certificate

        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        # X.509 stores timestamps at second precision - truncate microseconds
        before = datetime.now(UTC).replace(microsecond=0)
        generate_self_signed_cert(cert_path, key_path)
        after = datetime.now(UTC)

        cert = load_pem_x509_certificate(cert_path.read_bytes())
        assert before <= cert.not_valid_before_utc <= after

    def test_creates_parent_directories_if_missing(self, tmp_path: Path):
        """generate_self_signed_cert creates missing parent directories."""
        cert_path = tmp_path / "nested" / "certs" / "cert.pem"
        key_path = tmp_path / "nested" / "keys" / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        assert cert_path.exists()
        assert key_path.exists()

    def test_overwrites_existing_cert_file(self, tmp_path: Path):
        """Calling generate_self_signed_cert twice overwrites the previous cert."""
        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)
        first_content = cert_path.read_bytes()

        generate_self_signed_cert(cert_path, key_path)
        second_content = cert_path.read_bytes()

        # New cert is generated each time (different serial number)
        assert first_content != second_content

    def test_key_not_encrypted(self, tmp_path: Path):
        """Private key PEM is not encrypted (no passphrase needed)."""
        cert_path = tmp_path / "cert.pem"
        key_path = tmp_path / "key.pem"

        generate_self_signed_cert(cert_path, key_path)

        # Should load without password - raises ValueError if encrypted
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        key = load_pem_private_key(key_path.read_bytes(), password=None)
        assert key is not None


class TestCertGeneratorError:
    """Tests for CertGeneratorError exception."""

    def test_cert_generator_error_is_exception(self):
        """CertGeneratorError is a subclass of Exception."""
        err = CertGeneratorError("something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "something went wrong"

    def test_raises_cert_generator_error_on_invalid_path(self):
        """generate_self_signed_cert raises CertGeneratorError when write fails."""
        # Use a path that cannot be written (a directory used as file path)
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Provide the directory itself as the cert file path
            bad_cert_path = Path(tmpdir)
            key_path = Path(tmpdir) / "key.pem"

            with pytest.raises(CertGeneratorError):
                generate_self_signed_cert(bad_cert_path, key_path)
