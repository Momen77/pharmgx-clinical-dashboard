"""
Interactive D3.js Radial Visualization for JSON-LD Pharmacogenetic Data
Creates a color-coded, zoomable, clickable radial tree visualization
"""
import streamlit as st
import json
from rdflib import Graph
from collections import defaultdict


def jsonld_to_hierarchy(jsonld_data):
    """Convert JSON-LD to a clinically-relevant hierarchy for D3.js (direct field extraction)."""
    try:
        # Direct extraction from structured JSON-LD fields (not RDF triples)
        name = jsonld_data.get('name') or jsonld_data.get('identifier') or 'Patient'
        root = {"name": name, "children": []}

        # Demographics
        demo_children = []
        clin_info = jsonld_data.get('clinical_information', {})
        demo = clin_info.get('demographics', {}) if isinstance(clin_info, dict) else {}
        if jsonld_data.get('identifier'):
            demo_children.append({"name": f"ID: {jsonld_data.get('identifier')}"})
        if jsonld_data.get('dateCreated'):
            demo_children.append({"name": f"Created: {jsonld_data.get('dateCreated')}"})
        if demo.get('age'):
            demo_children.append({"name": f"Age: {demo.get('age')}"})
        if demo_children:
            root["children"].append({"name": "Demographics", "children": demo_children})

        # Genes -> Variants -> Drugs
        pgx_profile = jsonld_data.get('pharmacogenomics_profile', {})
        if isinstance(pgx_profile, dict):
            genes = pgx_profile.get('genes_analyzed', [])
            variants = jsonld_data.get('variants', [])
            gene_children = []
            for gene_symbol in genes[:15]:  # Cap to 15 genes
                vlist = [v for v in variants if v.get('gene') == gene_symbol][:5]  # Top 5 variants per gene
                v_children = []
                for var in vlist:
                    rsid = var.get('rsid') or var.get('variant_id', '')
                    if not rsid.startswith('rs') and var.get('variant_id'):
                        rsid = var.get('variant_id')
                    label = rsid if rsid else f"Variant {len(v_children) + 1}"
                    if var.get('clinical_significance'):
                        label = f"{label} ({var.get('clinical_significance')})"
                    drug_children = []
                    for d in var.get('drugs', [])[:5]:
                        dn = d.get('name', 'Unknown Drug')
                        drug_node = {"name": dn}
                        # Add recommendation as child node if present
                        if d.get('recommendation'):
                            rec_text = d.get('recommendation', '')[:80]
                            if len(d.get('recommendation', '')) > 80:
                                rec_text += "..."
                            drug_node["children"] = [{"name": rec_text}]
                        drug_children.append(drug_node)
                    if drug_children:
                        variant_node = {"name": label, "children": drug_children}
                    else:
                        variant_node = {"name": label}
                    v_children.append(variant_node)
                gene_children.append({"name": gene_symbol, "children": v_children or [{"name": "No variants"}]})
            if gene_children:
                root["children"].append({"name": "Genes", "children": gene_children})

        # Clinical: Conditions & Medications
        if isinstance(clin_info, dict):
            conds = clin_info.get('current_conditions', [])
            meds = clin_info.get('current_medications', [])
            cond_children = []
            for c in conds[:5]:
                label = c.get('rdfs:label') or c.get('skos:prefLabel') or c.get('name') or 'Condition'
                if c.get('snomed:code'):
                    label = f"{label} ({c.get('snomed:code')})"
                cond_children.append({"name": label})
            if cond_children:
                root["children"].append({"name": "Conditions", "children": cond_children})
            med_children = []
            for m in meds[:5]:
                label = m.get('rdfs:label') or m.get('name') or 'Medication'
                med_children.append({"name": label})
            if med_children:
                root["children"].append({"name": "Medications", "children": med_children})

        return root
    except Exception as e:
        st.error(f"Error converting JSON-LD to hierarchy: {e}")
        return {"name": "root", "children": []}


