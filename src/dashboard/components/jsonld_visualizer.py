import streamlit as st
import streamlit.components.v1 as components
import json
from collections import defaultdict

def get_best_label(node_obj, default_text="Unnamed"):
    """
    Finds the best human-readable label from a JSON object.
    It checks for common labeling properties in a specific order.
    """
    if not isinstance(node_obj, dict):
        return str(node_obj)

    # Prioritized list of keys to check for a label
    label_keys = [
        "skos:prefLabel",
        "rdfs:label",
        "schema:name",
        "name",
        "identifier"
    ]
    for key in label_keys:
        if node_obj.get(key):
            return node_obj[key]
    
    # Fallback if no prioritized key is found
    return default_text

def jsonld_to_radial_graph_data(jsonld_data: dict):
    """
    Transforms the nested JSON-LD into a radial/hierarchical structure
    with the patient at the center and meaningful, human-readable labels.

    Returns nodes organized in layers:
    - Layer 0: Patient (center)
    - Layer 1: Demographics (age, gender, birthplace, ethnicity)
    - Layer 2: Clinical Info (conditions, medications, lifestyle)
    - Layer 3: Genetics (genes, variants)
    - Layer 4: Drug Interactions
    """
    nodes = []
    links = []
    seen_nodes = set()
    node_counter = 0

    # Helper to generate unique IDs
    def get_unique_id(prefix):
        nonlocal node_counter
        node_counter += 1
        return f"{prefix}_{node_counter}"

    # Helper to add a node if it hasn't been seen
    def add_node(node_id, label, node_type, layer, data_obj=None):
        if node_id not in seen_nodes:
            seen_nodes.add(node_id)
            node_color_map = {
                "Patient": "#1f77b4",
                "Demographics": "#17becf",
                "Gene": "#2ca02c",
                "Variant": "#ff7f0e",
                "Drug": "#d62728",
                "Condition": "#9467bd",
                "Lifestyle": "#8c564b",
                "Medication": "#e377c2"
            }
            nodes.append({
                "id": node_id,
                "label": label,
                "type": node_type,
                "layer": layer,
                "color": node_color_map.get(node_type, "#7f7f7f"),
                "data": data_obj or {}
            })
            return node_id
        return node_id

    # 1. Create central Patient node
    patient_id = "patient_central"
    patient_name = jsonld_data.get('name', jsonld_data.get('identifier', 'Patient'))
    add_node(patient_id, patient_name, "Patient", 0, jsonld_data)

    # 2. Add Demographics layer (Layer 1)
    demographics_added = False

    # Age
    if date_created := jsonld_data.get('dateCreated'):
        age_id = get_unique_id("age")
        add_node(age_id, f"Created: {date_created}", "Demographics", 1)
        links.append({"source": patient_id, "target": age_id, "label": "date"})
        demographics_added = True

    # Identifier/MRN
    if identifier := jsonld_data.get('identifier'):
        id_node = get_unique_id("identifier")
        add_node(id_node, f"ID: {identifier}", "Demographics", 1)
        links.append({"source": patient_id, "target": id_node, "label": "identifier"})
        demographics_added = True

    # Description
    if description := jsonld_data.get('description'):
        desc_id = get_unique_id("description")
        # Truncate long descriptions
        desc_label = description[:50] + "..." if len(description) > 50 else description
        add_node(desc_id, desc_label, "Demographics", 1)
        links.append({"source": patient_id, "target": desc_id, "label": "description"})
        demographics_added = True

    # 3. Process Clinical Information (Layer 2)
    if clinical_info := jsonld_data.get('clinical_information'):
        # Conditions
        for i, condition in enumerate(clinical_info.get('current_conditions', [])[:5], 1):
            cond_id = get_unique_id(f"condition")
            cond_label = get_best_label(condition, f"Condition {i}")
            # Extract SNOMED code if available
            if snomed_code := condition.get('snomed:code'):
                cond_label = f"{cond_label} ({snomed_code})"
            add_node(cond_id, cond_label, "Condition", 2, condition)
            links.append({"source": patient_id, "target": cond_id, "label": "has_condition"})

        # Medications
        for i, med in enumerate(clinical_info.get('current_medications', [])[:5], 1):
            med_id = get_unique_id(f"medication")
            med_label = get_best_label(med, f"Medication {i}")
            add_node(med_id, med_label, "Medication", 2, med)
            links.append({"source": patient_id, "target": med_id, "label": "takes"})

            # Link medication to the condition it treats
            if treats := med.get('treats_condition', {}):
                # Find matching condition node
                treats_label = treats.get('rdfs:label', treats.get('name', ''))
                if treats_label:
                    # Create a link if we can find the matching condition
                    for node in nodes:
                        if node["type"] == "Condition" and treats_label.lower() in node["label"].lower():
                            links.append({"source": med_id, "target": node["id"], "label": "treats"})
                            break

        # Lifestyle Factors
        for i, factor in enumerate(clinical_info.get('lifestyle_factors', [])[:5], 1):
            factor_id = get_unique_id(f"lifestyle")
            factor_label = get_best_label(factor, f"Lifestyle {i}")
            # Add more detail from factor
            factor_type = factor.get('factor_type', '')
            status = factor.get('status', '')
            if factor_type and status:
                factor_label = f"{factor_type.title()}: {status}"
            add_node(factor_id, factor_label, "Lifestyle", 2, factor)
            links.append({"source": patient_id, "target": factor_id, "label": "lifestyle"})

    # 4. Process Variants and Genes (Layers 3 & 4)
    gene_map = {}  # To store gene nodes
    variant_count = {}  # Count variants per gene

    for variant in jsonld_data.get('variants', []):
        variant_id = variant.get('rsid') or variant.get('variant_id')
        if not variant_id:
            continue

        gene_symbol = variant.get('gene')
        if not gene_symbol:
            continue

        # Create or get Gene node (Layer 3)
        if gene_symbol not in gene_map:
            gene_id = get_unique_id(f"gene")
            variant_count[gene_symbol] = 0
            add_node(gene_id, gene_symbol, "Gene", 3)
            links.append({"source": patient_id, "target": gene_id, "label": "has_gene"})
            gene_map[gene_symbol] = gene_id

        # Limit variants per gene to avoid clutter
        if variant_count[gene_symbol] >= 3:
            continue
        variant_count[gene_symbol] += 1

        # Create Variant node (Layer 4)
        variant_node_id = get_unique_id(f"variant")
        # Create readable label
        protein_change = variant.get('protein_change', '')
        clinical_sig = variant.get('clinical_significance', '')
        variant_label = variant_id
        if protein_change:
            variant_label = f"{variant_id} ({protein_change})"
        if clinical_sig:
            variant_label = f"{variant_label}\n{clinical_sig}"

        add_node(variant_node_id, variant_label, "Variant", 4, variant)
        links.append({"source": gene_map[gene_symbol], "target": variant_node_id, "label": "variant"})

        # Link Variant to affected Drugs (Layer 4)
        for drug in variant.get('drugs', [])[:2]:  # Limit to 2 drugs per variant
            drug_name = drug.get('name')
            if drug_name:
                drug_id = get_unique_id(f"drug")
                add_node(drug_id, drug_name, "Drug", 4, drug)
                links.append({"source": variant_node_id, "target": drug_id, "label": "affects"})

    return {"nodes": nodes, "links": links}


