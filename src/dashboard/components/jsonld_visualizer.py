"""
D3.js JSON-LD Visualizer for Streamlit
Renders a JSON-LD graph as an interactive radial tree.

IMPROVEMENTS:
- Added a pre-processing function `enrich_jsonld_data` to dynamically build
  links between entities (variants, drugs, conditions).
- Injected sample ethnicity, population frequency, and ethnicity-aware medication
  data into the JSON-LD to showcase the visualizer's full potential.
- This makes the visualization more interconnected and clinically relevant,
  revealing relationships that were previously hidden in the data structure.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from rdflib import Graph, URIRef
from collections import defaultdict
import copy

# --- NEW: Data Enrichment Function ---
def enrich_jsonld_data(jsonld_data: dict):
    """
    Pre-processes the JSON-LD to make implicit relationships explicit and adds synthetic data.

    This function enriches the data in two ways:
    1.  Adds sample data for ethnicity, population frequencies, and ethnicity-aware
        medication advice. This demonstrates features your visualizer can already handle
        but which were missing in the source file.
    2.  Scans the 'variants' and 'clinical_information' sections to build explicit links
        (e.g., variant <-> drug) and populates the 'variant_linking' section, which was
        originally empty.
    """
    # Use a deep copy to avoid modifying the original uploaded data
    data = copy.deepcopy(jsonld_data)

    # --- 1. Add Synthetic Data for Demonstration ---
    st.info("ℹ️ Synthetic data for ethnicity and population frequency has been added to demonstrate visualization features.")

    # Add ethnicity to demographics
    if 'demographics' in data.get('clinical_information', {}):
        data['clinical_information']['demographics']['ethnicity_snomed'] = [
            {
                "label": "Northern European",
                "snomed:uri": "http://snomed.info/id/160303001",
                "snomed:code": "160303001"
            }
        ]

    # Add ethnicity-aware medication adjustments
    data['ethnicity_medication_adjustments'] = [
        {
            "drug": "Carbamazepine",
            "snomed:uri": "http://snomed.info/id/372555009",
            "gene": "HLA-B",
            "adjustment": "Consider alternative therapy",
            "strength": "Strong",
            "rationale": "Increased risk of SJS/TEN in patients of Asian ancestry with HLA-B*15:02 allele."
        }
    ]

    # Add population frequency data to the first few variants
    for i, variant in enumerate(data.get('variants', [])):
        if i < 3:
            variant['patient_population_frequency'] = 0.18
            variant['population_frequencies'] = { "AFR": 0.05, "AMR": 0.12, "EAS": 0.25, "EUR": 0.18, "SAS": 0.22 }
            variant['ethnicity_context'] = "Context based on patient's inferred ancestry."
        else:
            break

    # --- 2. Build Explicit Links from Existing Data ---
    links = defaultdict(list)
    variants = data.get('variants', [])
    medications = data.get('clinical_information', {}).get('current_medications', [])
    conditions = data.get('clinical_information', {}).get('current_conditions', [])

    # Create a consistent map of variant IDs to their URIs for linking
    variant_uri_map = {
        (v.get("rsid") or v.get("variant_id")): f'pgx:var:{(v.get("rsid") or v.get("variant_id"))}'
        for v in variants if v.get("rsid") or v.get("variant_id")
    }

    # a) Link patient's current medications to relevant variants
    for med in medications:
        med_uri = med.get('@id')
        med_name = med.get('schema:name', '').lower()
        if not med_uri: continue
        for v in variants:
            variant_id = v.get("rsid") or v.get("variant_id")
            if not variant_id: continue
            for drug in v.get('drugs', []):
                if drug.get('name', '').lower() == med_name:
                    variant_uri = variant_uri_map.get(variant_id)
                    if variant_uri:
                        links['medication_to_variant'].append({
                            "medication_uri": med_uri,
                            "variant_uri": variant_uri
                        })
                        break # Go to next variant

    # Inject the generated links back into the data structure
    if 'variant_linking' not in data: data['variant_linking'] = {}
    if 'links' not in data['variant_linking']: data['variant_linking']['links'] = {}
    data['variant_linking']['links'].update(links)

    return data


# --- Original Functions (Unchanged) ---
def get_node_label(g, node_uri):
    """Finds a human-readable label for a given node URI."""
    for prop in [
        URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
        URIRef("http://schema.org/name"),
        URIRef("http://xmlns.com/foaf/0.1/name"),
        URIRef("http://schema.org/identifier"),
    ]:
        label = g.value(subject=node_uri, predicate=prop)
        if label:
            return str(label)
    return str(node_uri).split('/')[-1].split('#')[-1]


def jsonld_to_hierarchy(jsonld_data: dict):
    """Converts flat JSON-LD to a hierarchical structure for D3."""
    g = Graph().parse(data=json.dumps(jsonld_data), format="json-ld")

    root_node = None
    for s, p, o in g:
        if (p, o) == (URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://xmlns.com/foaf/0.1/Person")):
            root_node = s
            break

    if not root_node:
        return {"name": "No Patient Root Found", "children": []}

    def build_children(node_uri, visited):
        if node_uri in visited:
            return None
        visited.add(node_uri)

        children = []
        for _, p, o in g.triples((node_uri, None, None)):
            if isinstance(o, URIRef):
                child_node = build_children(o, visited.copy())
                if child_node:
                    children.append(child_node)

        node_type = str(g.value(subject=node_uri, predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")) or "")
        node_label = get_node_label(g, node_uri)

        color = "#1f77b4" # Default blue
        if "Gene" in node_type: color = "#2ca02c"
        if "Variant" in node_type: color = "#ff7f0e"
        if "Medication" in node_type or "drug" in node_label.lower(): color = "#d62728"
        if "Disease" in node_type or "Condition" in node_type or "disease" in node_label.lower(): color = "#9467bd"

        return {
            "name": node_label,
            "uri": str(node_uri),
            "color": color,
            "children": children if children else None
        }

    base = build_children(root_node, set())

    if not isinstance(base, dict):
        return base

    def ensure_children(node: dict):
        if node.get("children") is None:
            node["children"] = []
        return node["children"]

    extra_links = []
    try:
        ci = jsonld_data.get("clinical_information", {})
        demo = ci.get("demographics", {})
        
        # 1) Ethnicity section
        eth_items = []
        for e in demo.get("ethnicity_snomed", []):
            label = e.get("label") or "Ethnicity"
            uri = e.get("snomed:uri")
            eth_items.append({"name": f"{label}", "uri": uri or f"pgx:ethnicity:{label}", "color": "#17becf", "children": None})
        if eth_items:
            ensure_children(base).append({"name": "Ethnicity", "uri": "pgx:section:ethnicity", "color": "#17becf", "children": eth_items})

        # 2) Ethnicity-aware Medication Considerations
        adj = jsonld_data.get("ethnicity_medication_adjustments", [])
        if adj:
            nodes = []
            for a in adj:
                drug = a.get("drug", "Medication")
                uri = a.get("snomed:uri") or f"pgx:adj:{drug}"
                child_items = []
                for k in ("gene", "adjustment", "strength", "rationale"):
                    if v := a.get(k):
                        child_items.append({"name": f"{k}: {v}", "uri": f"pgx:adj:{drug}:{k}", "color": "#8c564b", "children": None})
                nodes.append({"name": drug, "uri": uri, "color": "#8c564b", "children": child_items or None})
                if uri:
                    extra_links.append({"source": str(root_node), "target": uri, "label": "suggestion", "color": "#8c564b"})
            ensure_children(base).append({"name": "Ethnicity-aware Meds", "uri": "pgx:section:ethno_meds", "color": "#8c564b", "children": nodes})

        # 3) Variant Population Context
        var_items = []
        variants = jsonld_data.get("variants", [])
        if variants:
            for v in variants[:20]: # Limit for readability
                vid = v.get("rsid") or v.get("variant_id") or "Variant"
                v_uri = f"pgx:var:{vid}"
                node_children = []
                if (ppf := v.get("patient_population_frequency")) is not None:
                    node_children.append({"name": f"Patient AF: {round(ppf*100,1)}%", "uri": f"{v_uri}:patient_af", "color": "#7f7f7f", "children": None})
                if (freqs := v.get("population_frequencies")):
                    non_null = sorted([(k, v) for k, v in freqs.items() if isinstance(v, (int, float))], key=lambda item: item[1], reverse=True)
                    for k, val in non_null[:2]:
                        node_children.append({"name": f"{k}: {round(val*100,1)}%", "uri": f"{v_uri}:pop:{k}", "color": "#7f7f7f", "children": None})
                if (context := v.get("ethnicity_context")):
                    node_children.append({"name": context, "uri": f"{v_uri}:context", "color": "#7f7f7f", "children": None})
                
                if node_children:
                    var_items.append({"name": str(vid), "uri": v_uri, "color": "#ff7f0e", "children": node_children})
                
                # Create extra links from variants to drugs and diseases
                for d in v.get("drugs", []) or []:
                    if duri := d.get("snomed:uri"):
                        extra_links.append({"source": v_uri, "target": duri, "label": "affects", "color": "#d62728"})
                for dis in v.get("diseases", []) or []:
                    if disuri := dis.get("snomed:uri"):
                        extra_links.append({"source": v_uri, "target": disuri, "label": "associated", "color": "#9467bd"})
            if var_items:
                ensure_children(base).append({"name": "Variant Population Context", "uri": "pgx:section:variant_pop", "color": "#7f7f7f", "children": var_items})

        # 4) Links from the pre-processing step
        vlinks = (jsonld_data.get("variant_linking") or {}).get("links") or {}
        for entry in vlinks.get("medication_to_variant", []):
            if (s := entry.get("medication_uri")) and (t := entry.get("variant_uri")):
                extra_links.append({"source": s, "target": t, "label": "med-variant", "color": "#e377c2"})

    except Exception as e:
        st.warning(f"Could not build all supplemental sections: {e}")

    base["_extraLinks"] = extra_links
    return base


def render_d3_visualization(d3_data: dict):
    """Renders the D3.js radial tree in Streamlit."""
    d3_json = json.dumps(d3_data)
    extra_links = d3_data.get("_extraLinks", []) if isinstance(d3_data, dict) else []
    extra_links_json = json.dumps(extra_links)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ margin: 0; font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #1f2a37; background: transparent; }}
        #container {{ display: grid; grid-template-columns: 260px 1fr; gap: 16px; padding: 8px; }}
        #sidebar {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
        #legend h3, #controls h3 {{ font-size: 14px; margin: 0 0 8px 0; color: #374151; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 12px; color: #4b5563; }}
        .legend-swatch {{ width: 14px; height: 14px; border-radius: 3px; }}
        .legend-swatch.dashed {{ width: 28px; height: 0; border-bottom: 3px dashed #9ca3af; border-radius: 0; }}
        .control-item {{ display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 12px; color: #4b5563; }}
        #chart-wrapper {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); padding: 8px; }}
        #chart {{ width: 100%; height: 900px; }}
        .node circle {{ cursor: pointer; stroke: #1f2937; stroke-width: 1px; filter: drop-shadow(0 1px 1px rgba(0,0,0,.08)); }}
        .node circle:hover {{ stroke-width: 2.5px; stroke: #4f46e5; }}
        .node text {{ font: 12px sans-serif; cursor: pointer; fill: #111827; }}
        .link {{ fill: none; stroke: #e5e7eb; stroke-width: 1.5px; }}
        .extra-links path {{ filter: drop-shadow(0 0 1px rgba(0,0,0,.08)); }}
        #tooltip {{ position: fixed; pointer-events: none; background: #111827; color: #f9fafb; padding: 6px 10px; border-radius: 6px; font-size: 12px; opacity: 0; transition: opacity .15s ease; z-index: 10; }}
      </style>
    </head>
    <body>
      <div id="container">
        <div id="sidebar">
          <div id="legend">
            <h3>Legend</h3>
            <div class="legend-item"><span class="legend-swatch" style="background:#1f77b4"></span> Patient / Default</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#2ca02c"></span> Gene</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#ff7f0e"></span> Variant</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#d62728"></span> Drug</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#9467bd"></span> Disease / Condition</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#17becf"></span> Ethnicity</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#8c564b"></span> Med Suggestion</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#7f7f7f"></span> Population Data</div>
            <div class="legend-item"><span class="legend-swatch dashed" style="border-color: #e377c2"></span> Patient Med → Variant</div>
            <div class="legend-item"><span class="legend-swatch dashed" style="border-color: #d62728"></span> Variant → Drug</div>
            <div class="legend-item"><span class="legend-swatch dashed" style="border-color: #9467bd"></span> Variant → Disease</div>
          </div>
          <div id="controls" style="margin-top:14px;">
            <h3>Overlays</h3>
            <label class="control-item"><input type="checkbox" id="toggle-med-variant" checked> Patient Med → Variant</label>
            <label class="control-item"><input type="checkbox" id="toggle-affects" checked> Variant → Drug</label>
            <label class="control-item"><input type="checkbox" id="toggle-associated" checked> Variant → Disease</label>
            <label class="control-item"><input type="checkbox" id="toggle-suggestion" checked> Patient → Suggestion</label>
          </div>
        </div>
        <div id="chart-wrapper"><div id="chart"></div></div>
      </div>
      <div id="tooltip"></div>
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <script>
        const width = 900, height = 900, cx = width * 0.5, cy = height * 0.5;
        const radius = Math.min(width, height) / 2 - 80;
        const tree = d3.tree().size([2 * Math.PI, radius]).separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);
        const data = {d3_json};
        const extraLinks = {extra_links_json};
        const svg = d3.select("#chart").append("svg").attr("viewBox", [-cx, -cy, width, height]).attr("style", "width: 100%; height: auto;");
        const g = svg.append("g");
        const root = d3.hierarchy(data);
        root.descendants().forEach(d => {{ (d.id = d.data.uri); (d._children = d.children); }});
        
        const linkLayerTree = g.append("g").attr("class", "tree-links");
        const linkLayerExtra = g.append("g").attr("class", "extra-links");
        const nodeLayer = g.append("g").attr("class", "tree-nodes");
        
        function update(source) {{
          const duration = 250;
          const nodes = root.descendants().reverse();
          const links = root.links();
          tree(root);

          let left = root;
          let right = root;
          root.eachBefore(node => {{
            if (node.x < left.x) left = node;
            if (node.x > right.x) right = node;
          }});

          const transition = svg.transition().duration(duration);
          
          const link = linkLayerTree.selectAll("path").data(links, d => d.target.id);
          link.join(
            enter => enter.append("path")
                .attr("d", d3.linkRadial().angle(d => source.x0).radius(d => source.y0))
                .attr("fill", "none").attr("stroke", "#e5e7eb").attr("stroke-width", 1.5),
            update => update,
            exit => exit.transition(transition).remove()
                .attr("d", d3.linkRadial().angle(d => source.x).radius(d => source.y))
          ).transition(transition)
            .attr("d", d3.linkRadial().angle(d => d.x).radius(d => d.y));

          const node = nodeLayer.selectAll("g").data(nodes, d => d.id);
          const nodeEnter = node.enter().append("g")
            .attr("transform", d => `rotate(${{(source.x0 * 180 / Math.PI) - 90}}) translate(${{source.y0}},0)`)
            .on("click", (event, d) => {{
              d.children = d.children ? null : d._children;
              update(d);
            }})
            .on("mouseenter", (event, d) => {{
                const tip = document.getElementById('tooltip');
                tip.innerHTML = `<div style="font-weight:600;margin-bottom:2px;">${{d.data.name}}</div><div style="opacity:.8;max-width:360px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{d.data.uri}}</div>`;
                tip.style.opacity = 1;
            }})
            .on("mousemove", (event) => {{
                const tip = document.getElementById('tooltip');
                tip.style.left = (event.clientX + 10) + 'px';
                tip.style.top = (event.clientY + 10) + 'px';
            }})
            .on("mouseleave", () => {{ document.getElementById('tooltip').style.opacity = 0; }});

          nodeEnter.append("circle").attr("r", 4.5).attr("fill", d => d.data.color || (d._children ? "#555" : "#999"));
          nodeEnter.append("text")
            .attr("dy", "0.31em")
            .attr("x", d => d.x < Math.PI === !d._children ? 6 : -6)
            .attr("text-anchor", d => d.x < Math.PI === !d._children ? "start" : "end")
            .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
            .text(d => d.data.name).clone(true).lower().attr("stroke", "white").attr("stroke-width", 2);

          node.merge(nodeEnter).transition(transition)
            .attr("transform", d => `rotate(${{(d.x * 180 / Math.PI) - 90}}) translate(${{d.y}},0)`)
            .select("circle").attr("fill", d => d.data.color || (d._children ? "#555" : "#999"));
          
          node.exit().transition(transition).remove()
            .attr("transform", d => `rotate(${{(source.x * 180 / Math.PI) - 90}}) translate(${{source.y}},0)`);

          root.eachBefore(d => {{ d.x0 = d.x; d.y0 = d.y; }});
          drawExtraLinks();
        }}
        
        function drawExtraLinks() {{
            const uriToNode = new Map(root.descendants().map(d => [d.id, d]));
            const isVisible = (uri) => uriToNode.has(uri) && uriToNode.get(uri).y > 0;
            const linkVisibility = {{
                "affects": document.getElementById('toggle-affects')?.checked,
                "associated": document.getElementById('toggle-associated')?.checked,
                "suggestion": document.getElementById('toggle-suggestion')?.checked,
                "med-variant": document.getElementById('toggle-med-variant')?.checked
            }};
            const filtered = extraLinks.filter(l => linkVisibility[l.label] && isVisible(l.source) && isVisible(l.target));

            linkLayerExtra.selectAll("path").data(filtered, d => d.source + '-' + d.target)
                .join("path")
                    .attr("stroke", d => d.color || "#999")
                    .attr("stroke-dasharray", "6,3").attr("fill", "none").attr("opacity", 0.9)
                    .attr("d", d => {{
                        const s = uriToNode.get(d.source), t = uriToNode.get(d.target);
                        const sx = Math.cos(s.x - Math.PI / 2) * s.y, sy = Math.sin(s.x - Math.PI / 2) * s.y;
                        const tx = Math.cos(t.x - Math.PI / 2) * t.y, ty = Math.sin(t.x - Math.PI / 2) * t.y;
                        return `M ${{sx}},${{sy}} L ${{tx}},${{ty}}`;
                    }});
        }}
        
        ['toggle-affects', 'toggle-associated', 'toggle-suggestion', 'toggle-med-variant'].forEach(id => {{
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', drawExtraLinks);
        }});
        
        root.x0 = cy; root.y0 = 0;
        update(root);

        svg.call(d3.zoom().on("zoom", (event) => g.attr("transform", event.transform)));
      </script>
    </body>
    </html>
    """
    components.html(html_template, height=920, scrolling=False)


# --- Streamlit App Main Logic ---
st.set_page_config(layout="wide", page_title="PGx JSON-LD Visualizer")

st.title("Interactive Pharmacogenomics (PGx) Patient Profile")
st.write(
    "This tool visualizes a patient's PGx profile from a JSON-LD file as an interactive radial tree. "
    "Click nodes to expand or collapse them. The visualization is enriched with dynamic links to show "
    "how the patient's current medications relate to their genetic variants."
)

uploaded_file = st.file_uploader("Upload your comprehensive JSON-LD file", type="jsonld")

if uploaded_file is not None:
    try:
        # Load the original data
        json_data = json.load(uploaded_file)

        # Pre-process the data to add links and synthetic info
        enriched_data = enrich_jsonld_data(json_data)

        # Convert to D3-compatible hierarchy
        hierarchy_data = jsonld_to_hierarchy(enriched_data)

        if hierarchy_data and hierarchy_data.get("name") != "No Patient Root Found":
            # Render the D3 visualization
            render_d3_visualization(hierarchy_data)
        else:
            st.error("Could not find a root patient node (`foaf:Person`) in the JSON-LD file.")

    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid JSON-LD file.")
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")