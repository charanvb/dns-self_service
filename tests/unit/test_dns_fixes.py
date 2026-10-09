import unittest
from unittest.mock import MagicMock, patch
import time

from shared.validation.common import validate_fqdn, ValidationError
from shared.validation.record_types.cname import validate as validate_cname
from shared.validation.registry import SUPPORTED_RECORD_TYPES, RECORD_TYPE_VALIDATORS
from shared.micetro.encoding import encode
from shared.micetro.client import MicetroClient, _SESSION_CACHE, _SESSION_LOCK
from shared.micetro.provider import MicetroProvider


class TestFqdnValidation(unittest.TestCase):
    def test_txt_fqdn_allows_underscores(self):
        # DKIM selector
        validate_fqdn("default._domainkey.example.com", "example.com", record_type="TXT")
        # DMARC
        validate_fqdn("_dmarc.example.com", "example.com", record_type="TXT")
        # Multiple underscores in label
        validate_fqdn("_asuid.sub_domain.example.com", "example.com", record_type="TXT")

    def test_cname_fqdn_allows_underscores(self):
        # DKIM CNAME delegation
        validate_fqdn("selector1._domainkey.example.com", "example.com", record_type="CNAME")
        # Azure / domain verification CNAME
        validate_fqdn("_acme-challenge.example.com", "example.com", record_type="CNAME")

    def test_a_record_rejects_underscores(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_fqdn("_badhost.example.com", "example.com", record_type="A")
        self.assertIn("Invalid DNS label", str(ctx.exception))

    def test_cname_value_target_allows_underscores(self):
        # CNAME target pointing to DKIM or cloud provider service with underscores
        val = validate_cname({"target": "s1._domainkey.provider.net"})
        self.assertEqual(val["target"], "s1._domainkey.provider.net")

        val2 = validate_cname({"target": "_dmarc.customdomain.org."})
        self.assertEqual(val2["target"], "_dmarc.customdomain.org.")


class TestMxRecordRemoval(unittest.TestCase):
    def test_mx_not_supported(self):
        self.assertNotIn("MX", SUPPORTED_RECORD_TYPES)
        self.assertNotIn("MX", RECORD_TYPE_VALIDATORS)

    def test_mx_encoding_raises(self):
        with self.assertRaises(ValueError):
            encode("MX", {"preference": 10, "exchange": "mail.example.com"})


class TestMicetroSessionCaching(unittest.TestCase):
    def setUp(self):
        with _SESSION_LOCK:
            _SESSION_CACHE.clear()

    @patch("shared.micetro.client.requests.post")
    def test_session_cached_and_reused(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"result": {"session": "token-12345"}}
        mock_post.return_value = mock_response

        client = MicetroClient(
            base_url="https://micetro.test/mmws/api/v2",
            username="testuser",
            password="testpassword",
        )

        token1 = client._ensure_token()
        self.assertEqual(token1, "token-12345")
        self.assertEqual(mock_post.call_count, 1)

        # Second call should reuse cached token
        token2 = client._ensure_token()
        self.assertEqual(token2, "token-12345")
        self.assertEqual(mock_post.call_count, 1)

    @patch("shared.micetro.client.requests.post")
    def test_session_eviction_on_invalidation(self, mock_post):
        mock_post_resp = MagicMock()
        mock_post_resp.raise_for_status.return_value = None
        mock_post_resp.json.return_value = {"result": {"session": "token-abc"}}
        mock_post.return_value = mock_post_resp

        client = MicetroClient(
            base_url="https://micetro.test/mmws/api/v2",
            username="testuser",
            password="testpassword",
        )

        token = client._ensure_token()
        self.assertEqual(token, "token-abc")
        self.assertIn(client._cache_key, _SESSION_CACHE)

        # Evict cache
        client._invalidate_cached_token()
        self.assertNotIn(client._cache_key, _SESSION_CACHE)


class TestMicetroBaseUrlNormalization(unittest.TestCase):
    def test_host_only_url_gets_default_api_path(self):
        client = MicetroClient(
            base_url="https://ssportal-qa.unilever.com",
            username="testuser",
            password="testpassword",
        )
        self.assertEqual(client.base_url, "https://ssportal-qa.unilever.com/mmws/api/v2")

    def test_mmws_api_url_gets_version_suffix(self):
        client = MicetroClient(
            base_url="https://ssportal-qa.unilever.com/mmws/api",
            username="testuser",
            password="testpassword",
        )
        self.assertEqual(client.base_url, "https://ssportal-qa.unilever.com/mmws/api/v2")

    def test_v2_url_is_preserved(self):
        client = MicetroClient(
            base_url="https://ssportal-qa.unilever.com/mmws/api/v2",
            username="testuser",
            password="testpassword",
        )
        self.assertEqual(client.base_url, "https://ssportal-qa.unilever.com/mmws/api/v2")


class TestTargetedRecordLookup(unittest.TestCase):
    @patch.object(MicetroClient, "get")
    def test_find_records_by_name_apex(self, mock_get):
        mock_get.return_value = {
            "result": {
                "dnsRecords": [
                    {
                        "ref": "dnsRecords/1",
                        "name": "@",
                        "type": "TXT",
                        "data": "v=spf1 -all",
                        "ttl": 3600,
                    }
                ]
            }
        }
        provider = MicetroProvider(client=MagicMock(spec=MicetroClient))
        provider.client.get = mock_get

        records = provider.find_records_by_name(
            zone_ref="dnsZones/123",
            fqdn="example.com",
            record_type="TXT",
            zone_name="example.com",
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "example.com")
        self.assertEqual(records[0].record_type, "TXT")
        self.assertEqual(records[0].data, "v=spf1 -all")

        # Verify query parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertIn("filter", kwargs["params"])
        self.assertIn("type=TXT", kwargs["params"]["filter"])


if __name__ == "__main__":
    unittest.main()
