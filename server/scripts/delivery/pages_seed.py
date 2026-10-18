"""
Default content of the home and presentation pages, written by `manage.py seed_pages`.

The seed never modifies an existing row:
- `SiteSettings` is created when missing;
- `PageSection` is completed pair by pair, so a section added by a later version shows up;
- the editorial lists are filled only when their table is empty, so a deleted row does not come back.
"""

from datetime import date
from pathlib import Path

from django.core.files import File

from .models_pages import (
    PAGE_SECTIONS,
    FeatureCard,
    PageSection,
    ReleaseNote,
    RoadmapMilestone,
    SampleGame,
    ShowcaseImage,
    SiteLink,
    SiteSettings,
)

SEED_SECTIONS = {
    ("home", "download"): ("Download", "The engine SDK and the Owl Nest editor, for Linux and Windows."),
    ("home", "news"): ("Latest news", ""),
    ("presentation", "gallery"): (
        "Five styles, one game",
        "Scenes of the Engine Demo, rendered headless by the game runner on Vulkan.",
    ),
    ("presentation", "features"): ("Why Owl Engine", ""),
    ("presentation", "release"): ("Download", "The engine SDK and the Owl Nest editor, for Linux and Windows."),
    ("presentation", "samples"): (
        "Sample games",
        "Small but complete games made with Owl Engine, beside the all-in-one Engine Demo. "
        "Open one from the **Sample games** list of the Owl Nest File screen.",
    ),
    ("presentation", "roadmap"): (
        "Roadmap",
        "Exit criteria take precedence over dates: a version ships when its criteria hold.",
    ),
    ("presentation", "about"): (
        "How it is built",
        "Owl Engine is developed by one maintainer with Claude Code as a development tool. Every change is reviewed "
        "and owned by the maintainer, and goes through a strict CI: unit and scenario tests on Linux x64/arm64 and "
        "Windows, sanitizers, clang-tidy, include checks and performance budgets.",
    ),
    ("presentation", "links"): ("Get involved", "Source, issues and discussions live on GitHub."),
}

# key: (order, caption, style, in gallery, alt text)
SEED_IMAGES = {
    "hub": (
        1,
        "2D RPG hub: a village with four houses, one per level",
        "2d",
        True,
        "Top-down pixel-art village with houses, a river and a hero, HUD counter on top",
    ),
    "raycast": (
        2,
        "Raycast level: Wolfenstein 3D E1M1 in first person",
        "raycast",
        True,
        "First-person view of a stone corridor with doors, minimap in a corner",
    ),
    "voxel": (
        3,
        "Voxel terrain: walk, run and fly over a procedural world",
        "voxel",
        True,
        "Blocky hills and trees under a blue sky, distance objective in the HUD",
    ),
    "iso_town": (
        4,
        "Isometric town: build roads and watch the traffic",
        "isometric",
        True,
        "Isometric town with roads, cars, a river and a harbour",
    ),
    "platformer": (
        5,
        "2D platformer: meadow, farm and factory",
        "2d",
        True,
        "Side-scrolling level with platforms, coins and an astronaut",
    ),
    "main_menu": (
        6,
        "Main menu: one HUD system for every scene",
        "hud",
        True,
        "Engine Demo main menu with the Owl logo and buttons",
    ),
    "social_preview": (0, "Owl Engine", "", False, "Owl Engine logo and four screenshots of the Engine Demo"),
}

# Image keys the site settings take when their field is still empty.
SITE_IMAGE_KEYS = {"hero_image": "hub", "social_image": "social_preview"}

