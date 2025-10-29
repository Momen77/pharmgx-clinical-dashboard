"""
Enhanced D3.js JSON-LD Visualizer for Streamlit
Renders a JSON-LD pharmacogenomics graph with interactive features.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from rdflib import Graph, URIRef
from collections import defaultdict


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

        # Assign color based on type
        color = "#3b82f6"  # Default blue
        if "Gene" in node_type: color = "#10b981"  # Green
        if "Variant" in node_type: color = "#f59e0b"  # Orange
        if "Drug" in node_type or "drug" in node_label.lower(): color = "#ef4444"  # Red
        if "Disease" in node_type or "disease" in node_label.lower(): color = "#8b5cf6"  # Purple

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

    # Extract patient info for root node
    patient_name = jsonld_data.get("name", "Patient")
    base["name"] = patient_name
    base["details"] = {
        "type": "Patient",
        "id": jsonld_data.get("patient_id", ""),
        "demographics": jsonld_data.get("clinical_information", {}).get("demographics", {})
    }

    extra_links = []
    
    try:
        ci = jsonld_data.get("clinical_information", {}) or {}
        demo = ci.get("demographics", {}) if isinstance(ci, dict) else {}
        
        # 1) Clinical Conditions Section
        conditions = ci.get("current_conditions", [])
        if conditions:
            cond_nodes = []
            for cond in conditions:
                cond_nodes.append({
                    "name": cond.get("rdfs:label", "Condition"),
                    "uri": cond.get("@id", f"pgx:condition:{cond.get('snomed:code')}"),
                    "color": "#8b5cf6",
                    "details": {
                        "type": "Condition",
                        "code": cond.get("snomed:code"),
                        "definition": cond.get("skos:definition", ""),
                        "search_term": cond.get("search_term", "")
                    },
                    "children": None
                })
            ensure_children(base).append({
                "name": f"Conditions ({len(conditions)})",
                "uri": "pgx:section:conditions",
                "color": "#8b5cf6",
                "children": cond_nodes
            })

        # 2) Current Medications Section
        medications = ci.get("current_medications", [])
        if medications:
            med_nodes = []
            for med in medications:
                med_name = med.get("schema:name", med.get("rdfs:label", "Medication"))
                med_uri = med.get("@id", f"pgx:med:{med_name}")
                
                med_details = []
                if med.get("schema:dosageForm"):
                    med_details.append(f"Form: {med['schema:dosageForm']}")
                if med.get("schema:doseValue"):
                    med_details.append(f"Dose: {med['schema:doseValue']} {med.get('schema:doseUnit', '')}")
                if med.get("schema:frequency"):
                    med_details.append(f"Freq: {med['schema:frequency']}")
                
                med_children = []
                for detail in med_details:
                    med_children.append({
                        "name": detail,
                        "uri": f"{med_uri}:detail",
                        "color": "#94a3b8",
                        "children": None
                    })
                
                med_nodes.append({
                    "name": med_name,
                    "uri": med_uri,
                    "color": "#ef4444",
                    "details": {
                        "type": "Medication",
                        "purpose": med.get("purpose", ""),
                        "source": med.get("source", ""),
                        "snomed_code": med.get("snomed:code", "")
                    },
                    "children": med_children or None
                })
            ensure_children(base).append({
                "name": f"Medications ({len(medications)})",
                "uri": "pgx:section:medications",
                "color": "#ef4444",
                "children": med_nodes
            })

        # 3) Ethnicity section
        eth_items = []
        for e in demo.get("ethnicity_snomed", []) or []:
            label = e.get("label", "Ethnicity")
            uri = e.get("snomed:uri", f"pgx:ethnicity:{label}")
            eth_items.append({
                "name": label,
                "uri": uri,
                "color": "#06b6d4",
                "details": {"type": "Ethnicity", "code": e.get("snomed:code", "")},
                "children": None
            })
        
        if not eth_items:
            for label in demo.get("ethnicity", []) or []:
                eth_items.append({
                    "name": label,
                    "uri": f"pgx:ethnicity:{label}",
                    "color": "#06b6d4",
                    "children": None
                })
        
        if eth_items:
            ensure_children(base).append({
                "name": "Ethnicity",
                "uri": "pgx:section:ethnicity",
                "color": "#06b6d4",
                "children": eth_items
            })

        # 4) Ethnicity-aware Medication Adjustments
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
                            "name": f"{k.title()}: {v}",
                            "uri": f"{uri}:{k}",
                            "color": "#78716c",
                            "children": None
                        })
                nodes.append({
                    "name": drug,
                    "uri": uri,
                    "color": "#78716c",
                    "details": {"type": "Medication Adjustment", "data": a},
                    "children": child_items or None
                })
                extra_links.append({
                    "source": str(root_node),
                    "target": uri,
                    "label": "adjustment",
                    "color": "#78716c"
                })
            ensure_children(base).append({
                "name": f"Ethnicity-aware Med Adjustments ({len(nodes)})",
                "uri": "pgx:section:ethno_meds",
                "color": "#78716c",
                "children": nodes
            })

        # 5) Variants with comprehensive data
        variants = jsonld_data.get("variants", [])
        if isinstance(variants, list) and variants:
            variant_nodes = []
            for v in variants[:30]:  # Limit for performance
                vid = v.get("rsid") or v.get("variant_id") or v.get("id") or "Variant"
                vuri = f"pgx:var:rs{vid}" if vid.isdigit() else f"pgx:var:{vid}"
                vchildren = []
                
                # Gene info
                gene = v.get("gene")
                if gene:
                    vchildren.append({
                        "name": f"Gene: {gene}",
                        "uri": f"{vuri}:gene",
                        "color": "#10b981",
                        "children": None
                    })
                
                # Clinical significance
                sig = v.get("clinical_significance")
                if sig:
                    sig_color = "#ef4444" if "pathogenic" in sig.lower() else "#f59e0b"
                    vchildren.append({
                        "name": f"Significance: {sig}",
                        "uri": f"{vuri}:sig",
                        "color": sig_color,
                        "children": None
                    })
                
                # Drugs
                drugs = v.get("drugs", []) or []
                for d in drugs[:3]:  # Limit drugs shown
                    dname = d.get("name", "Drug")
                    duri = d.get("snomed:uri") or f"{vuri}:drug:{dname}"
                    vchildren.append({
                        "name": f"Drug: {dname}",
                        "uri": duri,
                        "color": "#ef4444",
                        "details": {
                            "type": "Drug",
                            "recommendation": d.get("recommendation", ""),
                            "evidence_level": d.get("evidence_level", "")
                        },
                        "children": None
                    })
                    extra_links.append({
                        "source": vuri,
                        "target": duri,
                        "label": "affects",
                        "color": "#ef4444"
                    })
                
                # Population context
                pop_freq = v.get("patient_population_frequency")
                if pop_freq:
                    vchildren.append({
                        "name": f"Pop. Frequency: {round(pop_freq*100, 2)}%",
                        "uri": f"{vuri}:popfreq",
                        "color": "#64748b",
                        "children": None
                    })
                
                # Literature count
                lit = v.get("literature", {})
                pub_count = len(lit.get("variant_specific_publications", []))
                if pub_count > 0:
                    vchildren.append({
                        "name": f"Publications: {pub_count}",
                        "uri": f"{vuri}:lit",
                        "color": "#6366f1",
                        "children": None
                    })
                
                variant_nodes.append({
                    "name": f"rs{vid}" if vid.isdigit() else str(vid),
                    "uri": vuri,
                    "color": "#f59e0b",
                    "details": {
                        "type": "Variant",
                        "data": v
                    },
                    "children": vchildren or None
                })
            
            ensure_children(base).append({
                "name": f"Genetic Variants ({len(variant_nodes)})",
                "uri": "pgx:section:variants",
                "color": "#f59e0b",
                "children": variant_nodes
            })

    except Exception as e:
        print(f"Error building supplemental sections: {e}")

    base["_extraLinks"] = extra_links
    base["_metadata"] = {
        "total_variants": len(jsonld_data.get("variants", [])),
        "total_conditions": len(ci.get("current_conditions", [])),
        "total_medications": len(ci.get("current_medications", [])),
        "patient_id": jsonld_data.get("patient_id", ""),
        "date_created": jsonld_data.get("dateCreated", "")
    }
    
    return base


def render_d3_visualization(d3_data: dict):
    """Renders the enhanced D3.js radial tree in Streamlit."""
    
    d3_json = json.dumps(d3_data)
    extra_links = d3_data.get("_extraLinks", []) if isinstance(d3_data, dict) else []
    extra_links_json = json.dumps(extra_links)
    metadata = d3_data.get("_metadata", {})
    metadata_json = json.dumps(metadata)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          color: #1e293b;
          background: #f8fafc;
          overflow: hidden;
        }}
        #container {{
          display: grid;
          grid-template-columns: 280px 1fr 340px;
          gap: 0;
          height: 100vh;
          width: 100vw;
        }}
        #sidebar, #detail-panel {{
          background: #ffffff;
          border-right: 1px solid #e2e8f0;
          overflow-y: auto;
          padding: 20px;
        }}
        #detail-panel {{
          border-right: none;
          border-left: 1px solid #e2e8f0;
        }}
        .section {{
          margin-bottom: 24px;
        }}
        .section-title {{
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #64748b;
          margin-bottom: 12px;
        }}
        .stat-card {{
          background: #f1f5f9;
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 8px;
        }}
        .stat-label {{
          font-size: 11px;
          color: #64748b;
          margin-bottom: 4px;
        }}
        .stat-value {{
          font-size: 20px;
          font-weight: 700;
          color: #1e293b;
        }}
        .legend-item {{
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 8px 0;
          font-size: 13px;
          color: #475569;
        }}
        .legend-swatch {{
          width: 16px;
          height: 16px;
          border-radius: 4px;
          flex-shrink: 0;
        }}
        .legend-swatch.dashed {{
          width: 32px;
          height: 0;
          border-bottom: 3px dashed #94a3b8;
          border-radius: 0;
        }}
        .control-item {{
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 8px 0;
          font-size: 13px;
          color: #475569;
          cursor: pointer;
          user-select: none;
        }}
        .control-item input[type="checkbox"] {{
          width: 16px;
          height: 16px;
          cursor: pointer;
        }}
        #chart-wrapper {{
          background: #ffffff;
          position: relative;
          overflow: hidden;
        }}
        #chart {{
          width: 100%;
          height: 100%;
        }}
        .node circle {{
          cursor: pointer;
          stroke: #fff;
          stroke-width: 2px;
          transition: all 0.2s;
        }}
        .node circle:hover {{
          stroke-width: 3px;
          filter: brightness(1.1);
        }}
        .node text {{
          font: 11px sans-serif;
          cursor: pointer;
          fill: #1e293b;
          user-select: none;
        }}
        .link {{
          fill: none;
          stroke: #e2e8f0;
          stroke-width: 1.5px;
        }}
        .extra-links path {{
          stroke-width: 2px;
          opacity: 0.6;
        }}
        #tooltip {{
          position: fixed;
          pointer-events: none;
          background: #1e293b;
          color: #f8fafc;
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 12px;
          opacity: 0;
          transition: opacity 0.15s;
          z-index: 100;
          max-width: 300px;
          box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }}
        .detail-content {{
          font-size: 13px;
          line-height: 1.6;
        }}
        .detail-content h3 {{
          font-size: 18px;
          font-weight: 700;
          color: #1e293b;
          margin-bottom: 16px;
        }}
        .detail-content .meta {{
          color: #64748b;
          font-size: 12px;
          margin-bottom: 16px;
        }}
        .detail-content .field {{
          margin-bottom: 12px;
        }}
        .detail-content .field-label {{
          font-weight: 600;
          color: #475569;
          margin-bottom: 4px;
        }}
        .detail-content .field-value {{
          color: #64748b;
        }}
        .search-box {{
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          font-size: 13px;
          margin-bottom: 16px;
        }}
        .search-box:focus {{
          outline: none;
          border-color: #3b82f6;
        }}
        .zoom-controls {{
          position: absolute;
          top: 16px;
          right: 16px;
          display: flex;
          gap: 8px;
          z-index: 10;
        }}
        .zoom-btn {{
          width: 36px;
          height: 36px;
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          font-size: 18px;
          color: #475569;
          transition: all 0.2s;
        }}
        .zoom-btn:hover {{
          background: #f1f5f9;
          border-color: #cbd5e1;
        }}
      </style>
    </head>
    <body>
      <div id="container">
        <div id="sidebar">
          <div class="section">
            <div class="section-title">Patient Overview</div>
            <div class="stat-card">
              <div class="stat-label">Variants</div>
              <div class="stat-value" id="stat-variants">-</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Conditions</div>
              <div class="stat-value" id="stat-conditions">-</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Medications</div>
              <div class="stat-value" id="stat-medications">-</div>
            </div>
          </div>
          
          <div class="section">
            <div class="section-title">Search</div>
            <input type="text" class="search-box" id="search-box" placeholder="Search nodes...">
          </div>

          <div class="section">
            <div class="section-title">Legend</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#3b82f6"></span> Patient</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#10b981"></span> Gene</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#f59e0b"></span> Variant</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#ef4444"></span> Drug</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#8b5cf6"></span> Condition</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#06b6d4"></span> Ethnicity</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#78716c"></span> Adjustment</div>
            <div class="legend-item"><span class="legend-swatch dashed"></span> Relationship</div>
          </div>

          <div class="section">
            <div class="section-title">Filters</div>
            <label class="control-item">
              <input type="checkbox" id="toggle-affects" checked>
              <span>Variant → Drug</span>
            </label>
            <label class="control-item">
              <input type="checkbox" id="toggle-adjustments" checked>
              <span>Adjustments</span>
            </label>
          </div>
        </div>

        <div id="chart-wrapper">
          <div class="zoom-controls">
            <div class="zoom-btn" id="zoom-in">+</div>
            <div class="zoom-btn" id="zoom-out">−</div>
            <div class="zoom-btn" id="zoom-reset">⟲</div>
          </div>
          <div id="chart"></div>
        </div>

        <div id="detail-panel">
          <div class="detail-content" id="detail-content">
            <h3>Details</h3>
            <p class="meta">Click on any node to see detailed information</p>
          </div>
        </div>
      </div>

      <div id="tooltip"></div>

      <script src="https://d3js.org/d3.v7.min.js"></script>
      <script>
        const width = window.innerWidth - 620;
        const height = window.innerHeight;
        const cx = width * 0.5;
        const cy = height * 0.5;
        const radius = Math.min(width, height) / 2 - 80;

        const tree = d3.tree()
            .size([2 * Math.PI, radius])
            .separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);

        const data = {d3_json};
        const extraLinks = {extra_links_json};
        const metadata = {metadata_json};

        // Update stats
        document.getElementById('stat-variants').textContent = metadata.total_variants || 0;
        document.getElementById('stat-conditions').textContent = metadata.total_conditions || 0;
        document.getElementById('stat-medications').textContent = metadata.total_medications || 0;

        const svg = d3.select("#chart").append("svg")
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [-cx, -cy, width, height]);

        const g = svg.append("g");

        const root = d3.hierarchy(data);
        root.descendants().forEach((d, i) => {{
          d._expanded = d.depth === 0;  // Only root expanded by default
        }});

        const linkLayerTree = g.append("g").attr("class", "tree-links");
        const nodeLayer = g.append("g").attr("class", "tree-nodes");
        const linkLayerExtra = g.append("g").attr("class", "extra-links");

        function update(source) {{
          // Collapse logic
          function collapse(d) {{
            if (d._expanded) {{
              d.children = d._children || d.data.children;
            }} else {{
              if (d.children) {{
                d._children = d.children;
                d.children = null;
              }}
            }}
            if (d.children) {{
              d.children.forEach(collapse);
            }}
          }}
          
          root.children = root._children || root.data.children;
          collapse(root);
          
          const layoutRoot = tree(root);

          // Links
          const links = linkLayerTree.selectAll("path")
            .data(layoutRoot.links(), d => d.target.data.uri);
          
          links.join(
            enter => enter.append("path")
              .attr("d", d3.linkRadial().angle(d => d.x).radius(d => d.y))
              .attr("fill", "none")
              .attr("stroke", "#e2e8f0")
              .attr("stroke-width", 1.5),
            update => update.attr("d", d3.linkRadial().angle(d => d.x).radius(d => d.y)),
            exit => exit.remove()
          );

          // Nodes
          const nodes = nodeLayer.selectAll("g")
            .data(layoutRoot.descendants(), d => d.data.uri);
          
          const nodesEnter = nodes.enter().append("g")
            .attr("transform", d => `rotate(${{d.x * 180 / Math.PI - 90}}) translate(${{d.y}},0)`)
            .on("click", (event, d) => {{
              d._expanded = !d._expanded;
              update(d);
              showDetails(d);
            }})
            .on("mouseenter", (event, d) => {{
              const tip = document.getElementById('tooltip');
              tip.innerHTML = `<strong>${{d.data.name}}</strong>`;
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
              document.getElementById('tooltip').style.opacity = 0;
            }});

          nodesEnter.append("circle")
            .attr("r", d => d.depth === 0 ? 8 : 5)
            .attr("fill", d => d.data.color || "#3b82f6");

          nodesEnter.append("text")
            .attr("dy", "0.31em")
            .attr("x", d => d.x < Math.PI === !d.children ? 6 : -6)
            .attr("text-anchor", d => d.x < Math.PI === !d.children ? "start" : "end")
            .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
            .text(d => d.data.name)
            .clone(true).lower()
            .attr("stroke", "white")
            .attr("stroke-width", 3);

          nodes.merge(nodesEnter)
            .attr("transform", d => `rotate(${{d.x * 180 / Math.PI - 90}}) translate(${{d.y}},0)`);

          nodes.exit().remove();

          // Extra links
          drawExtraLinks(layoutRoot);
        }}

        function drawExtraLinks(layoutRoot) {{
          linkLayerExtra.selectAll("path").remove();
          
          const showAffects = document.getElementById('toggle-affects')?.checked ?? true;
          const showAdjustments = document.getElementById('toggle-adjustments')?.checked ?? true;
          
          const uriToNode = new Map();
          layoutRoot.descendants().forEach(d => {{
            if (d.data && d.data.uri) uriToNode.set(d.data.uri, d);
          }});
          
          const filtered = extraLinks.filter(l => {{
            if (!uriToNode.has(l.source) || !uriToNode.has(l.target)) return false;
            if (l.label === 'affects' && !showAffects) return false;
            if (l.label === 'adjustment' && !showAdjustments) return false;
            return true;
          }});
          
          linkLayerExtra.selectAll("path")
            .data(filtered)
            .join("path")
              .attr("stroke", d => d.color || "#94a3b8")
              .attr("stroke-dasharray", "6,3")
              .attr("fill", "none")
              .attr("d", d => {{
                const s = uriToNode.get(d.source);
                const t = uriToNode.get(d.target);
                const sx = Math.cos(s.x - Math.PI/2) * s.y;
                const sy = Math.sin(s.x - Math.PI/2) * s.y;
                const tx = Math.cos(t.x - Math.PI/2) * t.y;
                const ty = Math.sin(t.x - Math.PI/2) * t.y;
                return `M ${{sx}},${{sy}} L ${{tx}},${{ty}}`;
              }});
        }}

        function showDetails(d) {{
          const panel = document.getElementById('detail-content');
          const details = d.data.details || {{}};
          
          let html = `<h3>${{d.data.name}}</h3>`;
          html += `<p class="meta">${{details.type || 'Node'}}</p>`;
          
          if (details.type === 'Variant' && details.data) {{
            const v = details.data;
            html += `<div class="field"><div class="field-label">Gene</div><div class="field-value">${{v.gene || 'N/A'}}</div></div>`;
            html += `<div class="field"><div class="field-label">Clinical Significance</div><div class="field-value">${{v.clinical_significance || 'N/A'}}</div></div>`;
            if (v.population_frequency_source) {{
              html += `<div class="field"><div class="field-label">Pop. Freq. Source</div><div class="field-value">${{v.population_frequency_source}}</div></div>`;
            }}
          }}
          
          if (details.type === 'Drug' && details.recommendation) {{
            html += `<div class="field"><div class="field-label">Recommendation</div><div class="field-value">${{details.recommendation.substring(0, 200)}}...</div></div>`;
            html += `<div class="field"><div class="field-label">Evidence Level</div><div class="field-value">${{details.evidence_level || 'N/A'}}</div></div>`;
          }}
          
          if (details.type === 'Condition' && details.code) {{
            html += `<div class="field"><div class="field-label">SNOMED Code</div><div class="field-value">${{details.code}}</div></div>`;
          }}
          
          panel.innerHTML = html;
        }}

        // Zoom controls
        const zoom = d3.zoom()
          .scaleExtent([0.3, 3])
          .on("zoom", (event) => {{
            g.attr("transform", event.transform);
          }});
        
        svg.call(zoom);
        
        document.getElementById('zoom-in').onclick = () => {{
          svg.transition().call(zoom.scaleBy, 1.3);
        }};
        document.getElementById('zoom-out').onclick = () => {{
          svg.transition().call(zoom.scaleBy, 0.7);
        }};
        document.getElementById('zoom-reset').onclick = () => {{
          svg.transition().call(zoom.transform, d3.zoomIdentity);
        }};

        // Search functionality
        document.getElementById('search-box').addEventListener('input', (e) => {{
          const searchTerm = e.target.value.toLowerCase();
          nodeLayer.selectAll('g').each(function(d) {{
            const matches = d.data.name.toLowerCase().includes(searchTerm);
            d3.select(this).style('opacity', searchTerm === '' || matches ? 1 : 0.2);
          }});
        }});

        // Toggle controls
        document.getElementById('toggle-affects').addEventListener('change', () => {{
          const layoutRoot = tree(root);
          drawExtraLinks(layoutRoot);
        }});
        document.getElementById('toggle-adjustments').addEventListener('change', () => {{
          const layoutRoot = tree(root);
          drawExtraLinks(layoutRoot);
        }});

        update(root);
      </script>
    </body>
    </html>
    """
    components.html(html_template, height=900, scrolling=False)