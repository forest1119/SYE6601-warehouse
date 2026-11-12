"""Single official runtime entry. No import of historical ticket_tools.

The selection table binds frozen upstream synthetic ticket datasets to the
corresponding raw-material bundle; it is environment setup, not a business label.
The builder only receives actual query receipts, never this setup configuration.
"""
from raw_evidence import RawEvidenceTools
from vendor.pr5_dynamic.cases import make_case

_TICKET_FIXTURES = {
    'bundle-01': 'DYN-01', 'bundle-02': 'NO-TICKET', 'bundle-03': 'REFERRAL',
    'bundle-04': 'AMOUNT', 'bundle-05': 'LATE-TICKET', 'bundle-06': 'BOUNDARY',
    'bundle-07': 'MISSING-TICKET', 'bundle-08': 'MAINTENANCE',
    'bundle-09': 'CONFLICT', 'bundle-10': 'EMPTY-CONTRACT', 'bundle-11': 'REFERRAL',
}


def create_provider(bundle_id='bundle-01', *, pr5_ticket_provider=None, **options):
    """Use injected PR5 provider, or the pinned unmodified PR5 fixture provider.

    Task identities for bundled examples are C-DEMO/I-DEMO. A production/other
    synthetic dataset requires matching materials, not an identity substitution.
    """
    if bundle_id not in _TICKET_FIXTURES:
        raise ValueError('Unknown runtime bundle')
    if pr5_ticket_provider is None:
        _, pr5_ticket_provider = make_case(_TICKET_FIXTURES[bundle_id])
    return RawEvidenceTools(bundle_id, ticket_provider=pr5_ticket_provider, **options)


def query(source, task, page=None):
    """Convenience one-shot; create_provider() once per run is recommended.
    No shared session state or auto-pagination. TICKET_DB always delegates PR5.
    """
    return create_provider()(source, task, page)
