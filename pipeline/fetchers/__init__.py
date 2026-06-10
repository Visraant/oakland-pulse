"""Fetcher registry: maps a source `type` in sources.yaml to a function.

Every fetcher takes the source dict from sources.yaml and returns a small
summary dict: {"records": int, "note": str}. Output is written to
data/<output> by the fetcher itself via utils.write_output().
"""
from . import bls, census, cre, oakland_finance, oakland_pdf_lists, socrata

REGISTRY = {
    "socrata": socrata.fetch,
    "bls": bls.fetch,
    "fred": census.fetch_fred,        # lives in census.py with other API fetchers
    "census_bfs": census.fetch_bfs,
    "oakland_pdf_list": oakland_pdf_lists.fetch,
    "oakland_finance_pdf": oakland_finance.fetch,
    "cbre_figures": cre.fetch_cbre,
    "cushman_marketbeat": cre.fetch_cushman,
}
