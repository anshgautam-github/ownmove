"""Regression tests for `app.core.security` — the single most
security-critical code path in the app: every protected route's identity
guarantee depends on `verify_token`/`decode_token` correctly accepting only
a genuinely valid, current, correctly-audienced Supabase JWT and rejecting
everything else.

These are deliberately narrow, dependency-free unit tests against the
module directly (no TestClient, no FastAPI dependency graph) — the goal is
a fast, permanent guard against a regression in the verification logic
itself, independent of how any given route wires it up. HTTP-level 401
behavior (missing header, wrong scheme, etc.) is covered separately by the
existing route/integration tests; this file is about the token check
itself.

conftest.py sets SUPABASE_JWT_SECRET="test-secret" and leaves SUPABASE_URL
unset before any app module imports settings, so every test below signs
with that same HS256 secret and never touches the JWKS/asymmetric path
(covered separately below by simulating an unconfigured JWKS lookup).
"""

import time

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import AuthenticatedUser, decode_token, token_expiry, verify_token

_SECRET = "test-secret"  # matches conftest.py's SUPABASE_JWT_SECRET
_AUDIENCE = "authenticated"  # matches settings.SUPABASE_JWT_AUDIENCE's default


def _payload(**overrides) -> dict:
    now = int(time.time())
    payload = {
        "sub": "user-123",
        "email": "student@example.com",
        "role": "authenticated",
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + 3600,
    }
    payload.update(overrides)
    return payload


def _token(secret: str = _SECRET, algorithm: str = "HS256", **overrides) -> str:
    return jwt.encode(_payload(**overrides), secret, algorithm=algorithm)


# ---------------------------------------------------------------------------
# valid token
# ---------------------------------------------------------------------------


def test_verify_token_accepts_a_valid_token():
    user = verify_token(_token())

    assert isinstance(user, AuthenticatedUser)
    assert user.id == "user-123"
    assert user.email == "student@example.com"
    assert user.role == "authenticated"


def test_verify_token_carries_app_metadata_provider_through():
    token = _token(app_metadata={"provider": "google"})

    user = verify_token(token)

    assert user.provider == "google"


def test_decode_token_returns_the_raw_claims():
    claims = decode_token(_token())

    assert claims["sub"] == "user-123"
    assert claims["aud"] == _AUDIENCE


def test_token_expiry_reads_the_exp_claim():
    claims = decode_token(_token())

    expiry = token_expiry(claims)

    assert expiry is not None
    assert expiry.timestamp() == pytest.approx(claims["exp"], abs=1)


def test_token_expiry_returns_none_when_exp_is_absent():
    # decode_token itself requires "exp" (options={"require": ["exp", "sub"]}),
    # so this exercises token_expiry() as a standalone unit against a claims
    # dict that never went through decode_token — a defensive case, not one
    # reachable via verify_token() in production.
    assert token_expiry({"sub": "user-123"}) is None


# ---------------------------------------------------------------------------
# wrong signing secret
# ---------------------------------------------------------------------------


def test_verify_token_rejects_a_token_signed_with_the_wrong_secret():
    token = _token(secret="an-attacker-controlled-secret")

    with pytest.raises(UnauthorizedError):
        verify_token(token)


# ---------------------------------------------------------------------------
# expired token
# ---------------------------------------------------------------------------


def test_verify_token_rejects_an_expired_token():
    now = int(time.time())
    token = _token(iat=now - 7200, exp=now - 3600)

    with pytest.raises(UnauthorizedError, match="expired"):
        verify_token(token)


# ---------------------------------------------------------------------------
# missing / empty subject claim
# ---------------------------------------------------------------------------


