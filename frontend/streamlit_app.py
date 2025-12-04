"""Minimal Streamlit client for the Keymark Heat Pumps API."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

DEFAULT_API_BASE = "http://localhost:8000"
CLIMATE_OPTIONS = {
    "Average": "average",
    "Colder": "colder",
    "Warmer": "warmer",
}


def get_api_base() -> str:
    """Prefer Streamlit secrets/env var overrides for API base URL."""
    # Streamlit raises when no secrets file exists, so guard the lookup.
    secret_value: str | None = None
    try:
        secret_value = st.secrets["api_base"]
    except Exception:  # noqa: BLE001 - secrets module raises custom errors
        secret_value = None

    env_value = os.environ.get("API_BASE_URL")
    return secret_value or env_value or DEFAULT_API_BASE


def fetch_measurements(params: dict[str, Any]) -> dict[str, Any]:
    """Fetch paginated measurements from the FastAPI backend."""
    return _request_api("/measurements", params)


def fetch_heat_pumps(params: dict[str, Any]) -> dict[str, Any]:
    """Fetch heat pump summaries for dropdown selection."""
    return _request_api("/heat-pumps", params)


@st.cache_data(ttl=600)
def load_heat_pumps(cold_only: bool, search_term: str) -> list[dict[str, Any]]:
    """Load and cache heat pump summaries for selector widgets."""
    params: dict[str, Any] = {"limit": 5000}
    if cold_only:
        params["has_cold_climate"] = True
    if search_term:
        params["search"] = search_term

    payload = fetch_heat_pumps(params)
    return payload.get("data", [])


def _request_api(path: str, params: dict[str, Any]) -> dict[str, Any]:
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}{path}"
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def main() -> None:
    st.set_page_config(page_title="Keymark Heat Pumps", layout="wide")
    st.title("Keymark Heat Pump Explorer")
    st.caption("Streamlit prototype backed by DuckDB + FastAPI")

    with st.sidebar:
        st.header("Heat pump selector")
        cold_only = st.checkbox("Only show colder-climate models", value=False)
        search_term = st.text_input("Search manufacturer or model")
        heat_pumps = load_heat_pumps(cold_only, search_term)

        if heat_pumps:
            labels = [
                f"{hp['manufacturer_name']} – {hp['model_name']} ({hp['variant_name']})"
                for hp in heat_pumps
            ]
            options = ["All heat pumps", *labels]
            selected_label = st.selectbox("Heat pump", options)
            selected_hp = None if selected_label == options[0] else heat_pumps[labels.index(selected_label)]
        else:
            st.warning("No heat pumps match the current selector.")
            selected_hp = None

        st.divider()
        st.header("Measurement filters")
        climate_default = list(CLIMATE_OPTIONS.keys())
        climate_choice = st.multiselect(
            "Climate zones",
            climate_default,
            default=climate_default,
            help="Choose one or more EN 14825 climate zones",
        )
        en_code = st.text_input("EN code")
        dimension = st.text_input("Dimension code")
        limit = st.slider("Rows", min_value=10, max_value=500, value=100, step=10)
        offset = st.number_input("Offset", min_value=0, value=0, step=limit)
        fetch_button = st.button("Fetch data", use_container_width=True)

    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if selected_hp:
        params["manufacturer"] = selected_hp["manufacturer_name"]
        params["model"] = selected_hp["model_name"]
        params["variant"] = selected_hp["variant_name"]
    if en_code:
        params["en_code"] = en_code
    if dimension:
        params["dimension"] = dimension
    if climate_choice and len(climate_choice) < len(CLIMATE_OPTIONS):
        params["climates"] = [CLIMATE_OPTIONS[label] for label in climate_choice]

    if cold_only and "climates" not in params:
        params["climates"] = [CLIMATE_OPTIONS["Colder"]]

    if fetch_button:
        with st.spinner("Loading data from API..."):
            try:
                data = fetch_measurements(params)
            except httpx.HTTPError as exc:
                st.error(f"Request failed: {exc}")
                return

        meta = data.get("meta", {})
        st.subheader("Results")
        st.write(
            f"Total measurements: {meta.get('total', 'unknown')} | "
            f"Showing {len(data.get('data', []))} rows starting at offset {meta.get('offset', 0)}"
        )

        if not data.get("data"):
            st.info("No rows matched the current filters.")
            return

        st.dataframe(data["data"], use_container_width=True)
        st.json(meta, expanded=False)


if __name__ == "__main__":
    main()
