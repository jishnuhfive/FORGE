"""Opt-in inspector investigation: authenticated GET evidence, never a proposal."""

import logging

import httpx2 as httpx

from forge_api.auth.provider import ProviderError
from forge_api.auth.runtime import AuthRuntime
from forge_api.cad_edits.domain import EditError
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.eligibility import EligibilityRejected
from forge_api.integrations.onshape.service import read_permission
from forge_api.integrations.onshape.write_client import SafeEditClient

logger = logging.getLogger("forge.onshape.safe_edit")


def probe(
    auth: AuthRuntime,
    transport: httpx.Client,
    reference: WorkspaceReference,
    user_id: str,
) -> None:
    # Defense in depth if mutable test settings or a direct internal call bypass
    # startup validation. This never calls the mutation method or writes records.
    if (
        auth.settings.environment != "development"
        or not auth.settings.forge_safe_edit_diagnostics_enabled
        or auth.settings.forge_cad_writes_enabled
    ):
        return
    if read_permission(auth, user_id) is not True:
        logger.warning("safe_edit_probe outcome=read_permission_unknown_or_missing")
        return
    try:
        token = auth.tokens.get_valid_onshape_access_token(user_id)
        SafeEditClient(auth.settings, transport, token).evidence(reference)
    except EligibilityRejected:
        # The projection already emitted only closed fixed metadata.
        return
    except EditError, ProviderError:
        logger.warning("safe_edit_probe outcome=read_unavailable")
        return
    logger.warning("safe_edit_probe outcome=eligible_no_proposal_no_write")