def render_radial_graph(graph_data: dict):
    """Renders a radial/hierarchical D3.js graph with patient at center in Streamlit."""

    graph_json = json.dumps(graph_data)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
            #container {{ display: flex; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }}
            #chart {{ flex-grow: 1; height: 900px; position: relative; }}
            #legend {{
                width: 220px;
                padding: 15px;
                background-color: rgba(255,255,255,0.95);
                border-left: 1px solid #ddd;
                box-shadow: -2px 0 10px rgba(0,0,0,0.1);
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                margin-bottom: 8px;
                font-size: 13px;
                padding: 4px;
                border-radius: 4px;
            }}
            .legend-item:hover {{ background-color: #f0f0f0; }}
            .legend-swatch {{ width: 14px; height: 14px; border-radius: 50%; margin-right: 10px; border: 2px solid #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }}
            .link {{
                stroke: #999;
                stroke-opacity: 0.4;
                fill: none;
                stroke-width: 1.5px;
            }}
            .link:hover {{ stroke-opacity: 0.8; stroke-width: 2.5px; }}
            .node circle {{
                stroke: #fff;
                stroke-width: 2px;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            .node:hover circle {{
                stroke-width: 4px;
                stroke: #333;
                filter: drop-shadow(0 0 8px rgba(0,0,0,0.4));
            }}
            .node text {{
                pointer-events: none;
                font-size: 11px;
                fill: #222;
                font-weight: 500;
                text-shadow: 1px 1px 2px rgba(255,255,255,0.8), -1px -1px 2px rgba(255,255,255,0.8);
            }}
            .node.patient circle {{ stroke-width: 3px; }}
            .node.patient text {{ font-size: 14px; font-weight: 700; }}
            #tooltip {{
                position: absolute;
                text-align: left;
                padding: 12px;
                font: 12px sans-serif;
                background: rgba(0,0,0,0.85);
                color: white;
                border: 0px;
                border-radius: 8px;
                pointer-events: none;
                opacity: 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                max-width: 250px;
            }}
            #legend h3 {{
                margin-top: 0;
                margin-bottom: 15px;
                font-size: 16px;
                color: #333;
                border-bottom: 2px solid #1f77b4;
                padding-bottom: 8px;
            }}
            .layer-label {{
                font-size: 10px;
                fill: #666;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="chart"></div>
            <div id="legend">
                <h3>Legend</h3>
                <div class="legend-item"><span class="legend-swatch" style="background:#1f77b4"></span> Patient</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#17becf"></span> Demographics</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#9467bd"></span> Condition</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#e377c2"></span> Medication</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#8c564b"></span> Lifestyle</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#2ca02c"></span> Gene</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#ff7f0e"></span> Variant</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#d62728"></span> Drug</div>
                <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
                <div style="font-size: 11px; color: #666; line-height: 1.6;">
                    <strong>Layout:</strong><br>
                    • Center: Patient<br>
                    • Ring 1: Demographics<br>
                    • Ring 2: Clinical Info<br>
                    • Ring 3-4: Genetics<br>
                    <br>
                    <strong>Interactions:</strong><br>
                    • Hover for details<br>
                    • Scroll to zoom<br>
                    • Drag to pan
                </div>
            </div>
        </div>
        <div id="tooltip"></div>

        <script src="https://d3js.org/d3.v7.min.js"></script>
        <script>
            const graphData = {graph_json};
            const width = document.getElementById('chart').clientWidth;
            const height = 900;
            const centerX = width / 2;
            const centerY = height / 2;

            // Radial layout configuration - distance from center for each layer
            const layerRadii = {{
                0: 0,      // Patient at center
                1: 120,    // Demographics
                2: 240,    // Clinical info
                3: 360,    // Genes
                4: 480     // Variants/Drugs
            }};

            const svg = d3.select("#chart").append("svg")
                .attr("width", width)
                .attr("height", height)
                .call(d3.zoom()
                    .scaleExtent([0.3, 3])
                    .on("zoom", (event) => {{
                        mainGroup.attr("transform", event.transform);
                    }}))
                .append("g");

            const mainGroup = svg.append("g")
                .attr("transform", `translate(${{centerX}}, ${{centerY}})`);

            const tooltip = d3.select("#tooltip");

            // Calculate positions for nodes based on layer
            const nodesByLayer = d3.group(graphData.nodes, d => d.layer);

            graphData.nodes.forEach(node => {{
                const layer = node.layer;
                const radius = layerRadii[layer] || 100;

                // Get all nodes in this layer
                const nodesInLayer = nodesByLayer.get(layer);
                const nodeIndex = nodesInLayer.indexOf(node);
                const totalNodesInLayer = nodesInLayer.length;

                // Calculate angle for this node (distribute evenly around circle)
                const angle = (2 * Math.PI * nodeIndex / totalNodesInLayer) - Math.PI / 2;

                // Set fixed position
                node.fx = radius * Math.cos(angle);
                node.fy = radius * Math.sin(angle);
            }});

            // Draw layer circles (guides)
            [1, 2, 3, 4].forEach(layer => {{
                mainGroup.append("circle")
                    .attr("cx", 0)
                    .attr("cy", 0)
                    .attr("r", layerRadii[layer])
                    .attr("fill", "none")
                    .attr("stroke", "#ddd")
                    .attr("stroke-width", 1)
                    .attr("stroke-dasharray", "5,5")
                    .attr("opacity", 0.3);
            }});

            // Draw links
            const link = mainGroup.append("g")
                .attr("class", "links")
                .selectAll("path")
                .data(graphData.links)
                .enter().append("path")
                .attr("class", "link")
                .attr("d", d => {{
                    const sourceNode = graphData.nodes.find(n => n.id === d.source);
                    const targetNode = graphData.nodes.find(n => n.id === d.target);
                    return `M${{sourceNode.fx}},${{sourceNode.fy}} L${{targetNode.fx}},${{targetNode.fy}}`;
                }})
                .attr("stroke", d => {{
                    // Color links based on relationship type
                    if (d.label === "treats") return "#e377c2";
                    if (d.label === "affects") return "#d62728";
                    return "#999";
                }});

            // Draw nodes
            const node = mainGroup.append("g")
                .attr("class", "nodes")
                .selectAll("g")
                .data(graphData.nodes)
                .enter().append("g")
                .attr("class", d => d.type === "Patient" ? "node patient" : "node")
                .attr("transform", d => `translate(${{d.fx}}, ${{d.fy}})`);

            node.append("circle")
                .attr("r", d => {{
                    if (d.type === 'Patient') return 20;
                    if (d.layer === 1) return 10;
                    if (d.layer === 2) return 12;
                    return 8;
                }})
                .attr("fill", d => d.color);

            node.append("text")
                .text(d => d.label)
                .attr("x", d => d.type === 'Patient' ? 0 : 15)
                .attr("y", d => d.type === 'Patient' ? -25 : 4)
                .attr("text-anchor", d => d.type === 'Patient' ? "middle" : "start")
                .style("font-size", d => d.type === 'Patient' ? "14px" : "11px");

            // Enhanced tooltips
            node.on("mouseover", (event, d) => {{
                tooltip.transition().duration(200).style("opacity", .95);
                let html = `<strong style="color: ${{d.color}}; font-size: 14px;">${{d.type}}</strong><br/>`;
                html += `<strong>Label:</strong> ${{d.label}}<br/>`;
                html += `<strong>Layer:</strong> ${{d.layer}}`;

                // Add extra info if available
                if (d.data && Object.keys(d.data).length > 0) {{
                    if (d.data.identifier) html += `<br/><strong>ID:</strong> ${{d.data.identifier}}`;
                    if (d.data['snomed:code']) html += `<br/><strong>SNOMED:</strong> ${{d.data['snomed:code']}}`;
                    if (d.data.clinical_significance) html += `<br/><strong>Significance:</strong> ${{d.data.clinical_significance}}`;
                }}

                tooltip.html(html)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", () => {{
                tooltip.transition().duration(500).style("opacity", 0);
            }});

        </script>
    </body>
    </html>
    """
    components.html(html_template, height=920)

# --- Streamlit App Main Logic ---
st.set_page_config(layout="wide", page_title="PGx Network Visualizer")

st.title("Interactive Pharmacogenomics (PGx) Patient Profile")
st.write(
    "This tool visualizes a patient's PGx profile from a JSON-LD file as an interactive **radial graph** "
    "with the patient at the center. The visualization is organized in concentric rings radiating from the patient, "
    "making it easy to understand demographic information, clinical data, and genetic relationships at a glance."
)

st.info(
    "**Radial Layout:** Patient (center) → Demographics (ring 1) → Clinical Info (ring 2) → "
    "Genes (ring 3) → Variants & Drug Interactions (ring 4). "
    "Scroll to zoom, drag to pan, and hover over nodes for detailed information."
)

uploaded_file = st.file_uploader("Upload your comprehensive JSON-LD file", type=["json", "jsonld"])

if uploaded_file is not None:
    try:
        # Load the original data
        json_data = json.load(uploaded_file)

        # Transform data for the radial graph
        graph_data = jsonld_to_radial_graph_data(json_data)

        if graph_data and graph_data["nodes"]:
            # Show summary statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Nodes", len(graph_data["nodes"]))
            with col2:
                st.metric("Total Connections", len(graph_data["links"]))
            with col3:
                genes = [n for n in graph_data["nodes"] if n["type"] == "Gene"]
                st.metric("Genes", len(genes))
            with col4:
                variants = [n for n in graph_data["nodes"] if n["type"] == "Variant"]
                st.metric("Variants", len(variants))

            # Render the D3 radial visualization
            render_radial_graph(graph_data)

            # Optional: Show raw data in expander
            with st.expander("📊 View Graph Data (for debugging)"):
                st.json(graph_data)
        else:
            st.error("Could not parse the JSON-LD file to generate graph data.")

    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid JSON-LD file.")
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.exception(e) # Provides a full traceback for debugging