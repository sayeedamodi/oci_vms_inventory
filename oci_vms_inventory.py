import oci
import pandas as pd

# Load OCI config
config = oci.config.from_file(profile_name="DEFAULT")
tenancy_id = config["tenancy"]

identity_client = oci.identity.IdentityClient(config)
compute_client = oci.core.ComputeClient(config)

rows = []
shape_cache = {}

# Get all compartments
compartments = oci.pagination.list_call_get_all_results(
    identity_client.list_compartments,
    tenancy_id,
    compartment_id_in_subtree=True,
    access_level="ANY"
).data

# Add root compartment
root = identity_client.get_compartment(tenancy_id).data
compartments.append(root)

for comp in compartments:
    # Cache shapes per compartment
    if comp.id not in shape_cache:
        shapes = oci.pagination.list_call_get_all_results(
            compute_client.list_shapes,
            comp.id
        ).data
        shape_cache[comp.id] = {s.shape: s for s in shapes}

    instances = oci.pagination.list_call_get_all_results(
        compute_client.list_instances,
        comp.id
    ).data

    for inst in instances:
        # Tags
        defined_tags = inst.defined_tags or {}
        application_tag = defined_tags.get("Application", {}).get("Application")
        environment_tag = defined_tags.get("Environment", {}).get("Environment")

        # OCPU & Memory
        ocpu_count = None
        memory_gb = None

        if inst.shape_config:
            ocpu_count = inst.shape_config.ocpus
            memory_gb = inst.shape_config.memory_in_gbs
        else:
            shape = shape_cache[comp.id].get(inst.shape)
            if shape:
                ocpu_count = shape.ocpus
                memory_gb = shape.memory_in_gbs

        # Provisioned Date
        provisioned_date = inst.time_created.strftime("%Y-%m-%d %H:%M:%S") if inst.time_created else None

        rows.append({
            "Compartment Name": comp.name,
            "Compartment OCID": comp.id,
            "Instance Name": inst.display_name,
            "Instance OCID": inst.id,
            "Lifecycle State": inst.lifecycle_state,
            "Shape": inst.shape,
            "OCPU Count": ocpu_count,
            "Memory (GB)": memory_gb,
            "Provisioned Date (UTC)": provisioned_date,
            "Availability Domain": inst.availability_domain,
            "Region": config["region"],
            "Application Tag": application_tag,
            "Environment Tag": environment_tag
        })

# Create DataFrame
df = pd.DataFrame(rows)

# Export to Excel
output_file = "oci_compute_inventory_jeddah_full.xlsx"
df.to_excel(output_file, index=False)

print(f"Compute inventory exported successfully to {output_file}")