# (icon, title, body)
SEED_FEATURES = (
    (
        "layers",
        "Render-style mixing",
        "2D batches, tilemaps, a raycaster, voxel terrain, isometric maps and 3D meshes are renderer-stack layers "
        "that compose with each other and the HUD, in the editor viewport and in Play.",
    ),
    (
        "edit_square",
        "Owl Nest editor",
        "Scenes, tilemaps, node graphs, animations, HUDs and prefabs with undo/redo and hot reload.",
    ),
    (
        "smart_toy",
        "Drivable by AI agents",
        "A built-in MCP server lets an AI agent drive Owl Nest through the same editor commands as the user.",
    ),
    (
        "verified",
        "Engineering rigour",
        "Unit and scenario tests, CI on Linux x64/arm64 and Windows, sanitizers, Vulkan validation clean and "
        "performance budgets checked against a baseline.",
    ),
    (
        "deployed_code",
        "Modern rendering",
        "OpenGL 4.5 and Vulkan 1.4 backends, Slang shaders compiled to SPIR-V and precompiled at build time.",
    ),
    (
        "account_tree",
        "ECS and Lua",
        "Entity-Component-System on EnTT with parent-child hierarchy, prefabs and Lua 5.5 scripting.",
    ),
    (
        "sports_esports",
        "Physics, sound, input",
        "Box2D 2D physics, OpenAL spatial sound, input actions with gamepad support and a fixed simulation tick.",
    ),
    (
        "package_2",
        "From editor to game",
        "OBJ, glTF and FBX loading, asset packs and a game runner: export a project as a standalone game.",
    ),
)

SAMPLES_URL = "https://github.com/Silmaen/Owl/tree/main/samples/"

# (title, slug, inspired by, status, target, published, summary, exercises, image key, link)
SEED_SAMPLES = (
    (
        "Breakout",
        "breakout",
        "Breakout / Arkanoid",
        "playable",
        "0.4.0",
        True,
        "Five levels on one screen, three lives, bricks of one to three hits and two power-ups.",
        "2D, physics, HUD, sound, gamepad",
        "",
        SAMPLES_URL + "breakout",
    ),
    (
        "Sokoban",
        "sokoban",
        "Sokoban",
        "playable",
        "0.4.0",
        True,
        "Ten levels of rising difficulty, from one crate to five, with undo and saved best scores; levels are "
        "painted in the Owl Nest tilemap editor.",
        "Tilemap, undo, saves, level editing",
        "",
        SAMPLES_URL + "sokoban",
    ),
    (
        "Wolfenstein mini",
        "wolfenstein",
        "Wolfenstein 3D",
        "playable",
        "0.4.0",
        True,
        "Three floors drawn by the raycast renderer: treasure, keys, locked doors, secret walls and an exit "
        "elevator on each floor.",
        "Raycast, doors, pick-ups, HUD",
        "raycast",
        SAMPLES_URL + "wolfenstein",
    ),
    (
        "Mini Transport Tycoon",
        "mini-transport-tycoon",
        "Mini Motorways / TTD",
        "planned",
        "0.5.0",
        True,
        "Roads, vehicles and a management HUD on the isometric renderer: Owl Engine's main argument.",
        "Isometric, roads, pathfinding, management HUD",
        "iso_town",
        "",
    ),
    (
        "Mini Minecraft",
        "mini-minecraft",
        "Minecraft",
        "planned",
        "0.6.0",
        True,
        "A finite voxel island: break blocks, collect them, build from a nine-slot hotbar.",
        "Voxel, build and break, inventory",
        "voxel",
        "",
    ),
    (
        "One-room Zelda-like",
        "zelda-like",
        "The Legend of Zelda",
        "planned",
        "0.7.0",
        False,
        "A top-down room with dialogue, enemy AI and 2D lights.",
        "Top-down, dialogue, enemy AI, 2D lights",
        "",
        "",
    ),
    (
        "Marble or mini kart",
        "marble-kart",
        "Marble Madness / Kart",
        "planned",
        "0.7.0",
        False,
        "A small 3D game on Jolt physics and shadows.",
        "3D, Jolt physics, shadows",
        "",
        "",
    ),
    (
        "Networked Bomberman",
        "bomberman",
        "Bomberman",
        "planned",
        "0.8.0",
        False,
        "Multiplayer on the deterministic simulation.",
        "Tilemap, deterministic simulation, multiplayer",
        "",
        "",
    ),
)

