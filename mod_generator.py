import argparse
import os
import subprocess
import shutil
import tempfile
import sys
import zipfile
import json
import re

def parse_args():
    parser = argparse.ArgumentParser(description="Generate a Minecraft Fabric 1.21.11 Mod with Mojang Mappings")
    parser.add_argument("mod_id", help="The mod ID (e.g., mymod)")
    parser.add_argument("mod_name", help="The mod name (e.g., 'My Mod')")
    parser.add_argument("description", help="The mod description")
    parser.add_argument("package_name", help="The package name (e.g., com.example.mymod)")
    parser.add_argument("--output", default=".", help="Output directory for the zip file")
    return parser.parse_args()

def clone_template(temp_dir):
    print("Cloning fabric-example-mod (1.21 branch)...")
    subprocess.run([
        "git", "clone", "--branch", "1.21", "--depth", "1",
        "https://github.com/FabricMC/fabric-example-mod.git",
        temp_dir
    ], check=True)

    # Remove the .git directory to sever the git history
    git_dir = os.path.join(temp_dir, ".git")
    if os.path.exists(git_dir):
        shutil.rmtree(git_dir)

def update_gradle_properties(temp_dir, mod_id, package_name):
    prop_file = os.path.join(temp_dir, "gradle.properties")
    with open(prop_file, "r") as f:
        content = f.read()

    content = re.sub(r'minecraft_version=.*', r'minecraft_version=1.21.11', content)
    content = re.sub(r'maven_group=.*', f'maven_group={package_name}', content)
    content = re.sub(r'archives_base_name=.*', f'archives_base_name={mod_id}', content)

    with open(prop_file, "w") as f:
        f.write(content)

def update_build_gradle(temp_dir):
    build_file = os.path.join(temp_dir, "build.gradle")
    with open(build_file, "r") as f:
        content = f.read()

    # Ensure mappings use Mojang Mappings
    if 'mappings loom.officialMojangMappings()' not in content:
        # If it uses yarn or something else, replace it
        content = re.sub(
            r'mappings\s+.*',
            r'mappings loom.officialMojangMappings()',
            content
        )

    with open(build_file, "w") as f:
        f.write(content)

def update_fabric_mod_json(temp_dir, mod_id, mod_name, description):
    json_file = os.path.join(temp_dir, "src", "main", "resources", "fabric.mod.json")
    with open(json_file, "r") as f:
        data = json.load(f)

    data["id"] = mod_id
    data["name"] = mod_name
    data["description"] = description

    if "authors" in data:
        data["authors"] = ["Me!"]
    if "contact" in data:
        data["contact"] = {"homepage": "https://fabricmc.net/"}

    # Update entrypoints points to use the new package
    # We will handle package replacement globally as well, but let's update this safely

    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)

