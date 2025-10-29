"""
D3.js JSON-LD Visualizer for Streamlit
Renders a JSON-LD graph as an interactive radial tree.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from rdflib import Graph, URIRef
from collections import defaultdict


def get_node_label(g, node_uri):
    """Finds a human-readable label for a given node URI."""
    # Try common labeling properties
    for prop in [
        URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
        URIRef("http://schema.org/name"),
        URIRef("http://xmlns.com/foaf/0.1/name"),
        URIRef("http://schema.org/identifier"),
    ]:
        label = g.value(subject=node_uri, predicate=prop)
        if label:
            return str(label)
    # Fallback to a shortened URI
    return str(node_uri).split('/')[-1].split('#')[-1]


def jsonld_to_hierarchy(jsonld_data: dict):
    """Converts flat JSON-LD to a hierarchical structure for D3.

    Enhancements:
    - Adds supplemental sections for Ethnicity, Ethnicity-aware Medications, and Variant Population Context
      so users can visually understand new patient-specific connections that are literals (not IRIs) in JSON-LD.
    """
    g = Graph().parse(data=json.dumps(jsonld_data), format="json-ld")

    # Find the root node (the patient)
    root_node = None
    for s, p, o in g:
        if (p, o) == (URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://xmlns.com/foaf/0.1/Person")):
            root_node = s
            break

    if not root_node:
        return {"name": "No Patient Root Found", "children": []}

    # Build hierarchy recursively
    def build_children(node_uri, visited):
        if node_uri in visited:
            return None  # Avoid cycles
        visited.add(node_uri)

        children = []
        for _, p, o in g.triples((node_uri, None, None)):
            if isinstance(o, URIRef):
                child_node = build_children(o, visited.copy())
                if child_node:
                    children.append(child_node)

        node_type = str(g.value(subject=node_uri, predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")) or "")
        node_label = get_node_label(g, node_uri)

        # Assign color based on type
        color = "#1f77b4" # Default blue
        if "Gene" in node_type: color = "#2ca02c" # Green
        if "Variant" in node_type: color = "#ff7f0e" # Orange
        if "Drug" in node_type or "drug" in node_label.lower(): color = "#d62728" # Red
        if "Disease" in node_type or "disease" in node_label.lower(): color = "#9467bd" # Purple

        return {
            "name": node_label,
            "uri": str(node_uri),
            "color": color,
            "children": children if children else None
        }

    base = build_children(root_node, set())

    # If base failed, return
    if not isinstance(base, dict):
        return base

    # Helper: ensure children list exists
    def ensure_children(node: dict):
        if node.get("children") is None:
            node["children"] = []
        return node["children"]

    # Supplemental sections extracted from original JSON (not RDF triples)
    extra_links = []  # [{"source": uri, "target": uri, "label": str, "color": str}]
    try:
        ci = jsonld_data.get("clinical_information", {}) or jsonld_data.get("clinicalInformation", {})
        demo = ci.get("demographics", {}) if isinstance(ci, dict) else {}
        # 1) Ethnicity section
        eth_items = []
        # Prefer enriched ethnicity_snomed if present
        for e in demo.get("ethnicity_snomed", []) or []:
            label = e.get("label") or "Ethnicity"
            uri = e.get("snomed:uri")
            eth_items.append({
                "name": f"{label}",
                "uri": uri or f"pgx:ethnicity:{label}",
                "color": "#17becf",
                "children": None
            })
        # Fallback to raw labels
        if not eth_items:
            for label in demo.get("ethnicity", []) or []:
                eth_items.append({
                    "name": f"{label}",
                    "uri": f"pgx:ethnicity:{label}",
                    "color": "#17becf",
                    "children": None
                })
        if eth_items:
            ensure_children(base).append({
                "name": "Ethnicity",
                "uri": "pgx:section:ethnicity",
                "color": "#17becf",
                "children": eth_items
            })

        # 2) Ethnicity-aware Medication Considerations
        adj = jsonld_data.get("ethnicity_medication_adjustments", [])
        if isinstance(adj, list) and adj:
            nodes = []
            for a in adj:
                drug = a.get("drug", "Medication")
                uri = a.get("snomed:uri") or f"pgx:adj:{drug}"
                child_items = []
                for k in ("gene", "adjustment", "strength", "rationale"):
                    v = a.get(k)
                    if v:
                        child_items.append({
                            "name": f"{k}: {v}",
                            "uri": f"pgx:adj:{drug}:{k}",
                            "color": "#8c564b",
                            "children": None
                        })
                nodes.append({
                    "name": drug,
                    "uri": uri,
                    "color": "#8c564b",
                    "children": child_items or None
                })
                # Link medication suggestion to the patient root as a semantic edge
                if uri:
                    extra_links.append({
                        "source": str(root_node),
                        "target": uri,
                        "label": "suggestion",
                        "color": "#8c564b"
                    })
            ensure_children(base).append({
                "name": "Ethnicity-aware Medications",
                "uri": "pgx:section:ethno_meds",
                "color": "#8c564b",
                "children": nodes
            })

        # 3) Variant Population Context (top-level summary)
        var_items = []
        variants = jsonld_data.get("variants", [])
        if isinstance(variants, list) and variants:
            # Limit to first 20 variants for readability
            for v in variants[:20]:
                vid = v.get("rsid") or v.get("variant_id") or v.get("id") or "Variant"
                node_children = []
                # Patient freq
                ppf = v.get("patient_population_frequency")
                if isinstance(ppf, (int, float)):
                    node_children.append({
                        "name": f"Patient AF: {round(ppf*100,1)}%",
                        "uri": f"pgx:var:{vid}:patient_af",
                        "color": "#7f7f7f",
                        "children": None
                    })
                # Top pops (show at most 2 non-null highest)
                freqs = v.get("population_frequencies") or {}
                if isinstance(freqs, dict):
                    non_null = [(k, freqs.get(k)) for k in freqs.keys() if isinstance(freqs.get(k), (int, float))]
                    non_null.sort(key=lambda kv: kv[1], reverse=True)
                    for k, val in non_null[:2]:
                        node_children.append({
                            "name": f"{k}: {round(val*100,1)}%",
                            "uri": f"pgx:var:{vid}:pop:{k}",
                            "color": "#7f7f7f",
                            "children": None
                        })
                context = v.get("ethnicity_context")
                if context:
                    node_children.append({
                        "name": context,
                        "uri": f"pgx:var:{vid}:context",
                        "color": "#7f7f7f",
                        "children": None
                    })
                var_items.append({
                    "name": str(vid),
                    "uri": f"pgx:var:{vid}",
                    "color": "#ff7f0e",
                    "children": node_children or None
                })
                # Create extra links from variants to drugs and diseases if URIs exist
                for d in v.get("drugs", []) or []:
                    duri = d.get("snomed:uri")
                    if duri:
                        extra_links.append({
                            "source": f"pgx:var:{vid}",
                            "target": duri,
                            "label": "affects",
                            "color": "#d62728"
                        })
                for dis in v.get("diseases", []) or []:
                    disuri = dis.get("snomed:uri")
                    if disuri:
                        extra_links.append({
                            "source": f"pgx:var:{vid}",
                            "target": disuri,
                            "label": "associated",
                            "color": "#9467bd"
                        })
        if var_items:
            ensure_children(base).append({
                "name": "Variant Population Context",
                "uri": "pgx:section:variant_pop",
                "color": "#7f7f7f",
                "children": var_items
            })

        # 4) Full Variants list (synthetic tree) to reflect JSON-LD content if RDF doesn't include them
        full_variant_nodes = []
        if isinstance(variants, list) and variants:
            for v in variants[:50]:  # cap to 50 for performance
                vid = v.get("rsid") or v.get("variant_id") or v.get("id") or "Variant"
                vuri = f"pgx:var:{vid}"
                vchildren = []
                # Basic props
                if v.get("gene"):
                    vchildren.append({
                        "name": f"Gene: {v.get('gene')}",
                        "uri": f"{vuri}:gene",
                        "color": "#2ca02c",
                        "children": None
                    })
                if v.get("clinical_significance"):
                    vchildren.append({
                        "name": f"Significance: {v.get('clinical_significance')}",
                        "uri": f"{vuri}:sig",
                        "color": "#ff7f0e",
                        "children": None
                    })
                # Drugs
                for d in v.get("drugs", []) or []:
                    dname = d.get("name") or "Drug"
                    duri = d.get("snomed:uri") or f"{vuri}:drug:{dname}"
                    vchildren.append({
                        "name": f"Drug: {dname}",
                        "uri": duri,
                        "color": "#d62728",
                        "children": None
                    })
                # Diseases
                for dis in v.get("diseases", []) or []:
                    dlabel = dis.get("name") or "Disease"
                    disuri = dis.get("snomed:uri") or f"{vuri}:disease:{dlabel}"
                    vchildren.append({
                        "name": f"Disease: {dlabel}",
                        "uri": disuri,
                        "color": "#9467bd",
                        "children": None
                    })
                # Attach population context summary if present
                if isinstance(v.get("population_frequencies"), dict):
                    vchildren.append({
                        "name": "Pop Frequencies",
                        "uri": f"{vuri}:popfreq",
                        "color": "#7f7f7f",
                        "children": None
                    })
                full_variant_nodes.append({
                    "name": str(vid),
                    "uri": vuri,
                    "color": "#ff7f0e",
                    "children": vchildren or None
                })
        if full_variant_nodes:
            ensure_children(base).append({
                "name": "Variants",
                "uri": "pgx:section:variants",
                "color": "#ff7f0e",
                "children": full_variant_nodes
            })
        # Variant-linking provided links, if any
        vlinks = (jsonld_data.get("variant_linking") or {}).get("links") or {}
        # Expect dicts like medication_to_variant: [{"medication_uri": uri, "variant_uri": uri}]
        try:
            for entry in vlinks.get("drug_to_variant", []) or []:
                s = entry.get("drug_uri") or entry.get("medication_uri")
                t = entry.get("variant_uri")
                if s and t:
                    extra_links.append({
                        "source": s,
                        "target": t,
                        "label": "drug-variant",
                        "color": "#d62728"
                    })
            for entry in vlinks.get("medication_to_variant", []) or []:
                s = entry.get("medication_uri")
                t = entry.get("variant_uri")
                if s and t:
                    extra_links.append({
                        "source": s,
                        "target": t,
                        "label": "med-variant",
                        "color": "#d62728"
                    })
            for entry in vlinks.get("condition_to_disease", []) or []:
                s = entry.get("condition_uri")
                t = entry.get("disease_uri")
                if s and t:
                    extra_links.append({
                        "source": s,
                        "target": t,
                        "label": "condition-disease",
                        "color": "#9467bd"
                    })
        except Exception:
            pass
    except Exception:
        # If any of the supplemental sections fails, still return the base tree
        pass

    # Attach extra links for the renderer to pick up
    base["_extraLinks"] = extra_links
    return base


def get_node_details(jsonld_data: dict, node_uri: str):
    """Extracts all properties of a specific node from the graph."""
    g = Graph().parse(data=json.dumps(jsonld_data), format="json-ld")
    uri_ref = URIRef(node_uri)
    details = {}
    for _, p, o in g.triples((uri_ref, None, None)):
        prop_name = str(p).split('/')[-1].split('#')[-1]
        prop_value = str(o)
        if prop_name not in details:
            details[prop_name] = []
        details[prop_name].append(prop_value)
    return details


def render_d3_visualization(d3_data: dict):
    """Renders the D3.js radial tree in Streamlit."""
    
    # Convert Python dict to JSON string for JS
    d3_json = json.dumps(d3_data)
    # Extract extra semantic links if present
    extra_links = d3_data.get("_extraLinks", []) if isinstance(d3_data, dict) else []
    extra_links_json = json.dumps(extra_links)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          margin: 0;
          font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          color: #1f2a37;
          background: transparent; /* match Streamlit app background */
        }}
        #container {{
          display: grid;
          grid-template-columns: 260px 1fr;
          gap: 16px;
          padding: 8px;
        }}
        #sidebar {{
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 14px;
          box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }}
        #legend h3, #controls h3 {{
          font-size: 14px;
          margin: 0 0 8px 0;
          color: #374151;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 12px; color: #4b5563; }}
        .legend-swatch {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}
        .legend-swatch.dashed {{ width: 28px; height: 0; border-bottom: 3px dashed #9ca3af; border-radius: 0; margin-right: 6px; }}
        .control-item {{ display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 12px; color: #4b5563; }}
        #chart-wrapper {{
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          box-shadow: 0 1px 2px rgba(0,0,0,0.04);
          padding: 8px;
        }}
        #chart {{
          width: 100%;
          height: 900px;
        }}
        .node circle {{ cursor: pointer; stroke: #1f2937; stroke-width: 1px; filter: drop-shadow(0 1px 1px rgba(0,0,0,.08)); }}
        .node circle:hover {{ stroke-width: 2px; }}
        .node text {{ font: 12px sans-serif; cursor: pointer; fill: #111827; }}
        .link {{ fill: none; stroke: #e5e7eb; stroke-width: 1.5px; }}
        .extra-links path {{ filter: drop-shadow(0 0 1px rgba(0,0,0,.08)); }}
        #tooltip {{ position: fixed; pointer-events: none; background: #111827; color: #f9fafb; padding: 6px 8px; border-radius: 6px; font-size: 12px; opacity: 0; transition: opacity .15s ease; z-index: 10; }}
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
            <div class="legend-item"><span class="legend-swatch" style="background:#9467bd"></span> Disease</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#17becf"></span> Ethnicity</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#8c564b"></span> Med Suggestion</div>
            <div class="legend-item"><span class="legend-swatch dashed"></span> Extra semantic link</div>
          </div>
          <div id="controls" style="margin-top:14px;">
            <h3>Overlays</h3>
            <label class="control-item"><input type="checkbox" id="toggle-affects" checked> Variant → Drug</label>
            <label class="control-item"><input type="checkbox" id="toggle-associated" checked> Variant → Disease</label>
            <label class="control-item"><input type="checkbox" id="toggle-suggestion" checked> Patient → Suggestion</label>
            <label class="control-item"><input type="checkbox" id="toggle-vlinks" checked> Variant Linking</label>
          </div>
        </div>
        <div id="chart-wrapper"><div id="chart"></div></div>
      </div>
      <div id="tooltip"></div>
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <script>
        const width = 900;
        const height = 900;
        const cx = width * 0.5;
        const cy = height * 0.5;
        const radius = Math.min(width, height) / 2 - 60;

        const tree = d3.tree()
            .size([2 * Math.PI, radius])
            .separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);

        const data = {d3_json};
        const extraLinks = {extra_links_json};

        const svg = d3.select("#chart").append("svg")
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [-cx, -cy, width, height])
            .attr("style", "width: 100%; height: auto; font: 12px sans-serif;");

        const g = svg.append("g");

        // Collapsible tree setup
        const root = d3.hierarchy(data);
        function collapse(d) {{
          if (d.children) {{
            d._children = d.children;
            d._children.forEach(collapse);
            d.children = null;
          }}
        }}
        collapse(root); // collapse all; user expands gradually

        const linkLayerTree = g.append("g").attr("class", "tree-links");
        const nodeLayer = g.append("g").attr("class", "tree-nodes");
        const linkLayerExtra = g.append("g").attr("class", "extra-links");

        function update(source) {{
          const layoutRoot = tree(root);

          // LINKS
          const links = linkLayerTree.selectAll("path").data(layoutRoot.links(), d => d.target.data.uri + '-' + d.target.depth);
          links.join(
            enter => enter.append("path")
            .attr("fill", "none")
            .attr("stroke", "#ccc")
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", 1.5)
              .attr("d", d3.linkRadial().angle(d => d.x).radius(d => d.y)),
            update => update.attr("d", d3.linkRadial().angle(d => d.x).radius(d => d.y)),
            exit => exit.remove()
          );

          // NODES
          const nodes = nodeLayer.selectAll("g").data(layoutRoot.descendants(), d => d.data.uri + '-' + d.depth);
          const nodesEnter = nodes.enter().append("g")
            .attr("transform", d => `rotate(${{d.x * 180 / Math.PI - 90}}) translate(${{d.y}},0)`)
            .on("click", (event, d) => {{
              if (d.children) {{ d._children = d.children; d.children = null; }}
              else {{ d.children = d._children; d._children = null; }}
              update(d);
            }})
            .on("mouseenter", (event, d) => {{
                const tip = document.getElementById('tooltip');
                const name = d?.data?.name || '';
                const uri = d?.data?.uri || '';
                tip.innerHTML = `<div style=\"font-weight:600;margin-bottom:2px;\">${{name}}</div><div style=\"opacity:.8;max-width:360px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;\">${{uri}}</div>`;
                tip.style.opacity = 1;
                tip.style.left = (event.clientX + 10) + 'px';
                tip.style.top = (event.clientY + 10) + 'px';
            }})
            .on("mousemove", (event) => {{
                const tip = document.getElementById('tooltip');
                tip.style.left = (event.clientX + 10) + 'px';
                tip.style.top = (event.clientY + 10) + 'px';
            }})
            .on("mouseleave", () => {{
                const tip = document.getElementById('tooltip');
                tip.style.opacity = 0;
            }});

          nodesEnter.append("circle")
            .attr("fill", d => d.data.color || ((d.children || d._children) ? "#555" : "#999"))
            .attr("r", 4.5);

          nodesEnter.append("text")
            .attr("dy", "0.31em")
            .attr("x", d => d.x < Math.PI === !(d.children || d._children) ? 6 : -6)
            .attr("text-anchor", d => d.x < Math.PI === !(d.children || d._children) ? "start" : "end")
            .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
            .text(d => d.data.name)
            .clone(true).lower()
            .attr("stroke", "white");

          nodes.merge(nodesEnter)
            .attr("transform", d => `rotate(${{d.x * 180 / Math.PI - 90}}) translate(${{d.y}},0)`)
            .select("circle")
              .attr("fill", d => d.data.color || ((d.children || d._children) ? "#555" : "#999"));

          nodes.exit().remove();

          // EXTRA LINKS (respecting toggles and current visibility)
          const uriToNode = new Map();
          layoutRoot.descendants().forEach(d => { if (d.data && d.data.uri) { uriToNode.set(d.data.uri, d); } });
          const extra = extraLinks.filter(l => uriToNode.has(l.source) && uriToNode.has(l.target));
          function drawExtraLinks() {
            linkLayerExtra.selectAll("path").remove();
            const showAffects = document.getElementById('toggle-affects')?.checked ?? true;
            const showAssoc = document.getElementById('toggle-associated')?.checked ?? true;
            const showSuggest = document.getElementById('toggle-suggestion')?.checked ?? true;
            const showVlinks = document.getElementById('toggle-vlinks')?.checked ?? true;
            const allowed = new Set();
            if (showAffects) allowed.add('affects');
            if (showAssoc) allowed.add('associated');
            if (showSuggest) allowed.add('suggestion');
            if (showVlinks) { allowed.add('drug-variant'); allowed.add('med-variant'); allowed.add('condition-disease'); }
            const filtered = extra.filter(d => allowed.has(d.label));
            if (filtered.length === 0) return;
            linkLayerExtra.selectAll("path")
              .data(filtered)
              .join("path")
                .attr("stroke", d => d.color || "#999")
                .attr("stroke-dasharray", "6,3")
                .attr("fill", "none")
                .attr("opacity", 0.9)
                .attr("d", d => {
                  const s = uriToNode.get(d.source);
                  const t = uriToNode.get(d.target);
                  const sx = Math.cos(s.x - Math.PI / 2) * s.y;
                  const sy = Math.sin(s.x - Math.PI / 2) * s.y;
                  const tx = Math.cos(t.x - Math.PI / 2) * t.y;
                  const ty = Math.sin(t.x - Math.PI / 2) * t.y;
                  return `M ${sx},${sy} L ${tx},${ty}`;
                });
          }
          drawExtraLinks();
          ['toggle-affects','toggle-associated','toggle-suggestion','toggle-vlinks'].forEach(id => {
            const el = document.getElementById(id);
            if (el && !el._bound) { el.addEventListener('change', drawExtraLinks); el._bound = true; }
          });
        }

        update(root);

        // Zooming
        const zoom = d3.zoom().on("zoom", (event) => {{
            g.attr("transform", event.transform);
        }});
        svg.call(zoom);

        // Extra semantic links are drawn per update() so they respect collapsed nodes
        // We hook into update() by redefining it to also draw overlays

      </script>
    </body>
    </html>
    """
    components.html(html_template, height=900, scrolling=False)