# Sample slug -> key of the image it shows.
SAMPLE_IMAGE_KEYS = {sample[1]: sample[8] for sample in SEED_SAMPLES if sample[8]}

# (version, status, expected, is target, goal, highlights)
SEED_MILESTONES = (
    (
        "0.4.0",
        "in_progress",
        date(2026, 11, 1),
        False,
        "An engine able to carry a Transport Tycoon-like game: isometric renderer on large chunked tile maps with "
        "slopes, vehicles on a tile graph, a HUD for management games, gamepad input actions, a fixed simulation "
        "tick and an MCP server in Owl Nest.",
        "- `RendererIsometric` layer with corner heights and 19 slopes\n"
        "- Tile-graph pathfinding and vehicles following roads\n"
        "- HUD overhaul with the `.owlhud` asset and its editor\n"
        "- Input actions with a gamepad\n"
        "- MCP server built into Owl Nest\n"
        "- Sample games Breakout, Sokoban and Wolfenstein mini",
    ),
    (
        "0.5.0",
        "planned",
        date(2027, 1, 31),
        False,
        "A focused 3D core: static meshes, PBR, lights and shadows for 2D, isometric and 3D, render graph, "
        "essential post-processing, full 3D editing.",
        "",
    ),
    (
        "0.6.0",
        "planned",
        date(2027, 4, 15),
        False,
        "Produce content at scale and script games without C++: offline asset pipeline, animation and effects, "
        "procedural graphs, tile tools, Lua editor scripts and visual scripting compiled to Lua.",
        "",
    ),
    (
        "0.7.0",
        "planned",
        date(2027, 6, 30),
        False,
        "The systems that make games — AI, 2D and 3D physics, audio, narrative — on a deterministic simulation "
        "with input replay and rewind.",
        "",
    ),
    (
        "0.8.0",
        "planned",
        date(2027, 9, 15),
        False,
        "Open Owl Engine to other players, modders and the browser: networked multiplayer, mods, the Web; the 1.0 "
        "release candidate.",
        "",
    ),
    (
        "1.0.0",
        "planned",
        date(2027, 10, 31),
        True,
        "A stable engine a third party can rely on: frozen public API, versioned formats, consumable SDK, two "
        "showcase games, Linux, Windows and the Web.",
        "",
    ),
)

# (branch, title, release date, highlights)
SEED_RELEASE_NOTES = (
    (
        "0.3.0",
        "Owl Engine 0.3.0 — Foundations",
        date(2026, 10, 11),
        "Every known bug fixed, safety nets, Owl RHI repaired, architecture opened, iteration sped up, Owl Nest "
        "made ergonomic.",
    ),
)

GITHUB_URL = "https://github.com/Silmaen/Owl"

# (kind, label, url, icon, placement)
SEED_LINKS = (
    ("github", "GitHub", GITHUB_URL, "code", "band"),
    ("docs_latest", "Documentation", "", "menu_book", "band"),
    ("downloads", "All downloads", "", "package_2", "band"),
    ("changelog", "Changelog", GITHUB_URL + "/blob/main/doc/pages/changelog.md", "history", "band"),
    ("roadmap", "Roadmap", GITHUB_URL + "/blob/main/doc/pages/roadmap.md", "map", "band"),
    ("custom", "Issues", GITHUB_URL + "/issues", "bug_report", "band"),
    ("github", "GitHub", GITHUB_URL, "code", "footer"),
    ("custom", "Site source", "https://github.com/Silmaen/OwlDelivery", "code", "footer"),
)


def link_new_image(image):
    """
    Give a new image to the rows waiting for its key: the site settings (`hub` → hero, `social_preview` → social)
    and the seeded sample games (`raycast` → Wolfenstein mini, ...). The samples are often seeded before the engine
    CI pushes its screenshots, so the link is made when the image arrives.
    Only an empty field is filled: a choice made in the admin is kept.
    :param image: The image just created.
    """
    settings_row = SiteSettings.load()
    for field, key in SITE_IMAGE_KEYS.items():
        if image.key == key and getattr(settings_row, f"{field}_id") is None:
            setattr(settings_row, field, image)
            settings_row.save(update_fields=[field])
    for sample in SampleGame.objects.filter(slug__in=SAMPLE_IMAGE_KEYS, image__isnull=True):
        if SAMPLE_IMAGE_KEYS[sample.slug] == image.key:
            sample.image = image
            sample.save(update_fields=["image", "updated"])


