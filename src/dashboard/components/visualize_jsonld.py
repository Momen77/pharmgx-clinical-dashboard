"""
Interactive D3.js Radial Visualization for JSON-LD Pharmacogenetic Data
Creates a color-coded, zoomable, clickable radial tree visualization
"""
import streamlit as st
import json
from rdflib import Graph
from collections import defaultdict


def jsonld_to_hierarchy(jsonld_data):
    """Convert JSON-LD to a clinically-relevant hierarchy for D3.js (whitelisted)."""
    try:
        g = Graph().parse(data=json.dumps(jsonld_data), format="json-ld")
        allowed_node_patterns = (
            "identifiers.org/dbsnp/rs",
            "identifiers.org/ncbigene/",
            "snomed.info/id/",
            "pharmgkb",
            "drugbank",
            "ugent.be/person/",
        )
        allowed_pred_keywords = (
            "hasvariant", "has_gene", "hasgene", "affectsgene",
            "drug", "phenotype", "disease"
        )

        # Build filtered adjacency
        links = defaultdict(list)
        nodes_seen = set()
        for subj, pred, obj in g:
            s, p, o = str(subj), str(pred).lower(), str(obj)
            if not any(k in s for k in allowed_node_patterns):
                continue
            if not any(k in o for k in allowed_node_patterns):
                continue
            if not any(k in p for k in allowed_pred_keywords):
                continue
            links[s].append(o)
            nodes_seen.add(s); nodes_seen.add(o)

        # Choose patient as root if present
        roots = [n for n in nodes_seen if "ugent.be/person/" in n]
        root = roots[0] if roots else (list(links.keys())[0] if links else "root")

        visited = set()

        def label_of(iri: str) -> str:
            if "identifiers.org/dbsnp/rs" in iri:
                return iri.split("/")[-1]  # rsID
            if "identifiers.org/ncbigene/" in iri:
                return "Gene:" + iri.split("/")[-1]
            if "snomed.info/id/" in iri:
                return "SNOMED:" + iri.split("/")[-1]
            if "ugent.be/person/" in iri:
                return "Patient"
            if "pharmgkb" in iri or "drugbank" in iri:
                return "Drug"
            return iri.split("/")[-1]

        def make_tree(node, depth=0, max_depth=4):
            if node in visited or depth > max_depth:
                return {"name": label_of(node)}
            visited.add(node)
            children = [make_tree(c, depth+1, max_depth) for c in links.get(node, [])]
            result = {"name": label_of(node)}
            if children:
                result["children"] = children
            return result

        return make_tree(root)
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
        background-color: #0f1116;
        color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 20px;
      }}
      .legend {{
        margin-bottom: 15px;
        font-size: 14px;
      }}
      .legend-item {{
        display: inline-block;
        margin-right: 20px;
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
        background: rgba(0,0,0,0.9);
        color: #fff;
        border-radius: 6px;
        pointer-events: none;
        font-size: 13px;
        border: 1px solid rgba(255,255,255,0.2);
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
        border: 1px solid #333;
        border-radius: 8px;
        background-color: #1a1a2e;
      }}
      text {{
        fill: #e0e0e0;
        font-size: 11px;
      }}
    </style>
    </head>
    <body>
      <div class="legend">
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#00BFFF;"></span>
          <span>Gene</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#FF7F50;"></span>
          <span>Variant</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#32CD32;"></span>
          <span>Drug</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#FFD700;"></span>
          <span>Phenotype</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#FF69B4;"></span>
          <span>Disease</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background-color:#9370DB;"></span>
          <span>Evidence</span>
        </div>
      </div>
      
      <div class="controls">
        <button class="control-btn" onclick="resetZoom()">Reset Zoom</button>
        <button class="control-btn" onclick="expandAll()">Expand All</button>
        <button class="control-btn" onclick="collapseAll()">Collapse All</button>
      </div>
      
      <svg width="950" height="950"></svg>
      <div class="tooltip" style="opacity:0"></div>
      
      <script>
        const data = {d3_data};
        const width = 950, radius = width / 2;

        const tree = d3.tree().size([2 * Math.PI, radius - 100]);
        const root = d3.hierarchy(data);
        tree(root);

        const svg = d3.select("svg")
          .attr("viewBox", [-width / 2, -width / 2, width, width]);

        const g = svg.append("g");

        // Color mapping based on node name
        function getColor(name) {{
          const n = name.toLowerCase();
          if (n.includes("gene") || n.includes("cyp") || n.includes("tpmt") || n.includes("dpyd")) return "#00BFFF";
          if (n.includes("variant") || n.includes("rs") || n.includes("*")) return "#FF7F50";
          if (n.includes("drug") || n.includes("medication") || n.includes("warfarin")) return "#32CD32";
          if (n.includes("phenotype") || n.includes("metabolizer")) return "#FFD700";
          if (n.includes("disease") || n.includes("condition")) return "#FF69B4";
          if (n.includes("evidence") || n.includes("literature") || n.includes("pmid")) return "#9370DB";
          return "#aaaaaa";
        }}

        const tooltip = d3.select(".tooltip");

        // Links
        const link = g.append("g")
          .selectAll("path")
          .data(root.links())
          .join("path")
          .attr("fill", "none")
          .attr("stroke", "#555")
          .attr("stroke-opacity", 0.4)
          .attr("stroke-width", 1.5)
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
          .attr("r", d => d.children ? 6 : 4)
          .attr("stroke", "#fff")
          .attr("stroke-width", 1)
          .style("cursor", "pointer")
          .on("mouseover", function(event, d) {{
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", d.children ? 9 : 7);
            
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
              .attr("r", d.children ? 6 : 4);
            
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
          .attr("x", d => d.x < Math.PI === !d.children ? 6 : -6)
          .attr("text-anchor", d => d.x < Math.PI === !d.children ? "start" : "end")
          .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
          .text(d => d.data.name)
          .style("font-size", "10px")
          .clone(true).lower()
          .attr("stroke", "#1a1a2e")
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

    st.components.v1.html(html, height=1000, scrolling=True)


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

