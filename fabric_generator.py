import os
import argparse
import stat
import urllib.request
import re

def clean_package_name(name):
    # Remove all non-alphanumeric characters and convert to lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def create_mod(mod_name, mod_id, version, author, description, mc_version):
    print(f"Creating mod {mod_name} ({mod_id}) for Minecraft {mc_version}...")

    clean_author = clean_package_name(author)
    if not clean_author:
        clean_author = "user"

    # Create directory structure
    mod_dir = os.path.join(os.getcwd(), mod_id)
    if os.path.exists(mod_dir):
        print(f"Directory {mod_dir} already exists. Aborting.")
        return

    os.makedirs(mod_dir)
    os.makedirs(os.path.join(mod_dir, "src", "main", "java", "com", clean_author, mod_id, "mixin"))
    os.makedirs(os.path.join(mod_dir, "src", "main", "resources", "assets", mod_id))
    os.makedirs(os.path.join(mod_dir, "src", "client", "java", "com", clean_author, mod_id, "client"))
    os.makedirs(os.path.join(mod_dir, "gradle", "wrapper"))

    # 1. build.gradle
    build_gradle = """plugins {
	id 'fabric-loom' version '1.7-SNAPSHOT'
	id 'maven-publish'
}

version = project.mod_version
group = project.maven_group

base {
	archivesName = project.archives_base_name
}

repositories {
	// Add repositories to publish to here.
	// Notice: This block does NOT have the same function as the block in the top level.
	// The repositories here will be used for publishing your artifact, not for
	// retrieving dependencies.
}

dependencies {
	// To change the versions see the gradle.properties file
	minecraft "com.mojang:minecraft:${project.minecraft_version}"
	mappings loom.officialMojangMappings()
	modImplementation "net.fabricmc:fabric-loader:${project.loader_version}"

	// Fabric API. This is technically optional, but you probably want it anyway.
	modImplementation "net.fabricmc.fabric-api:fabric-api:${project.fabric_version}"
}

processResources {
	inputs.property "version", project.version
	inputs.property "minecraft_version", project.minecraft_version
	inputs.property "loader_version", project.loader_version
	filteringCharset "UTF-8"

	filesMatching("fabric.mod.json") {
		expand "version": project.version,
				"minecraft_version": project.minecraft_version,
				"loader_version": project.loader_version
	}
}

def targetJavaVersion = 21
tasks.withType(JavaCompile).configureEach {
	// ensure that the encoding is set to UTF-8, no matter what the system default is
	// this fixes some edge cases with special characters not displaying correctly
	// see http://yodaconditions.net/blog/fix-for-java-file-encoding-problems-with-gradle.html
	// If Javadoc is generated, this must be specified in that task too.
	it.options.encoding = "UTF-8"
	if (targetJavaVersion >= 10 || JavaVersion.current().isJava10Compatible()) {
		it.options.release.set(targetJavaVersion)
	}
}

java {
	def javaVersion = JavaVersion.toVersion(targetJavaVersion)
	if (JavaVersion.current() < javaVersion) {
		toolchain.languageVersion = JavaLanguageVersion.of(targetJavaVersion)
	}

	// Loom will automatically attach sourcesJar to a RemapSourcesJar task and to the "build" task
	// if it is present.
	// If you remove this line, sources will not be generated.
	withSourcesJar()
}

jar {
	from("LICENSE") {
		rename { "${it}_${project.archivesBaseName}"}
	}
}

// configure the maven publication
publishing {
	publications {
		create("mavenJava", MavenPublication) {
			artifactId = project.archives_base_name
			from components.java
		}
	}

	// See https://docs.gradle.org/current/userguide/publishing_maven.html for information on how to set up publishing.
	repositories {
		// Add repositories to publish to here.
		// Notice: This block does NOT have the same function as the block in the top level.
		// The repositories here will be used for publishing your artifact, not for
		// retrieving dependencies.
	}
}
"""
    with open(os.path.join(mod_dir, "build.gradle"), "w") as f:
        f.write(build_gradle)

    # 2. gradle.properties
    gradle_properties = f"""# Done to increase the memory available to gradle.
org.gradle.jvmargs=-Xmx1G
org.gradle.parallel=true

# Fabric Properties
# check these on https://fabricmc.net/develop
minecraft_version={mc_version}
yarn_mappings=1.21.1+build.3
loader_version=0.16.2

# Mod Properties
mod_version={version}
maven_group=com.{clean_author}.{mod_id}
archives_base_name={mod_id}

# Dependencies
fabric_version=0.102.0+1.21.1
"""
    with open(os.path.join(mod_dir, "gradle.properties"), "w") as f:
        f.write(gradle_properties)

    # 3. settings.gradle
    settings_gradle = f"""pluginManagement {{
	repositories {{
		maven {{
			name = 'Fabric'
			url = 'https://maven.fabricmc.net/'
		}}
		mavenCentral()
		gradlePluginPortal()
	}}
}}

rootProject.name = '{mod_id}'
"""
    with open(os.path.join(mod_dir, "settings.gradle"), "w") as f:
        f.write(settings_gradle)

    # 4. src/main/resources/fabric.mod.json
    fabric_mod_json = f"""{{
	"schemaVersion": 1,
	"id": "{mod_id}",
	"version": "${{version}}",
	"name": "{mod_name}",
	"description": "{description}",
	"authors": [
		"{author}"
	],
	"contact": {{
		"homepage": "https://fabricmc.net/",
		"sources": "https://github.com/FabricMC/fabric-example-mod"
	}},
	"license": "CC0-1.0",
	"icon": "assets/{mod_id}/icon.png",
	"environment": "*",
	"entrypoints": {{
		"main": [
			"com.{clean_author}.{mod_id}.{mod_name.replace(' ', '')}"
		],
		"client": [
			"com.{clean_author}.{mod_id}.client.{mod_name.replace(' ', '')}Client"
		]
	}},
	"mixins": [
		"{mod_id}.mixins.json",
		{{
			"config": "{mod_id}.client.mixins.json",
			"environment": "client"
		}}
	],
	"depends": {{
		"fabricloader": ">=${{loader_version}}",
		"minecraft": "~${{minecraft_version}}",
		"java": ">=21",
		"fabric-api": "*"
	}},
	"suggests": {{
		"another-mod": "*"
	}}
}}
"""
    with open(os.path.join(mod_dir, "src", "main", "resources", "fabric.mod.json"), "w") as f:
        f.write(fabric_mod_json)

    # 5. src/main/resources/modid.mixins.json
    mixins_json = f"""{{
	"required": true,
	"minVersion": "0.8",
	"package": "com.{clean_author}.{mod_id}.mixin",
	"compatibilityLevel": "JAVA_21",
	"mixins": [
		"ExampleMixin"
	],
	"injectors": {{
		"defaultRequire": 1
	}}
}}
"""
    with open(os.path.join(mod_dir, "src", "main", "resources", f"{mod_id}.mixins.json"), "w") as f:
        f.write(mixins_json)

    # 6. src/main/resources/modid.client.mixins.json
    client_mixins_json = f"""{{
	"required": true,
	"minVersion": "0.8",
	"package": "com.{clean_author}.{mod_id}.mixin.client",
	"compatibilityLevel": "JAVA_21",
	"mixins": [
	],
	"client": [
	],
	"injectors": {{
		"defaultRequire": 1
	}}
}}
"""
    with open(os.path.join(mod_dir, "src", "main", "resources", f"{mod_id}.client.mixins.json"), "w") as f:
        f.write(client_mixins_json)

    # 7. Java Main Class
    main_class = f"""package com.{clean_author}.{mod_id};

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class {mod_name.replace(' ', '')} implements ModInitializer {{
	public static final String MOD_ID = "{mod_id}";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {{
		LOGGER.info("Hello Fabric world!");
	}}
}}
"""
    with open(os.path.join(mod_dir, "src", "main", "java", "com", clean_author, mod_id, f"{mod_name.replace(' ', '')}.java"), "w") as f:
        f.write(main_class)

    # 8. Java Client Class
    client_class = f"""package com.{clean_author}.{mod_id}.client;

import net.fabricmc.api.ClientModInitializer;

public class {mod_name.replace(' ', '')}Client implements ClientModInitializer {{
	@Override
	public void onInitializeClient() {{
	}}
}}
"""
    with open(os.path.join(mod_dir, "src", "client", "java", "com", clean_author, mod_id, "client", f"{mod_name.replace(' ', '')}Client.java"), "w") as f:
        f.write(client_class)

    # 9. Example Mixin
    example_mixin = f"""package com.{clean_author}.{mod_id}.mixin;

import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import com.{clean_author}.{mod_id}.{mod_name.replace(' ', '')};

@Mixin(MinecraftServer.class)
public class ExampleMixin {{
	@Inject(at = @At("HEAD"), method = "loadLevel")
	private void init(CallbackInfo info) {{
		{mod_name.replace(' ', '')}.LOGGER.info("This line is printed by an example mod mixin!");
	}}
}}
"""
    with open(os.path.join(mod_dir, "src", "main", "java", "com", clean_author, mod_id, "mixin", "ExampleMixin.java"), "w") as f:
        f.write(example_mixin)

    # 10. gradle-wrapper.properties
    gradle_wrapper_properties = """distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.9-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""
    with open(os.path.join(mod_dir, "gradle", "wrapper", "gradle-wrapper.properties"), "w") as f:
        f.write(gradle_wrapper_properties)

    # Download gradlew and wrapper jar
    print("Downloading Gradle wrapper files...")
    gradle_version = "v8.9.0"
    urllib.request.urlretrieve(f"https://raw.githubusercontent.com/gradle/gradle/{gradle_version}/gradlew", os.path.join(mod_dir, "gradlew"))
    urllib.request.urlretrieve(f"https://raw.githubusercontent.com/gradle/gradle/{gradle_version}/gradlew.bat", os.path.join(mod_dir, "gradlew.bat"))
    urllib.request.urlretrieve(f"https://raw.githubusercontent.com/gradle/gradle/{gradle_version}/gradle/wrapper/gradle-wrapper.jar", os.path.join(mod_dir, "gradle", "wrapper", "gradle-wrapper.jar"))

    # Make gradlew executable
    st = os.stat(os.path.join(mod_dir, "gradlew"))
    os.chmod(os.path.join(mod_dir, "gradlew"), st.st_mode | stat.S_IEXEC)

    # Create empty icon
    with open(os.path.join(mod_dir, "src", "main", "resources", "assets", mod_id, "icon.png"), "wb") as f:
        # A 1x1 transparent PNG file properly escaped
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff\x3f\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82')

    print(f"Mod generator completed. Mod created at {mod_dir}")
    print("Run './gradlew build' inside the directory to compile the mod.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Fabric mod using Mojang mappings")
    parser.add_argument("--name", default="My Mod", help="Mod name")
    parser.add_argument("--id", default="mymod", help="Mod ID")
    parser.add_argument("--version", default="1.0.0", help="Mod version")
    parser.add_argument("--author", default="User", help="Mod author")
    parser.add_argument("--desc", default="A cool mod", help="Mod description")
    parser.add_argument("--mc", default="1.21.11", help="Minecraft version")

    args = parser.parse_args()
    create_mod(args.name, args.id, args.version, args.author, args.desc, args.mc)