def replace_in_files(temp_dir, mod_id, mod_name, package_name):
    # Find all java files and fabric.mod.json and mixin configs
    old_package = "com.example" # Default in fabric-example-mod
    old_mod_id = "modid"

    # Sanitize the mod name to create a valid Java class name
    class_name = re.sub(r'[^a-zA-Z0-9_]', '', mod_name)
    if not class_name or class_name[0].isdigit():
        class_name = "Mod" + class_name

    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith(".java") or file.endswith(".json"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()

                    # Update JSON configs for mixins and entrypoints
                    if file == "fabric.mod.json":
                        # Entrypoints
                        content = content.replace(f"{old_package}.ExampleMod", f"{package_name}.{class_name}")
                        content = content.replace(f"{old_package}.ExampleModClient", f"{package_name}.{class_name}Client")
                        content = content.replace(f"{old_mod_id}.mixins.json", f"{mod_id}.mixins.json")
                        content = content.replace(f"{old_mod_id}.client.mixins.json", f"{mod_id}.client.mixins.json")
                    elif file.endswith(".mixins.json"):
                        # Mixins package
                        content = content.replace(f"{old_package}.mixin", f"{package_name}.mixin")

                    content = content.replace(old_package, package_name)
                    content = content.replace(f'"{old_mod_id}"', f'"{mod_id}"') # Replace "modid" carefully
                    content = content.replace(f'{old_mod_id}:', f'{mod_id}:') # Resource locations
                    content = content.replace(f'assets/{old_mod_id}', f'assets/{mod_id}') # asset paths
                    content = content.replace(f'MOD_ID = "{old_mod_id}"', f'MOD_ID = "{mod_id}"') # java constant

                    # Handle ExampleMod renaming, being careful not to replace part of ExampleModClient if we do ExampleMod first
                    content = content.replace("ExampleModClient", f"{class_name}Client")
                    content = content.replace("ExampleMod", class_name)

                    with open(filepath, "w") as f:
                        f.write(content)
                except Exception as e:
                    pass

def move_package_dirs(temp_dir, mod_id, mod_name, package_name):
    old_package_path = os.path.join("com", "example")
    new_package_path = os.path.join(*package_name.split("."))

    class_name = re.sub(r'[^a-zA-Z0-9_]', '', mod_name)
    if not class_name or class_name[0].isdigit():
        class_name = "Mod" + class_name

    for source_dir in ["main", "client"]:
        java_dir = os.path.join(temp_dir, "src", source_dir, "java")
        if not os.path.exists(java_dir):
            continue

        old_dir = os.path.join(java_dir, old_package_path)
        if os.path.exists(old_dir):
            new_dir = os.path.join(java_dir, new_package_path)
            os.makedirs(new_dir, exist_ok=True)

            # Move all contents from old_dir to new_dir
            for item in os.listdir(old_dir):
                shutil.move(os.path.join(old_dir, item), new_dir)

            # Clean up old empty directories
            try:
                os.rmdir(old_dir)
                os.rmdir(os.path.dirname(old_dir)) # e.g. 'com' if it's empty
            except OSError:
                pass

        # Rename java files to match the class name ExampleMod -> mod_name
        # Note: files might be inside subdirectories (like mixin/), so we use os.walk
        new_dir = os.path.join(java_dir, new_package_path)
        if os.path.exists(new_dir):
            for root, _, files in os.walk(new_dir):
                for file in files:
                    if file.startswith("ExampleMod"):
                        new_file = file.replace("ExampleMod", class_name)
                        shutil.move(os.path.join(root, file), os.path.join(root, new_file))

def main():
    args = parse_args()
    print(f"Mod ID: {args.mod_id}")
    print(f"Mod Name: {args.mod_name}")
    print(f"Description: {args.description}")
    print(f"Package: {args.package_name}")

    with tempfile.TemporaryDirectory() as temp_dir:
        clone_template(temp_dir)
        print("Cloned successfully.")

        # Apply updates
        update_gradle_properties(temp_dir, args.mod_id, args.package_name)
        update_build_gradle(temp_dir)
        update_fabric_mod_json(temp_dir, args.mod_id, args.mod_name, args.description)
        replace_in_files(temp_dir, args.mod_id, args.mod_name, args.package_name)
        move_package_dirs(temp_dir, args.mod_id, args.mod_name, args.package_name)

        # Rename mixin config file
        mixin_file = os.path.join(temp_dir, "src", "main", "resources", "fabric-example-mod.mixins.json")
        if not os.path.exists(mixin_file):
            mixin_file = os.path.join(temp_dir, "src", "main", "resources", "modid.mixins.json")
        if os.path.exists(mixin_file):
            new_mixin_file = os.path.join(temp_dir, "src", "main", "resources", f"{args.mod_id}.mixins.json")
            shutil.move(mixin_file, new_mixin_file)

        client_mixin_file = os.path.join(temp_dir, "src", "client", "resources", "fabric-example-mod.client.mixins.json")
        if not os.path.exists(client_mixin_file):
            client_mixin_file = os.path.join(temp_dir, "src", "client", "resources", "modid.client.mixins.json")
        if os.path.exists(client_mixin_file):
            new_client_mixin_file = os.path.join(temp_dir, "src", "client", "resources", f"{args.mod_id}.client.mixins.json")
            shutil.move(client_mixin_file, new_client_mixin_file)

        # Rename assets folder
        assets_dir = os.path.join(temp_dir, "src", "main", "resources", "assets", "fabric-example-mod")
        if not os.path.exists(assets_dir):
            assets_dir = os.path.join(temp_dir, "src", "main", "resources", "assets", "modid")
        if os.path.exists(assets_dir):
            new_assets_dir = os.path.join(temp_dir, "src", "main", "resources", "assets", args.mod_id)
            shutil.move(assets_dir, new_assets_dir)

        print("Mod files generated successfully.")

        # Create ZIP file
        zip_filename = f"{args.mod_id}.zip"
        zip_filepath = os.path.join(args.output, zip_filename)
        print(f"Zipping to {zip_filepath}...")

        # Create a ZIP file with the contents of the temp_dir directly at the root of the zip
        shutil.make_archive(
            base_name=os.path.join(args.output, args.mod_id),
            format='zip',
            root_dir=temp_dir
        )
        print("Zipping complete.")

if __name__ == "__main__":
    main()