def test_verify_token_rejects_a_token_with_no_sub_claim():
    # decode_token requires "sub" via options={"require": [...]}, so PyJWT
    # itself rejects this before verify_token's own explicit check ever runs
    # -- both layers independently guarantee no caller is ever authenticated
    # without a subject claim.
    payload = _payload()
    del payload["sub"]
    token = jwt.encode(payload, _SECRET, algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        verify_token(token)


def test_verify_token_rejects_a_token_with_an_empty_sub_claim():
    # A present-but-empty "sub" satisfies PyJWT's require-claim check (the
    # key exists) but must still be rejected -- this is verify_token's own
    # explicit falsy check, a distinct code path from the test above.
    token = _token(sub="")

    with pytest.raises(UnauthorizedError, match="subject"):
        verify_token(token)


# ---------------------------------------------------------------------------
# wrong audience
# ---------------------------------------------------------------------------


def test_verify_token_rejects_a_token_with_the_wrong_audience():
    token = _token(aud="some-other-service")

    with pytest.raises(UnauthorizedError):
        verify_token(token)


def test_verify_token_rejects_a_token_with_no_audience_claim():
    payload = _payload()
    del payload["aud"]
    token = jwt.encode(payload, _SECRET, algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        verify_token(token)


# ---------------------------------------------------------------------------
# malformed / unparseable token
# ---------------------------------------------------------------------------


def test_verify_token_rejects_a_malformed_token():
    with pytest.raises(UnauthorizedError):
        verify_token("this-is-not-a-jwt-at-all")


def test_verify_token_rejects_an_empty_string():
    with pytest.raises(UnauthorizedError):
        verify_token("")


def test_verify_token_rejects_a_token_with_a_tampered_payload():
    # Flip a character in the payload segment -- signature no longer matches
    # the (unchanged) header/signature, so this must fail signature
    # verification rather than silently decoding a modified claim set.
    token = _token()
    header_b64, payload_b64, sig_b64 = token.split(".")
    tampered_payload = payload_b64[:-1] + ("A" if payload_b64[-1] != "A" else "B")
    tampered = f"{header_b64}.{tampered_payload}.{sig_b64}"

    with pytest.raises(UnauthorizedError):
        verify_token(tampered)


# ---------------------------------------------------------------------------
# algorithm confusion: alg=none
# ---------------------------------------------------------------------------


def test_verify_token_rejects_an_alg_none_token():
    # The classic JWT algorithm-confusion attack: a token that declares
    # alg="none" and carries no signature at all, hoping a lenient verifier
    # skips signature checking entirely. decode_token always resolves a
    # signing key and calls jwt.decode(..., algorithms=[algorithm]) with the
    # header's own declared algorithm forced into an HS-secret lookup (since
    # "none" doesn't start with "HS", it falls into the asymmetric branch,
    # which requires SUPABASE_URL -- unset in tests -- and is rejected before
    # any signature is even considered). Either way this must never be
    # accepted.
    unsigned = jwt.encode(_payload(), key="", algorithm="none")

    with pytest.raises(UnauthorizedError):
        verify_token(unsigned)


def test_verify_token_rejects_an_alg_none_token_even_disguised_as_hs256_claims():
    # Belt-and-suspenders: an attacker who strips the signature but keeps
    # the original HS256 header (rather than declaring "none") produces a
    # token PyJWT still refuses to accept without a valid signature -- this
    # is really the "tampered payload" / "wrong secret" guarantee restated
    # for the specific case of a missing signature segment.
    token = _token()
    header_b64, payload_b64, _sig_b64 = token.split(".")
    unsigned = f"{header_b64}.{payload_b64}."

    with pytest.raises(UnauthorizedError):
        verify_token(unsigned)


# ---------------------------------------------------------------------------
# asymmetric algorithm without SUPABASE_URL configured
# ---------------------------------------------------------------------------


def test_decode_token_rejects_an_asymmetric_token_when_jwks_is_not_configured(monkeypatch):
    # Deliberately monkeypatches _jwks_client() itself (not settings.
    # SUPABASE_URL) to force the "no JWKS configured" branch: settings.
    # SUPABASE_URL is NOT reliably empty here -- a developer's own .env
    # commonly has a real Supabase project configured for local dev, and
    # _jwks_client() is @lru_cache'd, so even patching settings.SUPABASE_URL
    # wouldn't undo an already-cached real client from an earlier call in
    # this process. Patching the function itself sidesteps both problems.
    import app.core.security as security_module

    monkeypatch.setattr(security_module, "_jwks_client", lambda: None)
    # Built by hand (not jwt.encode(), which signs using whatever algorithm
    # the header ends up declaring and would require a real RSA key) --
    # decode_token only ever reads this header via get_unverified_header()
    # before it decides which branch to take, so a syntactically-valid
    # header with a throwaway payload/signature is all this needs: the
    # point is that it must fail for "no JWKS configured", before any
    # signature is even considered.
    import base64
    import json

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header_b64 = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    payload_b64 = _b64url(json.dumps(_payload()).encode())
    token = f"{header_b64}.{payload_b64}.fake-signature"

    with pytest.raises(UnauthorizedError, match="not configured"):
        decode_token(token)


# ---------------------------------------------------------------------------
# HS256 secret not configured
# ---------------------------------------------------------------------------


def test_decode_token_rejects_hs_tokens_when_secret_is_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")

    with pytest.raises(UnauthorizedError, match="not configured"):
        decode_token(_token())
