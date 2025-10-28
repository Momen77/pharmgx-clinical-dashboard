"""Profile builder UI: uses user-created profile as base with enrichment modes."""
from __future__ import annotations

import streamlit as st


def render_profile_controls():
    st.subheader("Patient Profile Source")
    mode = st.radio(
        "Choose profile base",
        ["Manual (dashboard form)", "Auto-generate", "None"],
        index=0,
        horizontal=True,
    )

    st.subheader("Enrichment before linking")
    enrich = st.radio(
        "Conditions/medications/labs",
        ["Auto (by age/lifestyle)", "Manual (enter now)", "None"],
        index=0,
        horizontal=True,
    )

    return mode, enrich


def render_manual_enrichment_forms():
    conditions = []
    medications = []
    labs = {}

    with st.expander("Add conditions"):
        name = st.text_input("Condition name")
        code = st.text_input("SNOMED code (optional)")
        if st.button("Add condition") and name:
            conditions.append({"rdfs:label": name, "snomed:code": code})
            st.success("Condition added")

    with st.expander("Add medications"):
        drug = st.text_input("Medication name")
        if st.button("Add medication") and drug:
            medications.append({"schema:name": drug})
            st.success("Medication added")

    with st.expander("Add labs"):
        alt = st.number_input("ALT (U/L)", min_value=0.0, value=25.0)
        ast = st.number_input("AST (U/L)", min_value=0.0, value=22.0)
        crcl = st.number_input("Creatinine clearance (mL/min/1.73m²)", min_value=0.0, value=95.0)
        labs = {"liver": {"alt": alt, "ast": ast}, "kidney": {"creatinine_clearance": crcl}}

    return conditions, medications, labs