def render_d3_visualization(hierarchy_data):
    """Render interactive D3.js radial tree visualization"""
    d3_data = json.dumps(hierarchy_data)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
      body {{
        background-color: #ffffff;
        color: #333;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 20px;
      }}
      .legend {{
        margin-bottom: 15px;
        font-size: 14px;
        color: #333;
      }}
      .legend-item {{
        display: inline-block;
        margin-right: 20px;
        color: #333;
      }}
      .legend-dot {{
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 5px;
        vertical-align: middle;
      }}
      .tooltip {{
        position: absolute;
        text-align: center;
        padding: 8px 12px;
        background: rgba(255,255,255,0.98);
        color: #333;
        border-radius: 6px;
        pointer-events: none;
        font-size: 13px;
        border: 1px solid rgba(0,0,0,0.2);
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
      }}
      .controls {{
        margin-bottom: 15px;
      }}
      .control-btn {{
        background-color: #1e3a8a;
        color: white;
        border: none;
        padding: 8px 16px;
        margin-right: 10px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 13px;
      }}
      .control-btn:hover {{
        background-color: #1e40af;
      }}
      svg {{
        border: 1px solid #ddd;
        border-radius: 8px;
        background-color: #ffffff;
      }}
      text {{
        fill: #333;
        font-size: 13px;
      }}
    </style>
    </head>
    <body>
      <div class="legend">
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#1f77b4;"></span>
          <span>Patient</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#1e90ff;"></span>
          <span>Gene</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#FF7F50;"></span>
          <span>Variant (rsID)</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#90EE90;"></span>
          <span>Drug</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#FF69B4;"></span>
          <span>Disease</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#17becf;"></span>
          <span>Demographics</span>
        </div>
      </div>
      
      <div class="controls">
        <button class="control-btn" onclick="resetZoom()">Reset Zoom</button>
        <button class="control-btn" onclick="expandAll()">Expand All</button>
        <button class="control-btn" onclick="collapseAll()">Collapse All</button>
      </div>
      
      <svg width="1600" height="900"></svg>
      <div class="tooltip" style="opacity:0"></div>
      
      <script>
        const data = {d3_data};
        const width = 1400, height = 900, radius = Math.min(width, height) / 1.0;

        const tree = d3.tree().size([2 * Math.PI, radius * 0.85]).separation((a, b) => (a.parent == b.parent ? 180 : 220));
        const root = d3.hierarchy(data);
        tree(root);

        const svg = d3.select("svg")
          .attr("viewBox", [-width / 2, -height / 2, width, height]);

        const g = svg.append("g");

        // Color mapping based on node name patterns
        function getColor(name) {{
          const n = name.toLowerCase().trim();
          // Patient (root) - dark blue
          if (n.includes("patient") || n.startsWith("jane") || n.startsWith("mrn-")) return "#1f77b4";
          // Genes container - bright blue
          if (n === "genes") return "#00BFFF";
          // Gene symbols - blue
          if (n.match(/^(slco1b1|g6pd|cyp\d+|tpmt|dpyd|ugt1a1|nudt15|cfp|cbc|dpy-?d|dihydroxy|udp-glucur|thiopurine|nucleoside|no variants)$/i)) return "#1e90ff";
          // Demographics container - cyan
          if (n === "demographics") return "#17becf";
          // Demographics items - light cyan
          if (n.startsWith("id:") || n.startsWith("created:") || n.startsWith("age:")) return "#7ec8e3";
          // Conditions container - pink
          if (n === "conditions") return "#FF69B4";
          // Condition items - light pink
          if (n.includes("condition") && !n.includes("conditions")) return "#ffb3db";
          // Medications container - green
          if (n === "medications") return "#32CD32";
          // Medication items - light green
          if (n.includes("medication") && !n.includes("medications")) return "#90EE90";
          // Variants (rs IDs) - orange
          if (n.match(/^rs\d+/) || (n.includes("variant") && !n.includes("variants"))) return "#FF7F50";
          // Drugs - light green
          if (n.includes("drug") || n.includes(" - ")) return "#90EE90";
          // Default - gray
          return "#888888";
        }}

        const tooltip = d3.select(".tooltip");

        // Links
        const link = g.append("g")
          .selectAll("path")
          .data(root.links())
          .join("path")
          .attr("fill", "none")
          .attr("stroke", "#888")
          .attr("stroke-opacity", 0.5)
          .attr("stroke-width", 2)
          .attr("d", d3.linkRadial()
            .angle(d => d.x)
            .radius(d => d.y));

        // Nodes
        const node = g.append("g")
          .selectAll("g")
          .data(root.descendants())
          .join("g")
          .attr("transform", d => `
            rotate(${{d.x * 180 / Math.PI - 90}})
            translate(${{d.y}},0)
          `);

        node.append("circle")
          .attr("fill", d => getColor(d.data.name))
          .attr("r", d => d.children ? 12 : 10)
          .attr("stroke", "#333")
          .attr("stroke-width", 2)
          .style("cursor", "pointer")
          .on("mouseover", function(event, d) {{
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", d.children ? 16 : 14);
            
            tooltip.transition().duration(200).style("opacity", .95);
            tooltip.html(`
              <strong>${{d.data.name}}</strong><br/>
              Depth: ${{d.depth}}<br/>
              ${{d.children ? `Children: ${{d.children.length}}` : 'Leaf node'}}
            `)
              .style("left", (event.pageX + 10) + "px")
              .style("top", (event.pageY - 20) + "px");
          }})
          .on("mouseout", function(event, d) {{
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", d.children ? 12 : 10);
            
            tooltip.transition().duration(500).style("opacity", 0);
          }})
          .on("click", function(event, d) {{
            event.stopPropagation();
            // Send node info to parent Streamlit app
            const nodeInfo = {{
              name: d.data.name,
              depth: d.depth,
              hasChildren: !!d.children,
              childCount: d.children ? d.children.length : 0
            }};
            window.parent.postMessage({{ 
              type: 'streamlit:setComponentValue',
              value: nodeInfo
            }}, '*');
          }});

        // Labels
        node.append("text")
          .attr("dy", "0.31em")
          .attr("x", d => d.x < Math.PI === !d.children ? 15 : -15)
          .attr("text-anchor", d => d.x < Math.PI === !d.children ? "start" : "end")
          .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
          .text(d => d.data.name)
          .style("font-size", "13px")
          .style("font-weight", "500")
          .clone(true).lower()
          .attr("stroke", "#ffffff")
          .attr("stroke-width", 3);

        // Zoom and pan
        const zoom = d3.zoom()
          .scaleExtent([0.3, 8])
          .on("zoom", (event) => {{
            g.attr("transform", event.transform);
          }});
        
        svg.call(zoom);

        // Control functions
        window.resetZoom = function() {{
          svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
        }};

        window.expandAll = function() {{
          root.each(d => {{
            if (d._children) {{
              d.children = d._children;
              d._children = null;
            }}
          }});
          update(root);
        }};

        window.collapseAll = function() {{
          root.each(d => {{
            if (d.children && d.depth > 0) {{
              d._children = d.children;
              d.children = null;
            }}
          }});
          update(root);
        }};

        function update(source) {{
          tree(root);
          
          link.data(root.links())
            .attr("d", d3.linkRadial()
              .angle(d => d.x)
              .radius(d => d.y));
          
          node.data(root.descendants())
            .attr("transform", d => `
              rotate(${{d.x * 180 / Math.PI - 90}})
              translate(${{d.y}},0)
            `);
        }}
      </script>
    </body>
    </html>
    """

    st.components.v1.html(html, height=950, scrolling=True)


def get_node_details(jsonld_data, node_name):
    """Get detailed information about a specific node from JSON-LD"""
    try:
        g = Graph().parse(data=json.dumps(jsonld_data), format="json-ld")
        details = defaultdict(list)
        
        for s, p, o in g:
            if node_name in str(s) or node_name in str(o):
                predicate = str(p).split("/")[-1].split("#")[-1]
                obj_value = str(o).split("/")[-1].split("#")[-1]
                details[predicate].append(obj_value)
        
        return dict(details) if details else None
    except Exception as e:
        st.error(f"Error getting node details: {e}")
        return None