def seed_images(images_dir):
    """
    Import `<images_dir>/*.png` as published images, skipping the keys that already exist.
    :param images_dir: Folder of a checkout of `Owl/doc/images/showcase/`.
    :return: Number of images created.
    """
    created = 0
    for path in sorted(Path(images_dir).glob("*.png")):
        key = path.stem
        if ShowcaseImage.objects.filter(key=key).exists():
            continue
        order, caption, style_tag, in_gallery, alt_text = SEED_IMAGES.get(key, (100, key, "", True, key))
        image = ShowcaseImage(
            key=key,
            caption=caption,
            alt_text=alt_text,
            style_tag=style_tag,
            in_gallery=in_gallery,
            order=order,
            source="admin",
        )
        with open(path, "rb") as source:
            image.image = File(source, name=path.name)
            image.save()
        link_new_image(image)
        created += 1
    return created


def seed_pages(images_dir=None):
    """
    Create the missing default content.
    :param images_dir: Optional folder of screenshots to import first.
    :return: Number of rows created, per model name.
    """
    created = {}
    if not SiteSettings.objects.filter(pk=1).exists():
        SiteSettings.load()
        created["SiteSettings"] = 1

    if images_dir:
        created["ShowcaseImage"] = seed_images(images_dir)

    sections = 0
    for page, keys in PAGE_SECTIONS.items():
        for order, key in enumerate(keys, start=1):
            if PageSection.objects.filter(page=page, key=key).exists():
                continue
            title, intro = SEED_SECTIONS[(page, key)]
            PageSection.objects.create(page=page, key=key, title=title, intro=intro, order=order)
            sections += 1
    created["PageSection"] = sections

    if not FeatureCard.objects.exists():
        for order, (icon, title, body) in enumerate(SEED_FEATURES, start=1):
            FeatureCard.objects.create(icon=icon, title=title, body=body, order=order)
        created["FeatureCard"] = len(SEED_FEATURES)

    if not SampleGame.objects.exists():
        images = {image.key: image for image in ShowcaseImage.objects.all()}
        for order, sample in enumerate(SEED_SAMPLES, start=1):
            title, slug, inspired_by, status, target, published, summary, exercises, image_key, link = sample
            SampleGame.objects.create(
                title=title,
                slug=slug,
                inspired_by=inspired_by,
                status=status,
                target_version=target,
                published=published,
                summary=summary,
                exercises=exercises,
                image=images.get(image_key),
                link_url=link,
                order=order,
            )
        created["SampleGame"] = len(SEED_SAMPLES)

    if not RoadmapMilestone.objects.exists():
        for version, status, expected, is_target, goal, highlights in SEED_MILESTONES:
            RoadmapMilestone.objects.create(
                version=version,
                status=status,
                expected_date=expected,
                is_target=is_target,
                goal=goal,
                highlights=highlights,
            )
        created["RoadmapMilestone"] = len(SEED_MILESTONES)

    if not ReleaseNote.objects.exists():
        for branch, title, release_date, highlights in SEED_RELEASE_NOTES:
            ReleaseNote.objects.create(branch=branch, title=title, release_date=release_date, highlights=highlights)
        created["ReleaseNote"] = len(SEED_RELEASE_NOTES)

    if not SiteLink.objects.exists():
        for order, (kind, label, url, icon, placement) in enumerate(SEED_LINKS, start=1):
            SiteLink.objects.create(kind=kind, label=label, url=url, icon=icon, placement=placement, order=order)
        created["SiteLink"] = len(SEED_LINKS)

    return created
